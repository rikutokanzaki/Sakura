from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from app.routes import bp
import logging
import os

logging.basicConfig(
  level=logging.WARNING,
  format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)

def create_app():
  app = Flask(__name__)
  app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

  dispatcher_mode = os.getenv("DISPATCHER_MODE", "dynamic").lower()
  logger.info("Creating app with DISPATCHER_MODE: %s", dispatcher_mode)

  app.config['dispatcher_mode'] = dispatcher_mode

  app.register_blueprint(bp)

  return app
