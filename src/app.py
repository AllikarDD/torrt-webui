import os
from flask import Flask

from src.config import configure_app
import src.views as views  # Import views to register routes

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
logger = configure_app(app)

# Register all routes
views.register_routes(app)

if __name__ == '__main__':
    debug_flag = os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    app.run(debug=debug_flag, host='0.0.0.0', port=app.config['PORT'])
