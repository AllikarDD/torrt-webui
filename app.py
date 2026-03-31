# app.py
import os
import subprocess
import json
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, TextAreaField
from wtforms.validators import DataRequired, URL
import logging

app = Flask(__name__)
app.config['PORT'] = 5000
app.config['TORRT_PATH'] = 'torrt'  # or full path to torrt executable
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_current_walk_interval():
    """Try to get current walk interval from torrt config"""
    config_path = os.path.expanduser('~/.config/torrt/config.py')
    try:
        with open(config_path, 'r') as f:
            content = f.read()
            # Look for WALK_INTERVAL setting
            import re
            match = re.search(r'WALK_INTERVAL\s*=\s*(\d+(?:\.\d+)?)', content)
            if match:
                return float(match.group(1))
    except:
        pass
    return None

def run_torrt_command(cmd_args):
    """Execute torrt command and return output"""
    try:
        cmd = [app.config['TORRT_PATH']] + cmd_args
        logger.debug(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        # torrt outputs to stderr, combine both or use stderr
        output = result.stderr if result.stderr else result.stdout

        if result.returncode != 0:
            logger.error(f"Command failed: {output}")
            return {'success': False, 'output': output, 'error': output}

        return {'success': True, 'output': output}
    except subprocess.TimeoutExpired:
        return {'success': False, 'output': 'Command timed out', 'error': 'Timeout'}
    except Exception as e:
        logger.exception("Error running torrt command")
        return {'success': False, 'output': str(e), 'error': str(e)}

def parse_torrents_list(output):
    """Parse torrt list output into structured data"""
    torrents = []
    lines = output.strip().split('\n')

    for line in lines:
        line = line.strip()
        if line and not line.startswith('INFO: walk'):
            # Remove "INFO: " prefix if present
            if line.startswith('INFO:'):
                line = line[5:].strip()

            parts = line.split('\t')
            if len(parts) >= 2:
                torrents.append({
                    'hash': parts[0].strip(),
                    'name': parts[1].strip(),
                    'tracker': parts[2].strip() if len(parts) > 2 else 'N/A'
                })

    return torrents

class AddTorrentForm(FlaskForm):
    """Form for adding torrents"""
    url = StringField('Torrent URL', validators=[DataRequired(), URL()])
    download_path = StringField('Download Path (optional)', validators=[])
    content_layout = SelectField('Content Layout (for qBittorrent)', choices=[
        ('', 'Use client default'),
        ('NoSubfolder', 'No Subfolder - Save files directly'),
        ('CreateSubfolder', 'Create Subfolder - Create folder with torrent name'),
        ('Original', 'Original - Use structure defined in torrent file')
    ], validators=[])
    submit = SubmitField('Add Torrent')

class RemoveTorrentForm(FlaskForm):
    """Form for removing torrents"""
    torrent_hash = StringField('Torrent Hash', validators=[DataRequired()])
    submit = SubmitField('Remove Torrent')

class RegisterTorrentForm(FlaskForm):
    """Form for registering existing torrents"""
    torrent_hash = StringField('Torrent Hash', validators=[DataRequired()])
    tracker_alias = SelectField('Tracker', choices=[], validators=[DataRequired()])
    submit = SubmitField('Register Torrent')

@app.route('/')
def index():
    """Home page showing all functionality"""
    # Get torrents
    torrents_result = run_torrt_command(['list_torrents'])
    torrents = []
    if torrents_result['success']:
        torrents = parse_torrents_list(torrents_result['output'])

    # Get trackers for register form
    trackers_result = run_torrt_command(['list_trackers'])
    trackers = []
    if trackers_result['success']:
        trackers = [t.strip() for t in trackers_result['output'].split('\n') if t.strip()]

    # Create forms for each action
    class SimpleForm:
        def __init__(self):
            self.hidden_tag = lambda: ''

    add_form = SimpleForm()

    return render_template('index.html',
                           torrents=torrents,
                           trackers=trackers,
                           add_form=add_form,
                           walk_result=None)

@app.route('/rpc')
def list_rpc():
    """Show known RPCs aliases with their status"""
    result = run_torrt_command(['list_rpc'])

    rpc_list = []
    if result['success']:
        # Parse output - torrt list_rpc shows aliases
        aliases = [line.strip() for line in result['output'].split('\n') if line.strip()]

        # For each alias, check if it's enabled
        for alias in aliases:
            rpc_list.append({
                'alias': alias
            })

    return render_template('rpc.html', rpc_list=rpc_list, result=result)


@app.route('/configure_rpc', methods=['POST'])
def configure_rpc():
    """Configure RPC client settings"""
    action = request.form.get('action')
    rpc_alias = request.form.get('rpc_alias')

    if action == 'add':
        # Build settings from form
        settings = []
        if request.form.get('url'):
            settings.append(f"url={request.form.get('url')}")
        if request.form.get('host'):
            settings.append(f"host={request.form.get('host')}")
        if request.form.get('port'):
            settings.append(f"port={request.form.get('port')}")
        if request.form.get('username'):
            settings.append(f"user={request.form.get('username')}")
        if request.form.get('password'):
            settings.append(f"password={request.form.get('password')}")

        # First configure the RPC
        if settings:
            cmd_args = ['configure_rpc', rpc_alias] + settings
            result = run_torrt_command(cmd_args)

            if result['success']:
                flash(f'RPC client "{rpc_alias}" configured successfully!', 'success')
            else:
                flash(f'Error configuring RPC: {result["error"]}', 'danger')
                return redirect(url_for('list_rpc'))

        # Then enable it
        enable_result = run_torrt_command(['enable_rpc', rpc_alias])
        if enable_result['success']:
            flash(f'RPC client "{rpc_alias}" enabled successfully!', 'success')
        else:
            flash(f'RPC client configured but could not enable: {enable_result["error"]}', 'warning')

    elif action == 'configure':
        # Update existing RPC configuration
        settings = []
        if request.form.get('url'):
            settings.append(f"url={request.form.get('url')}")
        if request.form.get('host'):
            settings.append(f"host={request.form.get('host')}")
        if request.form.get('port'):
            settings.append(f"port={request.form.get('port')}")
        if request.form.get('username'):
            settings.append(f"user={request.form.get('username')}")
        if request.form.get('password'):
            settings.append(f"password={request.form.get('password')}")

        if settings:
            cmd_args = ['configure_rpc', rpc_alias] + settings
            result = run_torrt_command(cmd_args)

            if result['success']:
                flash(f'RPC client "{rpc_alias}" updated successfully!', 'success')
            else:
                flash(f'Error updating RPC: {result["error"]}', 'danger')

    return redirect(url_for('list_rpc'))


@app.route('/enable_rpc/<alias>', methods=['POST'])
def enable_rpc(alias):
    """Enable RPC client by alias"""
    result = run_torrt_command(['enable_rpc', alias])

    if result['success']:
        return jsonify({'success': True, 'message': f'RPC {alias} enabled'})
    else:
        return jsonify({'success': False, 'error': result['error']}), 400


@app.route('/disable_rpc/<alias>', methods=['POST'])
def disable_rpc(alias):
    """Disable RPC client by alias"""
    result = run_torrt_command(['disable_rpc', alias])

    if result['success']:
        return jsonify({'success': True, 'message': f'RPC {alias} disabled'})
    else:
        return jsonify({'success': False, 'error': result['error']}), 400

@app.route('/trackers')
def list_trackers():
    """Show known trackers aliases with configuration status"""
    result = run_torrt_command(['list_trackers'])

    trackers = []
    if result['success']:
        # Parse output - torrt list_trackers shows aliases
        aliases = [line.strip() for line in result['output'].split('\n') if line.strip()]

        # For each alias, check if it's configured
        # You might need to check torrt config to determine if credentials are set
        for alias in aliases:
            trackers.append({
                'alias': alias,
                'configured': False  # You can enhance this by checking config file
            })

    return render_template('trackers.html', trackers=trackers, result=result)


@app.route('/configure_tracker', methods=['POST'])
def configure_tracker():
    """Configure tracker settings (username/password)"""
    tracker_alias = request.form.get('tracker_alias')
    username = request.form.get('username')
    password = request.form.get('password')

    if not tracker_alias:
        flash('Tracker alias is required', 'danger')
        return redirect(url_for('list_trackers'))

    # Build settings list
    settings = []
    if username:
        settings.append(f"username={username}")
    if password:
        settings.append(f"password={password}")

    if not settings:
        flash('No settings provided to configure', 'warning')
        return redirect(url_for('list_trackers'))

    # Run configure_tracker command
    cmd_args = ['configure_tracker', tracker_alias] + settings
    result = run_torrt_command(cmd_args)

    if result['success']:
        flash(f'Tracker "{tracker_alias}" configured successfully!', 'success')
    else:
        flash(f'Error configuring tracker: {result["error"]}', 'danger')

    return redirect(url_for('list_trackers'))


# Optional: Add a route to test tracker configuration
@app.route('/test_tracker/<alias>', methods=['POST'])
def test_tracker(alias):
    """Test tracker configuration by trying to fetch something"""
    # This would require implementing a test method in torrt
    # For now, just return success
    return jsonify({'success': True, 'message': f'Tracker {alias} test not implemented yet'})

@app.route('/torrents')
def list_torrents():
    """Show torrents registered for updates"""
    result = run_torrt_command(['list_torrents'])

    torrents = []
    if result['success']:
        torrents = parse_torrents_list(result['output'])

    return render_template('torrents.html', torrents=torrents, result=result)

@app.route('/notifiers')
def list_notifiers():
    """Show configured notifiers"""
    result = run_torrt_command(['list_notifiers'])

    notifiers = []
    if result['success']:
        notifiers = [line.strip() for line in result['output'].split('\n') if line.strip()]

    return render_template('notifiers.html', notifiers=notifiers, result=result)

@app.route('/walk', methods=['POST'])
def walk():
    """Walk through registered torrents and perform automatic updates"""
    result = run_torrt_command(['walk'])

    # Get updated data for index page
    torrents_result = run_torrt_command(['list_torrents'])
    torrents = []
    if torrents_result['success']:
        torrents = parse_torrents_list(torrents_result['output'])

    trackers_result = run_torrt_command(['list_trackers'])
    trackers = []
    if trackers_result['success']:
        trackers = [t.strip() for t in trackers_result['output'].split('\n') if t.strip()]

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
    """Add torrent from URL both to torrt and torrent clients"""
    form = AddTorrentForm()

    if form.validate_on_submit():
        cmd_args = ['add_torrent', form.url.data]

        # Add download path if provided
        if form.download_path.data:
            cmd_args.extend(['-d', form.download_path.data])

        # Add content_layout as params if specified (for qBittorrent)
        if form.content_layout.data:
            params = f'contentLayout={form.content_layout.data}'
            cmd_args.extend(['--params', params])

        result = run_torrt_command(cmd_args)

        if result['success']:
            flash(f'Torrent added successfully!', 'success')
        else:
            flash(f'Error adding torrent: {result["error"]}', 'danger')

        return redirect(url_for('add_torrent'))

    return render_template('add.html', form=form)

@app.route('/remove', methods=['GET', 'POST'])
def remove_torrent():
    """Remove torrent by its hash both from torrt and torrent clients"""
    form = RemoveTorrentForm()

    if form.validate_on_submit():
        cmd_args = ['remove_torrent', form.torrent_hash.data]
        result = run_torrt_command(cmd_args)

        if result['success']:
            flash(f'Torrent {form.torrent_hash.data} removed successfully!', 'success')
        else:
            flash(f'Error removing torrent: {result["error"]}', 'danger')

        return redirect(url_for('remove_torrent'))

    return render_template('remove.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register_torrent():
    """Register torrent within torrt by its hash (for torrents already existing at torrent clients)"""
    form = RegisterTorrentForm()

    # Get available trackers
    tracker_result = run_torrt_command(['list_trackers'])

    if tracker_result['success']:
        form.tracker_alias.choices = [(t.strip(), t.strip()) for t in tracker_result['output'].split('\n') if t.strip()]

    if form.validate_on_submit():
        cmd_args = [
            'register_torrent',
            form.torrent_hash.data,
            '--tracker', form.tracker_alias.data
        ]
        result = run_torrt_command(cmd_args)

        if result['success']:
            flash(f'Torrent {form.torrent_hash.data} registered successfully!', 'success')
        else:
            flash(f'Error registering torrent: {result["error"]}', 'danger')

        return redirect(url_for('register_torrent'))

    return render_template('register.html', form=form)

@app.route('/unregister', methods=['GET', 'POST'])
def unregister_torrent():
    """Unregister torrent from torrt by its hash"""
    form = RemoveTorrentForm()  # Reuse the same form for hash input

    if form.validate_on_submit():
        cmd_args = ['unregister_torrent', form.torrent_hash.data]
        result = run_torrt_command(cmd_args)

        if result['success']:
            flash(f'Torrent {form.torrent_hash.data} unregistered successfully!', 'success')
        else:
            flash(f'Error unregistering torrent: {result["error"]}', 'danger')

        return redirect(url_for('unregister_torrent'))

    return render_template('unregister.html', form=form)

@app.route('/set_walk_interval', methods=['GET', 'POST'])
def set_walk_interval():
    """Set interval between consecutive torrent updates checks"""
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

            if result['success']:
                flash(f'Walk interval set to {interval} hours successfully!', 'success')
            else:
                flash(f'Error setting walk interval: {result["error"]}', 'danger')

        except ValueError:
            flash('Please enter a valid number', 'danger')

        return redirect(url_for('set_walk_interval'))

    current_interval = get_current_walk_interval()
    return render_template('set_walk_interval.html', current_interval=current_interval)

@app.route('/api/<command>')
def api_command(command):
    """REST API endpoint for commands"""
    valid_commands = [
        'list_rpc', 'list_trackers', 'list_torrents', 'list_notifiers'
    ]

    if command not in valid_commands:
        return jsonify({'error': 'Invalid command'}), 400

    result = run_torrt_command([command])
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=app.config['PORT'])