from flask import Blueprint, request
from app.controller import docker_manager, session_manager

bp = Blueprint('main', __name__)

@bp.route('/trigger/http', methods=['POST'])
def trigger_http():
  session_manager.update_session("http-honeypot")

  with session_manager._services["http-honeypot"].pause_lock:
    if not docker_manager.is_service_running("http-honeypot"):
      docker_manager.unpause_service("http-honeypot")
  
  return "HTTP Honeypot Triggered", 200

@bp.route('/trigger/ssh', methods=['POST'])
def trigger_ssh():
  session_manager.update_session("ssh-honeypot")

  with session_manager._services["ssh-honeypot"].pause_lock:
    if not docker_manager.is_service_running("ssh-honeypot"):
      docker_manager.unpause_service("ssh-honeypot")
  
  return "SSH Honeypot Triggered", 200