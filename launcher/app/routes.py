from flask import Blueprint, request, render_template, jsonify
from app.controller import docker_manager, session_manager
import os
import json

bp = Blueprint('main', __name__, static_url_path='/static', static_folder='static')

@bp.route('/')
def index():
  return render_template("index.html")

@bp.route('/api/logs/cowrie', methods=['GET'])
def get_cowrie_logs():
  file_path = os.path.join(os.path.dirname(__file__), '../static/data/cowrie/cowrie.json')

  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      logs = [json.loads(line) for line in f if line.strip()]
    return jsonify(logs)
  except FileNotFoundError:
    return jsonify({'error': 'cowrie.json not found'}), 404

@bp.route('/trigger/http', methods=['POST'])
def trigger_http():
  session_manager.update_session("http-honeypot")

  with session_manager._services["http-honeypot"].pause_lock:
    if not docker_manager.is_service_running("http-honeypot"):
      docker_manager.unpause_service("http-honeypot")
  
  return "HTTP Honeypot Triggered", 200

@bp.route('/trigger/ssh', methods=['POST'])
def trigger_ssh():
  session_manager.update_session("cowrie")

  with session_manager._services["cowrie"].pause_lock:
    if not docker_manager.is_service_running("cowrie"):
      docker_manager.unpause_service("cowrie")
  
  return "SSH Honeypot Triggered", 200