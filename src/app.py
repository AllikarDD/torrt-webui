import os
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from src.config import configure_app
import src.views as views  # Import views to register routes
import src.api as api  # Import API routes

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
logger = configure_app(app)

# Apply ProxyFix middleware to trust proxy headers (X-Forwarded-* headers from reverse proxy)
# This enables Flask to detect HTTPS, client IP, and original host from proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

# Register all routes
views.register_routes(app)
api.register_routes(app)

if __name__ == '__main__':
    debug_flag = os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    app.run(debug=debug_flag, host='0.0.0.0', port=app.config['PORT'])
