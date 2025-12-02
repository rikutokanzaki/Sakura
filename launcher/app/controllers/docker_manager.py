from app.controllers import docker_manager
import docker
import logging
import socket
import time

MAX_WAIT_SECONDS = 10
client = docker.from_env()

LINKED_SERVICES = {
  "snare": ["snare", "tanner_redis", "tanner_phpox", "tanner_api", "tanner"],
}

WAIT_CONFIG = {
  "cowrie": {"host": "cowrie", "port": 2222, "timeout": 60},
  "snare":  {"host": "snare",  "port": 80,   "timeout": 30},
}

logger = logging.getLogger(__name__)


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
    logger.warning("Container %s not found: %s", service_name, e)
    return

  healthy = _wait_for_health(container, timeout)
  if healthy:
    logger.info("%s is healthy.", service_name)
    return

  if port:
    logger.info(
      "Waiting for %s (%s:%s) to accept connections...",
      service_name,
      host,
      port,
    )
    if _wait_for_port(host, port, timeout):
      logger.info(
        "%s is accepting connections on %s:%s.",
        service_name,
        host,
        port,
      )
    else:
      logger.warning(
        "Timeout waiting for %s port %s:%s.",
        service_name,
        host,
        port,
      )


def stop_services(service_names):
  for name in service_names:
    if not is_service_running(name):
      logger.info("%s is already stopped.", name)
      continue

    logger.info("Stopping %s...", name)
    container = client.containers.get(name)
    container.stop()

    start_time = time.time()
    while True:
      if not is_service_running(name):
        logger.info("%s is now stopped.", name)
        break

      if time.time() - start_time > MAX_WAIT_SECONDS:
        logger.warning("Timeout while stopping %s.", name)
        break

      time.sleep(0.5)


def start_services(service_names):
  for name in service_names:
    if is_service_running(name):
      logger.info("%s is already running.", name)
      _wait_service_ready(name)
      continue

    logger.info("Starting %s...", name)
    container = client.containers.get(name)
    container.start()

    start_time = time.time()
    while True:
      if is_service_running(name):
        logger.info("%s is now running.", name)
        break

      if time.time() - start_time > MAX_WAIT_SECONDS:
        logger.warning("Timeout while starting %s.", name)
        break

      time.sleep(0.5)

    _wait_service_ready(name)
