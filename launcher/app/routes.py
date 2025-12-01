from dotenv import load_dotenv
from flask import Blueprint, request, abort, render_template, jsonify, current_app
from app.controllers import docker_manager, session_manager
from app.utils import flatten
import ipaddress
import logging
import os
import socket
import json

bp = Blueprint('main', __name__)

logger = logging.getLogger(__name__)

load_dotenv()
allowed_networks = [n.strip() for n in os.getenv("ALLOWED_NETWORKS", "").split(",") if n.strip()]

resolved_allowed_networks = []

try:
  hostname = socket.gethostname()
  ip = socket.gethostbyname(hostname)
  network = ipaddress.ip_network(f"{ip}/24", strict=False)
  resolved_allowed_networks.append(network)
  logger.info("Launcher self-resolved network: %s", network)
except socket.gaierror as e:
  logger.warning("Could not resolve self IP: %s", e)

for addr in allowed_networks:
  addr = addr.strip()
  if not addr:
    continue
  try:
    network = ipaddress.ip_network(addr, strict=False)
    resolved_allowed_networks.append(network)
    logger.info("Parsed network: %s", network)
    continue
  except ValueError:
    pass

  try:
    ip = socket.gethostbyname(addr)
    network = ipaddress.ip_network(f"{ip}/32", strict=False)
    resolved_allowed_networks.append(network)
    logger.info("Resolved %s to %s", addr, network)
  except socket.gaierror:
    logger.warning("Invalid network or hostname %s", addr)

@bp.route('/')
def index():
  return render_template("index.html")

@bp.route('/api/logs/openresty', methods=['GET'])
def get_openresty_logs():
  file_path = os.path.join(os.path.dirname(__file__), '/data/openresty/access.log')

  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      logs = [json.loads(line) for line in f if line.strip()]

    flat_logs = [flatten.flatten_dict(log) for log in logs]

    return jsonify(flat_logs)
  except FileNotFoundError:
    return jsonify({'error': 'log.json not found'}), 404

@bp.route('/api/logs/paramiko', methods=['GET'])
def get_paramiko_logs():
  file_path = os.path.join(os.path.dirname(__file__), '/data/paramiko/paramiko.log')

  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      logs = [json.loads(line) for line in f if line.strip()]

    flat_logs = [flatten.flatten_dict(log) for log in logs]

    return jsonify(flat_logs)
  except FileNotFoundError:
    return jsonify({'error': 'paramiko.log not found'}), 404

@bp.route('/api/logs/heralding', methods=['GET'])
def get_heralding_logs():
  file_path = os.path.join(os.path.dirname(__file__), '/data/heralding/log_session.json')

  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      logs = [json.loads(line) for line in f if line.strip()]

    flat_logs = [flatten.flatten_dict(log) for log in logs]

    return jsonify(flat_logs)
  except FileNotFoundError:
    return jsonify({'error': 'log.json not found'}), 404

@bp.route('/api/logs/wordpot', methods=['GET'])
def get_wordpot_logs():
  file_path = '/data/wordpot/log/wordpot.log'

  entries = []
  try:
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
      for raw in f:
        line = raw.strip()
        if not line:
          continue

        try:
          obj = json.loads(line)
        except json.JSONDecodeError:
          continue

        if isinstance(obj, dict):
          entries.append(flatten.flatten_dict(obj))

    return jsonify(entries)
  except FileNotFoundError:
    return jsonify({'error': 'wordpot.log not found'}), 404

@bp.route('/api/logs/h0neytr4p', methods=['GET'])
def get_h0neytr4p_logs():
  file_path = os.path.join(os.path.dirname(__file__), '/data/h0neytr4p/log/log.json')

  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      logs = [json.loads(line) for line in f if line.strip()]

    flat_logs = [flatten.flatten_dict(log) for log in logs]

    return jsonify(flat_logs)
  except FileNotFoundError:
    return jsonify({'error': 'log.json not found'}), 404

@bp.route('/api/logs/snare', methods=['GET'])
def get_snare_logs():
  file_path = os.path.join(os.path.dirname(__file__), '/data/tanner/log/tanner_report.json')

  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      logs = [json.loads(line) for line in f if line.strip()]

    flat_logs = [flatten.flatten_dict(log) for log in logs]

    return jsonify(flat_logs)
  except FileNotFoundError:
    return jsonify({'error': 'tanner_report.log not found'}), 404

@bp.route('/api/logs/cowrie', methods=['GET'])
def get_cowrie_logs():
  file_path = os.path.join(os.path.dirname(__file__), '/data/cowrie/cowrie.json')

  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      logs = [json.loads(line) for line in f if line.strip()]
    return jsonify(logs)
  except FileNotFoundError:
    return jsonify({'error': 'cowrie.json not found'}), 404

@bp.route('/trigger/heralding', methods=['POST'])
def trigger_heralding():
  session_manager.update_session("heralding")

  with session_manager._services["heralding"].stop_lock:
    if not docker_manager.is_service_running("heralding"):
      docker_manager.start_services(["heralding"])
    session_manager.update_session("heralding")

  return "HTTP Honeypot Triggered", 200

@bp.route('/trigger/wordpot', methods=['POST'])
def trigger_wordpot():
  session_manager.update_session("wordpot")

  with session_manager._services["wordpot"].stop_lock:
    if not docker_manager.is_service_running("wordpot"):
      docker_manager.start_services(["wordpot"])
    session_manager.update_session("wordpot")

  return "HTTP Honeypot Triggered", 200

