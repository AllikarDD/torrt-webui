import os

from flask import current_app, render_template, redirect, url_for
from src.commands import get_current_walk_interval
from src.forms import AddTorrentForm, RemoveTorrentForm, RegisterTorrentForm


def index():
    add_form = AddTorrentForm()
    remove_form = RemoveTorrentForm()
    unregister_form = RemoveTorrentForm()
    register_form = RegisterTorrentForm()

    return render_template(
        'index.html',
        add_form=add_form,
        remove_form=remove_form,
        unregister_form=unregister_form,
        register_form=register_form,
    )


def list_rpc():
    return render_template('rpc.html', rpc_list=[], result={'success': True, 'output': ''})


def configure_rpc():
    return render_template('rpc.html', rpc_list=[], result={'success': True, 'output': ''})


def enable_rpc(alias):
    return redirect(url_for('list_rpc'))


def disable_rpc(alias):
    return redirect(url_for('list_rpc'))


def list_trackers():
    return render_template('trackers.html', trackers=[], result={'success': True, 'output': ''})


def configure_tracker():
    return render_template('trackers.html', trackers=[], result={'success': True, 'output': ''})


def test_tracker(alias):
    return redirect(url_for('list_trackers'))


def list_torrents_view():
    return render_template('torrents.html', torrents=[], result={'success': True, 'output': ''})


def list_notifiers():
    return render_template('notifiers.html', notifiers=[], result={'success': True, 'output': ''})


def walk():
    return render_template('walk.html')


def add_torrent():
    form = AddTorrentForm()
    return render_template('add.html', form=form)


def remove_torrent():
    form = RemoveTorrentForm()
    return render_template('remove.html', form=form)


def register_torrent():
    form = RegisterTorrentForm()
    return render_template('register.html', form=form)


def unregister_torrent():
    form = RemoveTorrentForm()
    return render_template('unregister.html', form=form)


def set_walk_interval():
    current_interval = get_current_walk_interval()
    return render_template('set_walk_interval.html', current_interval=current_interval)


def tail_log_file(log_file, max_lines=200):
    if not log_file:
        return None, 'Log file path is not configured.'

    log_file = os.path.expanduser(log_file)
    try:
        with open(log_file, 'rb') as file:
            file.seek(0, os.SEEK_END)
            buffer = bytearray()
            block_size = 1024
            while file.tell() > 0 and buffer.count(b"\n") <= max_lines:
                seek_offset = min(file.tell(), block_size)
                file.seek(-seek_offset, os.SEEK_CUR)
                buffer[0:0] = file.read(seek_offset)
                file.seek(-seek_offset, os.SEEK_CUR)
                if file.tell() == 0:
                    break
            lines = buffer.splitlines()
            if len(lines) > max_lines:
                lines = lines[-max_lines:]
            text = b"\n".join(lines).decode('utf-8', errors='replace')
            return text, None
    except OSError as exc:
        return None, str(exc)


def logs():
    log_file = current_app.config.get('LOG_FILE')
    log_text, error = tail_log_file(log_file)
    return render_template('logs.html', log_file=log_file, log_text=log_text, error=error)


def favicon():
    from flask import send_from_directory
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')


def register_routes(app):
    """Register all routes with the Flask app."""
    app.add_url_rule('/', 'index', index)
    app.add_url_rule('/favicon.ico', 'favicon', favicon)
    app.add_url_rule('/rpc', 'list_rpc', list_rpc)
    app.add_url_rule('/configure_rpc', 'configure_rpc', configure_rpc)
    app.add_url_rule('/enable_rpc/<alias>', 'enable_rpc', enable_rpc)
    app.add_url_rule('/disable_rpc/<alias>', 'disable_rpc', disable_rpc)
    app.add_url_rule('/trackers', 'list_trackers', list_trackers)
    app.add_url_rule('/configure_tracker', 'configure_tracker', configure_tracker)
    app.add_url_rule('/test_tracker/<alias>', 'test_tracker', test_tracker)
    app.add_url_rule('/torrents', 'list_torrents_view', list_torrents_view)
    app.add_url_rule('/notifiers', 'list_notifiers', list_notifiers)
    app.add_url_rule('/walk', 'walk', walk)
    app.add_url_rule('/add', 'add_torrent', add_torrent)
    app.add_url_rule('/remove', 'remove_torrent', remove_torrent)
    app.add_url_rule('/register', 'register_torrent', register_torrent)
    app.add_url_rule('/unregister', 'unregister_torrent', unregister_torrent)
    app.add_url_rule('/set_walk_interval', 'set_walk_interval', set_walk_interval)
    app.add_url_rule('/logs', 'logs', logs)
