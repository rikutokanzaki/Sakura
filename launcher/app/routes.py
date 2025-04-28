from flask import Blueprint, request
from app.controller import docker_manager, session_manager

bp = Blueprint('main', __name__)

@bp.route('/trigger', methods=['POST'])
def trigger():
  session_manager.update_session()

  with session_manager.pause_lock:
    if not docker_manager.is_service_running("http-honeypot"):
      docker_manager.unpause_service("http-honeypot")
  
  return "Triggered", 200