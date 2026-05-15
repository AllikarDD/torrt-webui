import os
import re
import subprocess
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, URL

app = Flask(__name__)
app.config.from_mapping(
    PORT=int(os.environ.get('TORRTWEBUI_PORT', 5000)),
    TORRT_PATH=os.environ.get('TORRTWEBUI_TORRT_PATH', 'torrt'),
    SECRET_KEY=os.environ.get('TORRTWEBUI_SECRET_KEY', 'your-secret-key-here-change-in-production'),
    LOG_FILE=os.environ.get('TORRTWEBUI_LOG_FILE', '/var/log/torrtwebui/log.txt'),
    LOG_LEVEL=os.environ.get('TORRTWEBUI_LOG_LEVEL', 'DEBUG').upper(),
)

log_file = os.path.expanduser(app.config['LOG_FILE'])
log_dir = os.path.dirname(log_file)
if log_dir:
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError:
        pass

log_level = getattr(logging, app.config['LOG_LEVEL'], logging.DEBUG)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

try:
    file_handler = RotatingFileHandler(log_file, maxBytes=10_000_000, backupCount=5)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s'))
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)
except OSError as exc:
    logger.warning('Could not open log file %s (%s); falling back to console only', log_file, exc)


def get_current_walk_interval():
    config_path = os.path.expanduser('~/.config/torrt/config.py')
    try:
        with open(config_path, 'r') as f:
            content = f.read()
            match = re.search(r'WALK_INTERVAL\s*=\s*(\d+(?:\.\d+)?)', content)
            if match:
                return float(match.group(1))
    except OSError:
        logger.debug('Could not read walk interval config from %s', config_path)
    return None


