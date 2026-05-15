import os
from flask import Flask

from src.config import configure_app
import src.views as views  # Import views to register routes

app = Flask(__name__)
logger = configure_app(app)

# Register all routes
views.register_routes(app)

if __name__ == '__main__':
    debug_flag = os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
    app.run(debug=debug_flag, host='0.0.0.0', port=app.config['PORT'])
