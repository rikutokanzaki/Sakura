from dotenv import load_dotenv
from flask import Blueprint, request, abort, render_template, jsonify, current_app
from app.controllers import docker_manager, session_manager
from app.utils import flatten
import os
import json
import ipaddress
import socket

bp = Blueprint('main', __name__)

load_dotenv()
allowed_networks = [n.strip() for n in os.getenv("ALLOWED_NETWORKS", "").split(",") if n.strip()]

resolved_allowed_networks = []

try:
  hostname = socket.gethostname()
  ip = socket.gethostbyname(hostname)
  network = ipaddress.ip_network(f"{ip}/24", strict=False)
  resolved_allowed_networks.append(network)
  print(f"[ALLOW] Launcher self-resolved network: {network}")
except socket.gaierror as e:
  print(f"[DENY] Could not resolve self IP: {e}")

for addr in allowed_networks:
  addr = addr.strip()
  if not addr:
    continue
  try:
    network = ipaddress.ip_network(addr, strict=False)
    resolved_allowed_networks.append(network)
    print(f"[ALLOW] Parsed network: {network}")
    continue
  except ValueError:
    pass
  
  try:
    ip = socket.gethostbyname(addr)
    network = ipaddress.ip_network(f"{ip}/32", strict=False)
    resolved_allowed_networks.append(network)
    print(f"[ALLOW] Resolved {addr} to {network}")
  except socket.gaierror as e:
      print(f"[DENY] Invalid network or hostname {addr}")

@bp.route('/')
def index():
  return render_template("index.html")

@bp.route('/api/logs/snare', methods=['GET'])
def get_snare_logs():
  file_path = os.path.join(os.path.dirname(__file__), '../data/tanner/log/tanner_report.json')

  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      logs = [json.loads(line) for line in f if line.strip()]

    flat_logs = [flatten.flatten_dict(log) for log in logs]

    return jsonify(flat_logs)
  except FileNotFoundError:
    return jsonify({'error': 'tanner_report.log not found'}), 404

@bp.route('/api/logs/cowrie', methods=['GET'])
def get_cowrie_logs():
  file_path = os.path.join(os.path.dirname(__file__), '../data/cowrie/cowrie.json')

  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      logs = [json.loads(line) for line in f if line.strip()]
    return jsonify(logs)
  except FileNotFoundError:
    return jsonify({'error': 'cowrie.json not found'}), 404

@bp.route('/trigger/snare', methods=['POST'])
def trigger_snare():
  session_manager.update_session("snare")

  with session_manager._services["snare"].pause_lock:
    if not docker_manager.is_service_running("snare"):
      docker_manager.unpause_services(["snare","tanner_redis", "tanner_phpox", "tanner_api", "tanner"])
    session_manager.update_session("snare")
  
  return "HTTP Honeypot Triggered", 200

@bp.route('/trigger/cowrie', methods=['POST'])
def trigger_cowrie():
  session_manager.update_session("cowrie")

  with session_manager._services["cowrie"].pause_lock:
    if not docker_manager.is_service_running("cowrie"):
      docker_manager.unpause_services(["cowrie"])
    session_manager.update_session("cowrie")
  
  return "SSH Honeypot Triggered", 200

@bp.before_request
def restrict_ip():
  try:
    forwarded_for = request.headers.get('X-Forwarded-For')
    current_app.logger.info(f"X-Forwarded-For: {forwarded_for}")

    remote_ip = request.remote_addr
    remote_addr = ipaddress.ip_address(remote_ip)
    current_app.logger.info(f"Remote address: {remote_addr}")

    for ip_network in resolved_allowed_networks:
      if remote_addr in ip_network:
        current_app.logger.info(f"Allowed: {remote_addr} in {ip_network}")
        return
  except Exception as e:
    current_app.logger.error(f"Error in IP check: {e}")

  return abort(403, "Access denied from your IP address.")
