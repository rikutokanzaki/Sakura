from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
import os

def create_app():
  app = Flask(__name__)
  app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)

  from app.routes import bp
  app.register_blueprint(bp)

  return app
