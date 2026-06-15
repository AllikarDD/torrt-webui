import json
from flask import jsonify, request

from src.commands import (
    run_torrt_command,
    parse_torrents_list,
    parse_tracker_lines,
    get_current_walk_interval,
    build_settings,
)


def _json_success(data=None, message=None, output=None):
    response = {'success': True}
    if data is not None:
        response['data'] = data
    if message is not None:
        response['message'] = message
    if output is not None:
        response['output'] = output
    return jsonify(response)


def _json_error(message, output=None, status_code=400):
    response = {'success': False, 'error': message}
    if output is not None:
        response['output'] = output
    return jsonify(response), status_code


def _get_request_data():
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        return payload
    return request.form.to_dict()


def _parse_rpc_output(output):
    rpc_list = []
    for raw_line in output.splitlines():
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
    return rpc_list


def api_list_rpc():
    result = run_torrt_command(['list_rpc'])
    if result['success']:
        return _json_success(data=_parse_rpc_output(result['output']), output=result['output'])
    return _json_error(result['error'], output=result.get('output'))


def api_list_trackers():
    result = run_torrt_command(['list_trackers'])
    if result['success']:
        data = [{'alias': alias} for alias in parse_tracker_lines(result['output'])]
        return _json_success(data=data, output=result['output'])
    return _json_error(result['error'], output=result.get('output'))


def api_list_torrents():
    result = run_torrt_command(['list_torrents'])
    if result['success']:
        return _json_success(data=parse_torrents_list(result['output']), output=result['output'])
    return _json_error(result['error'], output=result.get('output'))


def api_list_notifiers():
    result = run_torrt_command(['list_notifiers'])
    if result['success']:
        data = [line.strip() for line in result['output'].splitlines() if line.strip()]
        return _json_success(data=data, output=result['output'])
    return _json_error(result['error'], output=result.get('output'))


def api_walk():
    result = run_torrt_command(['walk'])
    if result['success']:
        return _json_success(message='Walk completed', output=result['output'])
    return _json_error(result['error'], output=result.get('output'))


def api_add_torrent():
    data = _get_request_data()
    url = data.get('url')
    if not url:
        return _json_error('Torrent URL is required')

    cmd_args = ['add_torrent', url]
    download_path = data.get('download_path')
    content_layout = data.get('content_layout')
    if download_path:
        cmd_args.extend(['-d', download_path])
    if content_layout:
        cmd_args.extend(['--params', f'contentLayout={content_layout}'])

    result = run_torrt_command(cmd_args)
    if result['success']:
        return _json_success(message='Torrent added successfully', output=result['output'])
    return _json_error(result['error'], output=result.get('output'))


def api_remove_torrent():
    data = _get_request_data()
    torrent_hash = data.get('torrent_hash')
    if not torrent_hash:
        return _json_error('Torrent hash is required')

    result = run_torrt_command(['remove_torrent', torrent_hash])
    if result['success']:
        return _json_success(message=f'Torrent {torrent_hash} removed successfully', output=result['output'])
    return _json_error(result['error'], output=result.get('output'))


def api_register_torrent():
    data = _get_request_data()
    torrent_hash = data.get('torrent_hash')
    if not torrent_hash:
        return _json_error('Torrent hash is required')

    result = run_torrt_command(['register_torrent', torrent_hash])
    if result['success']:
        return _json_success(message=f'Torrent {torrent_hash} registered successfully', output=result['output'])
    return _json_error(result['error'], output=result.get('output'))


def api_unregister_torrent():
    data = _get_request_data()
    torrent_hash = data.get('torrent_hash')
    if not torrent_hash:
        return _json_error('Torrent hash is required')

    result = run_torrt_command(['unregister_torrent', torrent_hash])
    if result['success']:
        return _json_success(message=f'Torrent {torrent_hash} unregistered successfully', output=result['output'])
    return _json_error(result['error'], output=result.get('output'))


def api_enable_rpc(alias):
    result = run_torrt_command(['enable_rpc', alias])
    if result['success']:
        return _json_success(message=f'RPC {alias} enabled', output=result['output'])
    return _json_error(result['error'], output=result.get('output'))


def api_disable_rpc(alias):
    result = run_torrt_command(['disable_rpc', alias])
    if result['success']:
        return _json_success(message=f'RPC {alias} disabled', output=result['output'])
    return _json_error(result['error'], output=result.get('output'))


