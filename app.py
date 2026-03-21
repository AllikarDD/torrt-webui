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
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['TORRT_PATH'] = 'torrt'  # or full path to torrt executable

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
    rpc_alias = SelectField('Torrent Client', choices=[], validators=[DataRequired()])
    tracker_alias = SelectField('Tracker', choices=[], validators=[DataRequired()])
    download_path = StringField('Download Path (optional)', validators=[])
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
    """Home page showing available commands"""
    return render_template('index.html')

@app.route('/rpc')
def list_rpc():
    """Show known RPCs aliases"""
    result = run_torrt_command(['list_rpc'])

    rpc_list = []
    if result['success']:
        # Parse output - assuming it's a list of aliases
        rpc_list = [line.strip() for line in result['output'].split('\n') if line.strip()]

    return render_template('rpc.html', rpc_list=rpc_list, result=result)

@app.route('/trackers')
def list_trackers():
    """Show known trackers aliases"""
    result = run_torrt_command(['list_trackers'])

    trackers = []
    if result['success']:
        trackers = [line.strip() for line in result['output'].split('\n') if line.strip()]

    return render_template('trackers.html', trackers=trackers, result=result)

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

@app.route('/walk', methods=['GET', 'POST'])
def walk():
    """Walk through registered torrents and perform automatic updates"""
    if request.method == 'POST':
        result = run_torrt_command(['walk'])
        flash('Walk completed. Check results below.', 'info')
        return render_template('walk.html', result=result)

    return render_template('walk.html', result=None)

@app.route('/add', methods=['GET', 'POST'])
def add_torrent():
    """Add torrent from URL both to torrt and torrent clients"""
    form = AddTorrentForm()

    if form.validate_on_submit():
        cmd_args = ['add_torrent', form.url.data]

        # Add download path if provided
        if form.download_path.data:
            cmd_args.extend(['-d', form.download_path.data])

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
    app.run(debug=True, host='0.0.0.0', port=5000)