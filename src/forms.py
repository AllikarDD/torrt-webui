from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, URL


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