def run_torrt_command(cmd_args):
    cmd = [app.config['TORRT_PATH']] + cmd_args
    logger.debug('Running command: %s', ' '.join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError as exc:
        logger.exception('torrt executable not found')
        return {'success': False, 'output': '', 'error': str(exc)}
    except subprocess.TimeoutExpired as exc:
        logger.error('Command timed out: %s', ' '.join(cmd))
        logger.debug('Timeout exception: %s', exc)
        return {'success': False, 'output': 'Command timed out', 'error': 'Timeout'}
    except Exception as exc:
        logger.exception('Error running torrt command')
        return {'success': False, 'output': '', 'error': str(exc)}

    output = (result.stderr or result.stdout or '').strip()
    response = {
        'returncode': result.returncode,
        'stdout': result.stdout.strip(),
        'stderr': result.stderr.strip(),
        'output': output,
    }
    logger.debug('Command response: %s', response)

    if result.returncode != 0:
        logger.error('Command failed (returncode=%s): %s', result.returncode, output)
        return {'success': False, 'output': output, 'error': output}

    return {'success': True, 'output': output}


def parse_torrents_list(output):
    torrents = []
    lines = output.strip().split('\n')

    logger.info(f"lines {lines}")

    for line in lines:
        line = line.strip()
        if line and not line.startswith('INFO: walk'):
            # Remove "INFO: " prefix if present
            if line.startswith('INFO:'):
                line = line[5:].strip()
                logger.info(f"line {line}")


            parts = line.split('\t')
            logger.info(f"line {parts}")

            if len(parts) >= 2:
                torrents.append({
                    'hash': parts[0].strip(),
                    'name': parts[1].strip(),
                    'tracker': parts[2].strip() if len(parts) > 2 else 'N/A'
                })
            else:
                torrents.append({
                    'hash': parts[0].strip(),
                    'name': "N/A",
                    'tracker': 'N/A'
                })

    return torrents


def parse_tracker_lines(output):
    trackers = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('INFO:'):
            line = line[5:].strip()
        trackers.append(line)
    return trackers


def build_settings(fields):
    settings = []
    for key, field_name in fields:
        value = request.form.get(field_name)
        if value:
            settings.append(f'{key}={value}')
    return settings


def flash_command_result(result, success_message, failure_message=None):
    if result['success']:
        if any(marker in result['output'] for marker in ('WARNING', 'ERROR')):
            flash(result['output'], 'danger')
        else:
            flash(success_message, 'success')
    else:
        flash(failure_message or result['error'], 'danger')


class AddTorrentForm(FlaskForm):
    url = StringField('Torrent URL', validators=[DataRequired(), URL()])
    download_path = StringField('Download Path (optional)')
    content_layout = SelectField('Content Layout (for qBittorrent)', choices=[
        ('', 'Use client default'),
        ('NoSubfolder', 'No Subfolder - Save files directly'),
        ('CreateSubfolder', 'Create Subfolder - Create folder with torrent name'),
        ('Original', 'Original - Use structure defined in torrent file'),
    ])
    submit = SubmitField('Add Torrent')


class RemoveTorrentForm(FlaskForm):
    torrent_hash = StringField('Torrent Hash', validators=[DataRequired()])
    submit = SubmitField('Remove Torrent')


class RegisterTorrentForm(FlaskForm):
    torrent_hash = StringField('Torrent Hash', validators=[DataRequired()])
    submit = SubmitField('Register Torrent')


@app.route('/')
def index():
    torrents_result = run_torrt_command(['list_torrents'])
    torrents = parse_torrents_list(torrents_result['output']) if torrents_result['success'] else []

    trackers_result = run_torrt_command(['list_trackers'])
    trackers = parse_tracker_lines(trackers_result['output']) if trackers_result['success'] else []

    class SimpleForm:
        def __init__(self):
            self.hidden_tag = lambda: ''

    return render_template(
        'index.html',
        torrents=torrents,
        trackers=trackers,
        add_form=SimpleForm(),
        walk_result=None,
    )


@app.route('/rpc')
def list_rpc():
    result = run_torrt_command(['list_rpc'])
    rpc_list = []

    if result['success']:
        # Parse output - torrt list_rpc shows aliases
        res = [line.split(':')[1].strip() for line in result['output'].split('\n') if line.strip()]
        
        # For each alias, check if it's enabled
        for alias in res:
            rpc_list.append({
                'alias': alias.split('\t')[0],
                'status': alias.split('\t')[1].split('=')[1]
            })

    return render_template('rpc.html', rpc_list=rpc_list, result=result)


@app.route('/configure_rpc', methods=['POST'])
def configure_rpc():
    action = request.form.get('action')
    rpc_alias = request.form.get('rpc_alias')
    settings = build_settings([
        ('host', 'host'),
        ('port', 'port'),
        ('user', 'username'),
        ('password', 'password'),
    ])

    if action in ('add', 'configure') and rpc_alias and settings:
        result = run_torrt_command(['configure_rpc', rpc_alias] + settings)
        flash_command_result(result, f'RPC client "{rpc_alias}" configured successfully!')

        if action == 'add' and result['success']:
            enable_result = run_torrt_command(['enable_rpc', rpc_alias])
            flash_command_result(enable_result, f'RPC client "{rpc_alias}" enabled successfully!',
                                 f'RPC client configured but could not enable: {enable_result["error"]}')
    else:
        flash('RPC alias and settings are required', 'danger')
    return redirect(url_for('list_rpc'))


@app.route('/enable_rpc/<alias>', methods=['POST'])
def enable_rpc(alias):
    result = run_torrt_command(['enable_rpc', alias])
    if result['success']:
        return jsonify({'success': True, 'message': f'RPC {alias} enabled'})
    return jsonify({'success': False, 'error': result['error']}), 400


@app.route('/disable_rpc/<alias>', methods=['POST'])
def disable_rpc(alias):
    result = run_torrt_command(['disable_rpc', alias])
    if result['success']:
        return jsonify({'success': True, 'message': f'RPC {alias} disabled'})
    return jsonify({'success': False, 'error': result['error']}), 400


@app.route('/trackers')
def list_trackers():
    result = run_torrt_command(['list_trackers'])
    trackers = [{'alias': alias} for alias in parse_tracker_lines(result['output'])] if result['success'] else []
    return render_template('trackers.html', trackers=trackers, result=result)


@app.route('/configure_tracker', methods=['POST'])
def configure_tracker():
    tracker_alias = request.form.get('tracker_alias')
    settings = build_settings([
        ('username', 'username'),
        ('password', 'password'),
    ])

    if not tracker_alias:
        flash('Tracker alias is required', 'danger')
        return redirect(url_for('list_trackers'))

    if not settings:
        flash('No settings provided to configure', 'warning')
        return redirect(url_for('list_trackers'))

    result = run_torrt_command(['configure_tracker', tracker_alias] + settings)
    flash_command_result(result, f'Tracker "{tracker_alias}" configured successfully!')
    return redirect(url_for('list_trackers'))


@app.route('/test_tracker/<alias>', methods=['POST'])
def test_tracker(alias):
    return jsonify({'success': True, 'message': f'Tracker {alias} test not implemented yet'})


@app.route('/torrents')
def list_torrents_view():
    result = run_torrt_command(['list_torrents'])
    torrents = parse_torrents_list(result['output']) if result['success'] else []
    return render_template('torrents.html', torrents=torrents, result=result)


@app.route('/notifiers')
def list_notifiers():
    result = run_torrt_command(['list_notifiers'])
    notifiers = [line.strip() for line in result['output'].splitlines() if line.strip()] if result['success'] else []
    return render_template('notifiers.html', notifiers=notifiers, result=result)


@app.route('/walk', methods=['POST'])
def walk():
    result = run_torrt_command(['walk'])
    torrents = parse_torrents_list(run_torrt_command(['list_torrents'])['output'])
    trackers = parse_tracker_lines(run_torrt_command(['list_trackers'])['output'])

    class SimpleForm:
        def __init__(self):
            self.hidden_tag = lambda: ''

    return render_template('index.html',
                           torrents=torrents,
                           trackers=trackers,
                           add_form=SimpleForm(),
                           walk_result=result)


@app.route('/add', methods=['GET', 'POST'])
def add_torrent():
    form = AddTorrentForm()
    if form.validate_on_submit():
        cmd_args = ['add_torrent', form.url.data]
        if form.download_path.data:
            cmd_args.extend(['-d', form.download_path.data])
        if form.content_layout.data:
            cmd_args.extend(['--params', f'contentLayout={form.content_layout.data}'])

        result = run_torrt_command(cmd_args)
        flash_command_result(result, 'Torrent added successfully!', 'Error adding torrent')
        return redirect(url_for('index'))

    return render_template('add.html', form=form)


@app.route('/remove', methods=['GET', 'POST'])
def remove_torrent():
    form = RemoveTorrentForm()
    if form.validate_on_submit():
        result = run_torrt_command(['remove_torrent', form.torrent_hash.data])
        flash_command_result(result, f'Torrent {form.torrent_hash.data} removed successfully!', 'Error removing torrent')
        return redirect(url_for('index'))

    return render_template('remove.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register_torrent():
    form = RegisterTorrentForm()
    if request.method == 'POST':
        torrent_hash = request.form.get('torrent_hash') or form.torrent_hash.data
        if torrent_hash:
            result = run_torrt_command(['register_torrent', torrent_hash])
            flash_command_result(result, f'Torrent {torrent_hash} registered successfully!', 'Error registering torrent')
            return redirect(url_for('index'))

    return render_template('register.html', form=form)


@app.route('/unregister', methods=['GET', 'POST'])
def unregister_torrent():
    form = RemoveTorrentForm()
    if form.validate_on_submit():
        result = run_torrt_command(['unregister_torrent', form.torrent_hash.data])
        flash_command_result(result, f'Torrent {form.torrent_hash.data} unregistered successfully!', 'Error unregistering torrent')
        return redirect(url_for('index'))

    return render_template('unregister.html', form=form)


@app.route('/set_walk_interval', methods=['GET', 'POST'])
def set_walk_interval():
    if request.method == 'POST':
        walk_interval = request.form.get('walk_interval')
        if not walk_interval:
            flash('Walk interval is required', 'danger')
            return redirect(url_for('set_walk_interval'))

        try:
            interval = int(walk_interval)
            if interval <= 0:
                flash('Interval must be greater than 0', 'danger')
                return redirect(url_for('set_walk_interval'))

            result = run_torrt_command(['set_walk_interval', str(interval)])
            flash_command_result(result, f'Walk interval set to {interval} hours successfully!', 'Error setting walk interval')
        except ValueError:
            flash('Please enter a valid number', 'danger')

        return redirect(url_for('set_walk_interval'))

    current_interval = get_current_walk_interval()
    return render_template('set_walk_interval.html', current_interval=current_interval)


@app.route('/api/<command>')
def api_command(command):
    valid_commands = ['list_rpc', 'list_trackers', 'list_torrents', 'list_notifiers']
    if command not in valid_commands:
        return jsonify({'error': 'Invalid command'}), 400
    return jsonify(run_torrt_command([command]))


if __name__ == '__main__':
    debug_flag = os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    app.run(debug=debug_flag, host='0.0.0.0', port=app.config['PORT'])
