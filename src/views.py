from flask import render_template, request, jsonify, flash, redirect, url_for
from src.commands import (
    run_torrt_command,
    parse_torrents_list,
    parse_tracker_lines,
    get_current_walk_interval,
    build_settings,
    flash_command_result,
)
from src.forms import AddTorrentForm, RemoveTorrentForm, RegisterTorrentForm


def index():
    torrents_result = run_torrt_command(['list_torrents'])
    torrents = parse_torrents_list(torrents_result['output']) if torrents_result['success'] else []

    class SimpleForm:
        def __init__(self):
            self.hidden_tag = lambda: ''

    return render_template(
        'index.html',
        torrents=torrents,
        add_form=SimpleForm(),
        walk_result=None,
    )


def list_rpc():
    result = run_torrt_command(['list_rpc'])
    rpc_list = []

    if result['success']:
        for raw_line in result['output'].splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith('INFO:'):
                line = line[5:].strip()
                if not line:
                    continue

            parts = [part.strip() for part in line.split('\t') if part.strip()]
            if not parts:
                continue

            alias = parts[0]
            status = 'unknown'
            if len(parts) > 1 and '=' in parts[1]:
                status = parts[1].split('=', 1)[1].strip()
            rpc_list.append({'alias': alias, 'status': status})

    return render_template('rpc.html', rpc_list=rpc_list, result=result)


def configure_rpc():
    action = request.form.get('action')
    rpc_alias = request.form.get('rpc_alias')
    settings = build_settings([
        ('url', 'url'),
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


def enable_rpc(alias):
    result = run_torrt_command(['enable_rpc', alias])
    if result['success']:
        return jsonify({'success': True, 'message': f'RPC {alias} enabled'})
    return jsonify({'success': False, 'error': result['error']}), 400


def disable_rpc(alias):
    result = run_torrt_command(['disable_rpc', alias])
    if result['success']:
        return jsonify({'success': True, 'message': f'RPC {alias} disabled'})
    return jsonify({'success': False, 'error': result['error']}), 400


def list_trackers():
    result = run_torrt_command(['list_trackers'])
    trackers = [{'alias': alias} for alias in parse_tracker_lines(result['output'])] if result['success'] else []
    return render_template('trackers.html', trackers=trackers, result=result)


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


def test_tracker(alias):
    return jsonify({'success': True, 'message': f'Tracker {alias} test not implemented yet'})


def list_torrents_view():
    result = run_torrt_command(['list_torrents'])
    torrents = parse_torrents_list(result['output']) if result['success'] else []
    return render_template('torrents.html', torrents=torrents, result=result)


def list_notifiers():
    result = run_torrt_command(['list_notifiers'])
    notifiers = [line.strip() for line in result['output'].splitlines() if line.strip()] if result['success'] else []
    return render_template('notifiers.html', notifiers=notifiers, result=result)


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


def remove_torrent():
    form = RemoveTorrentForm()
    if form.validate_on_submit():
        result = run_torrt_command(['remove_torrent', form.torrent_hash.data])
        flash_command_result(result, f'Torrent {form.torrent_hash.data} removed successfully!', 'Error removing torrent')
        return redirect(url_for('index'))

    return render_template('remove.html', form=form)


def register_torrent():
    form = RegisterTorrentForm()
    if request.method == 'POST':
        torrent_hash = request.form.get('torrent_hash') or form.torrent_hash.data
        if torrent_hash:
            result = run_torrt_command(['register_torrent', torrent_hash])
            flash_command_result(result, f'Torrent {torrent_hash} registered successfully!', 'Error registering torrent')
            return redirect(url_for('index'))

    return render_template('register.html', form=form)


def unregister_torrent():
    form = RemoveTorrentForm()
    if form.validate_on_submit():
        result = run_torrt_command(['unregister_torrent', form.torrent_hash.data])
        flash_command_result(result, f'Torrent {form.torrent_hash.data} unregistered successfully!', 'Error unregistering torrent')
        return redirect(url_for('index'))

    return render_template('unregister.html', form=form)


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


def api_command(command):
    valid_commands = ['list_rpc', 'list_trackers', 'list_torrents', 'list_notifiers']
    if command not in valid_commands:
        return jsonify({'error': 'Invalid command'}), 400
    return jsonify(run_torrt_command([command]))


def favicon():
    from flask import send_from_directory
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')


def register_routes(app):
    """Register all routes with the Flask app."""
    app.add_url_rule('/', 'index', index)
    app.add_url_rule('/favicon.ico', 'favicon', favicon)
    app.add_url_rule('/rpc', 'list_rpc', list_rpc)
    app.add_url_rule('/configure_rpc', 'configure_rpc', configure_rpc, methods=['POST'])
    app.add_url_rule('/enable_rpc/<alias>', 'enable_rpc', enable_rpc, methods=['POST'])
    app.add_url_rule('/disable_rpc/<alias>', 'disable_rpc', disable_rpc, methods=['POST'])
    app.add_url_rule('/trackers', 'list_trackers', list_trackers)
    app.add_url_rule('/configure_tracker', 'configure_tracker', configure_tracker, methods=['POST'])
    app.add_url_rule('/test_tracker/<alias>', 'test_tracker', test_tracker, methods=['POST'])
    app.add_url_rule('/torrents', 'list_torrents_view', list_torrents_view)
    app.add_url_rule('/notifiers', 'list_notifiers', list_notifiers)
    app.add_url_rule('/walk', 'walk', walk, methods=['POST'])
    app.add_url_rule('/add', 'add_torrent', add_torrent, methods=['GET', 'POST'])
    app.add_url_rule('/remove', 'remove_torrent', remove_torrent, methods=['GET', 'POST'])
    app.add_url_rule('/register', 'register_torrent', register_torrent, methods=['GET', 'POST'])
    app.add_url_rule('/unregister', 'unregister_torrent', unregister_torrent, methods=['GET', 'POST'])
    app.add_url_rule('/set_walk_interval', 'set_walk_interval', set_walk_interval, methods=['GET', 'POST'])
    app.add_url_rule('/api/<command>', 'api_command', api_command)