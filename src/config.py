import os
import logging
from logging.handlers import RotatingFileHandler

def configure_app(app):
    """Configure Flask app with environment variables."""
    app.config.from_mapping(
        PORT=int(os.environ.get('TORRTWEBUI_PORT', 5000)),
        TORRT_PATH=os.environ.get('TORRTWEBUI_TORRT_PATH', 'torrt'),
        SECRET_KEY=os.environ.get('TORRTWEBUI_SECRET_KEY', 'your-secret-key-here-change-in-production'),
        LOG_FILE=os.environ.get('TORRTWEBUI_LOG_FILE', '/var/log/torrtwebui/log.txt'),
        LOG_LEVEL=os.environ.get('TORRTWEBUI_LOG_LEVEL', 'DEBUG').upper(),
    )

    # Set up logging
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
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    try:
        file_handler = RotatingFileHandler(log_file, maxBytes=10_000_000, backupCount=5)
        file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s'))
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    except OSError as exc:
        logging.getLogger(__name__).warning('Could not open log file %s (%s); falling back to console only', log_file, exc)

    return root_logger