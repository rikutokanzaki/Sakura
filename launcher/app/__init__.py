from flask import Flask
from app.controllers.log_observer import CowrieLogObserver
import os

log_observer = None

def create_app():
  global log_observer
  app = Flask(__name__)

  from app.routes import bp
  app.register_blueprint(bp)

  log_path = os.path.join(os.path.dirname(__file__), '/data/cowrie/cowrie.json')
  log_observer = CowrieLogObserver(log_path=log_path)
  log_observer.start()

  return app