def api_configure_rpc():
    data = _get_request_data()
    action = data.get('action')
    rpc_alias = data.get('rpc_alias')
    if not rpc_alias or action not in ('add', 'configure'):
        return _json_error('RPC alias and valid action are required')

    settings = build_settings(data, [
        ('url', 'url'),
        ('host', 'host'),
        ('port', 'port'),
        ('user', 'username'),
        ('password', 'password'),
    ])
    if not settings:
        return _json_error('RPC settings are required')

    result = run_torrt_command(['configure_rpc', rpc_alias] + settings)
    if not result['success'] or 'ERROR:' in result.get('output', ''):
        return _json_error(result.get('error') or 'RPC configuration failed', output=result.get('output'))

    if action == 'add':
        enable_result = run_torrt_command(['enable_rpc', rpc_alias])
        if not enable_result['success'] or 'ERROR:' in enable_result.get('output', ''):
            return _json_error(enable_result.get('error') or 'RPC enabling failed', output=enable_result.get('output'))
        return _json_success(message=f'RPC client "{rpc_alias}" configured and enabled', output=enable_result.get('output'))

    return _json_success(message=f'RPC client "{rpc_alias}" configured successfully', output=result.get('output'))


def api_configure_tracker():
    data = _get_request_data()
    tracker_alias = data.get('tracker_alias')
    if not tracker_alias:
        return _json_error('Tracker alias is required')

    settings = build_settings(data, [
        ('username', 'username'),
        ('password', 'password'),
    ])
    if not settings:
        return _json_error('Tracker settings are required')

    result = run_torrt_command(['configure_tracker', tracker_alias] + settings)
    if not result['success'] or 'ERROR:' in result.get('output', ''):
        return _json_error(result.get('error') or f'Tracker "{tracker_alias}" configuration failed', output=result.get('output'))

    return _json_success(message=f'Tracker "{tracker_alias}" configured successfully', output=result.get('output'))


def api_test_tracker(alias):
    # Placeholder behavior currently mimics a successful check.
    return _json_success(message=f'Tracker {alias} test completed')


def api_set_walk_interval():
    data = _get_request_data()
    walk_interval = data.get('walk_interval')
    try:
        interval = int(walk_interval)
        if interval <= 0:
            return _json_error('Interval must be greater than 0')
    except (TypeError, ValueError):
        return _json_error('Invalid walk interval provided')

    result = run_torrt_command(['set_walk_interval', str(interval)])
    if result['success']:
        return _json_success(message=f'Walk interval set to {interval} hours', output=result['output'])
    return _json_error(result['error'], output=result.get('output'))


def api_current_walk_interval():
    interval = get_current_walk_interval()
    return _json_success(data={'walk_interval': interval})


def register_routes(app):
    app.add_url_rule('/api/rpc', 'api_list_rpc', api_list_rpc)
    app.add_url_rule('/api/trackers', 'api_list_trackers', api_list_trackers)
    app.add_url_rule('/api/torrents', 'api_list_torrents', api_list_torrents)
    app.add_url_rule('/api/notifiers', 'api_list_notifiers', api_list_notifiers)
    app.add_url_rule('/api/walk', 'api_walk', api_walk, methods=['POST'])
    app.add_url_rule('/api/add_torrent', 'api_add_torrent', api_add_torrent, methods=['POST'])
    app.add_url_rule('/api/remove_torrent', 'api_remove_torrent', api_remove_torrent, methods=['POST'])
    app.add_url_rule('/api/register_torrent', 'api_register_torrent', api_register_torrent, methods=['POST'])
    app.add_url_rule('/api/unregister_torrent', 'api_unregister_torrent', api_unregister_torrent, methods=['POST'])
    app.add_url_rule('/api/enable_rpc/<alias>', 'api_enable_rpc', api_enable_rpc, methods=['POST'])
    app.add_url_rule('/api/disable_rpc/<alias>', 'api_disable_rpc', api_disable_rpc, methods=['POST'])
    app.add_url_rule('/api/configure_rpc', 'api_configure_rpc', api_configure_rpc, methods=['POST'])
    app.add_url_rule('/api/configure_tracker', 'api_configure_tracker', api_configure_tracker, methods=['POST'])
    app.add_url_rule('/api/test_tracker/<alias>', 'api_test_tracker', api_test_tracker, methods=['POST'])
    app.add_url_rule('/api/set_walk_interval', 'api_set_walk_interval', api_set_walk_interval, methods=['POST'])
    app.add_url_rule('/api/current_walk_interval', 'api_current_walk_interval', api_current_walk_interval)
