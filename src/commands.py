import os
import re
import subprocess
import logging
import shutil
from flask import current_app

logger = logging.getLogger(__name__)


def get_current_walk_interval():
    """Try to get current walk interval from torrt config."""
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
    """Execute torrt command and return output."""
    torrt_path = current_app.config['TORRT_PATH']
    resolved_path = torrt_path

    if not os.path.isabs(torrt_path):
        resolved_path = shutil.which(torrt_path)

    if not resolved_path or (os.path.isabs(torrt_path) and not os.path.exists(torrt_path)):
        logger.error('torrt executable not found: %s', torrt_path)
        return {
            'success': False,
            'output': '',
            'error': f'torrt executable not found: {torrt_path}'
        }

    cmd = [resolved_path] + cmd_args
    logger.debug('Running command: %s', ' '.join(cmd))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
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
    """Parse torrt list output into structured data."""
    torrents = []
    for raw_line in output.splitlines():
        line = raw_line.strip()

        if not line or line.startswith('INFO: walk'):
            continue
        if line.startswith('INFO:'):
            line = line[5:].strip()
        if not line:
            continue

        parts = [part.strip() for part in line.split('\t') if part.strip()]

        if len(parts) < 2:
            if raw_line.strip() and not raw_line.strip().startswith('INFO:'):
                logger.debug('Skipping unparsable torrent line: %s', raw_line)
            torrents.append({
                'hash': parts[0],
                'name': 'N/A',
                'tracker': 'N/A',
            })
            continue

        torrents.append({
            'hash': parts[0],
            'name': parts[1],
            'tracker': parts[2] if len(parts) > 2 else 'N/A',
        })

    return torrents


def parse_tracker_lines(output):
    """Parse tracker list output."""
    trackers = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('INFO:'):
            line = line[5:].strip()
        trackers.append(line)
    return trackers


def build_settings(data, fields):
    """Build settings list from a request payload or form-like data."""
    settings = []
    for key, field_name in fields:
        value = data.get(field_name)
        if value:
            settings.append(f'{key}={value}')
    return settings


def flash_command_result(result, success_message, failure_message=None):
    """Flash appropriate message based on command result."""
    from flask import flash
    if result['success']:
        if any(marker in result['output'] for marker in ('WARNING', 'ERROR')):
            flash(result['output'], 'danger')
        else:
            flash(success_message, 'success')
    else:
        flash(failure_message or result['error'], 'danger')
