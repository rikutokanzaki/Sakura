import time
import docker
import socket

MAX_WAIT_SECONDS = 10
client = docker.from_env()

LINKED_SERVICES = {
  "snare": ["snare", "tanner_redis", "tanner_phpox", "tanner_api", "tanner"],
}

WAIT_CONFIG = {
  "cowrie": {"host": "cowrie", "port": 2222, "timeout": 60},
  "snare":  {"host": "snare",  "port": 80,   "timeout": 30},
}

def is_service_running(service_name):
  running_services = []
  for container in client.containers.list():
    labels = container.labels
    service = labels.get("com.docker.compose.service")
    if service and container.status == "running":
      running_services.append(service)

  return service_name in running_services

def _wait_for_health(container, timeout_sec):
  try:
    start = time.time()
    while time.time() - start < timeout_sec:
      container.reload()
      health = container.attrs.get("State", {}).get("Health", {}).get("Status")
      if health == "healthy":
        return True
      # healthcheck が無い場合は False を返してポート待機に委譲
      if health is None:
        return False
      time.sleep(0.5)
  except Exception:
    return False
  return False

def _wait_for_port(host, port, timeout_sec):
  start = time.time()
  while time.time() - start < timeout_sec:
    try:
      with socket.create_connection((host, port), timeout=1.5):
        return True
    except OSError:
      time.sleep(0.5)
  return False

def _wait_service_ready(service_name):
  cfg = WAIT_CONFIG.get(service_name, {})
  host = cfg.get("host", service_name)
  port = cfg.get("port")
  timeout = cfg.get("timeout", 30)

  try:
    container = client.containers.get(service_name)
  except Exception as e:
    print(f"[WARN] Container {service_name} not found: {e}")
    return

  healthy = _wait_for_health(container, timeout)
  if healthy:
    print(f"[INFO] {service_name} is healthy.")
    return

  if port:
    print(f"[INFO] Waiting for {service_name} ({host}:{port}) to accept connections...")
    if _wait_for_port(host, port, timeout):
      print(f"[INFO] {service_name} is accepting connections on {host}:{port}.")
    else:
      print(f"[WARN] Timeout waiting for {service_name} port {host}:{port}.")

def stop_services(service_names):
  for name in service_names:
    if not is_service_running(name):
      print(f"[INFO] {name} is already stopped.")
      continue

    print(f"[INFO] Stopping {name}...")
    container = client.containers.get(name)
    container.stop()

    start_time = time.time()
    while True:
      if not is_service_running(name):
        print(f"[INFO] {name} is now stopped.")
        break

      if time.time() - start_time > MAX_WAIT_SECONDS:
        print(f"[WARN] Timeout while stopping {name}.")
        break

      time.sleep(0.5)

def start_services(service_names):
  for name in service_names:
    if is_service_running(name):
      print(f"[INFO] {name} is already running.")
      _wait_service_ready(name)
      continue

    print(f"[INFO] Stopping {name}...")
    container = client.containers.get(name)
    container.start()

    start_time = time.time()
    while True:
      if is_service_running(name):
        print(f"[INFO] {name} is now running.")
        break

      if time.time() - start_time > MAX_WAIT_SECONDS:
        print(f"[WARN] Timeout while stopping {name}.")
        break

      time.sleep(0.5)

    _wait_service_ready(name)
