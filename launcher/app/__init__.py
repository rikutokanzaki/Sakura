from flask import Flask

def create_app():
  app = Flask(__name__, static_url_path='/static', static_folder='static')

  from app.routes import bp
  app.register_blueprint(bp)

  return app