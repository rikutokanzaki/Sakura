from dotenv import load_dotenv
from flask import Blueprint, request, abort, render_template, jsonify, current_app
from app.controller import docker_manager, session_manager
import os
import json
import ipaddress
import socket

bp = Blueprint('main', __name__)

load_dotenv()
allowed_networks = [n.strip() for n in os.getenv("ALLOWED_NETWORKS", "").split(",") if n.strip()]

resolved_allowed_networks = []

for addr in os.getenv("ALLOWED_NETWORKS", "").split(","):
  addr = addr.strip()
  if not addr:
    continue
  try:
    ip = socket.gethostbyname(addr)
    network = ipaddress.ip_network(f"{ip}/32", strict=False)
    resolved_allowed_networks.append(network)
    print(f"[ALLOW] Resolved {addr} to {network}")
  except socket.gaierror:
    try:
      if "/" not in addr:
        addr += "/32"
      network = ipaddress.ip_network(addr, strict=False)
      resolved_allowed_networks.append(network)
      print(f"[ALLOW] Parsed network: {network}")
    except ValueError as e:
      print(f"Invalid network {addr}: {e}")

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

@bp.route('/trigger/cowrie', methods=['POST'])
def trigger_cowrie():
  session_manager.update_session("cowrie")

  with session_manager._services["cowrie"].pause_lock:
    if not docker_manager.is_service_running("cowrie"):
      docker_manager.unpause_service("cowrie")
  
  return "SSH Honeypot Triggered", 200

@bp.before_request
def before_request():
  restricted_paths = ['/', '/api/logs/cowrie']
  if request.path not in restricted_paths:
    return

  try:
    remote_ip = request.remote_addr or '0.0.0.0'
    remote_addr = ipaddress.ip_address(remote_ip)
    current_app.logger.info(f"Remote address: {remote_addr}")

    for ip_network in resolved_allowed_networks:
      if remote_addr in ip_network:
        current_app.logger.info(f"Allowed: {remote_addr} in {ip_network}")
        return
  except Exception as e:
    current_app.logger.error(f"Error in IP check: {e}")

  return abort(403, "Access denied from your IP address")
