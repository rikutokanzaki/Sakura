from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from app.routes import bp
import logging

logging.basicConfig(
  level=logging.WARNING,
  format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

def create_app():
  app = Flask(__name__)
  app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

  app.register_blueprint(bp)

  return app