@bp.route('/trigger/h0neytr4p', methods=['POST'])
def trigger_h0neytr4p():
  session_manager.update_session("h0neytr4p")

  with session_manager._services["h0neytr4p"].stop_lock:
    if not docker_manager.is_service_running("h0neytr4p"):
      docker_manager.start_services(["h0neytr4p"])
    session_manager.update_session("h0neytr4p")

  return "HTTP Honeypot Triggered", 200

@bp.route('/trigger/snare', methods=['POST'])
def trigger_snare():
  session_manager.update_session("snare")

  with session_manager._services["snare"].stop_lock:
    if not docker_manager.is_service_running("snare"):
      docker_manager.start_services(["snare","tanner_redis", "tanner_phpox", "tanner_api", "tanner"])
    session_manager.update_session("snare")

  return "HTTP Honeypot Triggered", 200

@bp.route('/trigger/cowrie', methods=['POST'])
def trigger_cowrie():
  session_manager.update_session("cowrie")

  with session_manager._services["cowrie"].stop_lock:
    if not docker_manager.is_service_running("cowrie"):
      docker_manager.start_services(["cowrie"])
    session_manager.update_session("cowrie")

  return "SSH Honeypot Triggered", 200

@bp.route('/session/update/cowrie', methods=['POST'])
def update_cowrie_session():
  session_manager.update_session("cowrie")
  return "Updated cowrie session", 200

def _ensure_session(service_name: str, persist: bool = False):
  session_manager.ensure_session(service_name, persist=persist)
  return session_manager._services[service_name]

@bp.route('/trigger-infty/heralding', methods=['POST'])
def trigger_infty_heralding():
  session_manager.update_session("heralding", persist=True)

  with session_manager._services["heralding"].stop_lock:
    if not docker_manager.is_service_running("heralding"):
      docker_manager.start_services(["heralding"])
  return "HTTP Honeypot Triggered", 200

@bp.route('/trigger-infty/wordpot', methods=['POST'])
def trigger_infty_wordpot():
  session_manager.update_session("wordpot", persist=True)

  with session_manager._services["wordpot"].stop_lock:
    if not docker_manager.is_service_running("wordpot"):
      docker_manager.start_services(["wordpot"])
  return "HTTP Honeypot Triggered", 200

@bp.route('/trigger-infty/h0neytr4p', methods=['POST'])
def trigger_infty_h0neytr4p():
  session_manager.update_session("h0neytr4p", persist=True)

  with session_manager._services["h0neytr4p"].stop_lock:
    if not docker_manager.is_service_running("h0neytr4p"):
      docker_manager.start_services(["h0neytr4p"])
  return "HTTP Honeypot Triggered", 200

@bp.route('/trigger-infty/snare', methods=['POST'])
def trigger_infty_snare():
  session_manager.update_session("snare", persist=True)

  with session_manager._services["snare"].stop_lock:
    if not docker_manager.is_service_running("snare"):
      docker_manager.start_services(["snare","tanner_redis", "tanner_phpox", "tanner_api", "tanner"])
  return "HTTP Honeypot Triggered", 200

@bp.route('/trigger-infty/cowrie', methods=['POST'])
def trigger_infty_cowrie():
  session_manager.update_session("cowrie", persist=True)

  with session_manager._services["cowrie"].stop_lock:
    if not docker_manager.is_service_running("cowrie"):
      docker_manager.start_services(["cowrie"])
  return "SSH Honeypot Triggered", 200

@bp.route('/stop/heralding', methods=['POST'])
def stop_heralding():
  _ensure_session("heralding")

  with session_manager._services["heralding"].stop_lock:
    if docker_manager.is_service_running("heralding"):
      docker_manager.stop_services(["heralding"])
  return "HTTP Honeypot Triggered", 200

@bp.route('/stop/wordpot', methods=['POST'])
def stop_wordpot():
  _ensure_session("wordpot")

  with session_manager._services["wordpot"].stop_lock:
    if docker_manager.is_service_running("wordpot"):
      docker_manager.stop_services(["wordpot"])
  return "HTTP Honeypot Triggered", 200

@bp.route('/stop/h0neytr4p', methods=['POST'])
def stop_h0neytr4p():
  _ensure_session("h0neytr4p")

  with session_manager._services["h0neytr4p"].stop_lock:
    if docker_manager.is_service_running("h0neytr4p"):
      docker_manager.stop_services(["h0neytr4p"])
  return "HTTP Honeypot Triggered", 200

@bp.route('/stop/snare', methods=['POST'])
def stop_snare():
  _ensure_session("snare")

  with session_manager._services["snare"].stop_lock:
    if docker_manager.is_service_running("snare"):
      docker_manager.stop_services(["snare","tanner_redis", "tanner_phpox", "tanner_api", "tanner"])
  return "HTTP Honeypot Triggered", 200

@bp.route('/stop/cowrie', methods=['POST'])
def stop_cowrie():
  _ensure_session("cowrie")

  with session_manager._services["cowrie"].stop_lock:
    if docker_manager.is_service_running("cowrie"):
      docker_manager.stop_services(["cowrie"])
  return "SSH Honeypot Triggered", 200

@bp.before_request
def restrict_ip():
  try:
    remote_ip = request.remote_addr
    remote_addr = ipaddress.ip_address(remote_ip)

    for ip_network in resolved_allowed_networks:
      if remote_addr in ip_network:
        current_app.logger.info(f"Allowed: {remote_addr} in {ip_network}")
        return
  except Exception as e:
    current_app.logger.error(f"Error in IP check: {e}")

  return abort(403, "Access denied from your IP address.")
