import subprocess
import time
import docker

MAX_WAIT_SECONDS = 10
client = docker.from_env()

def is_service_running(service_name):
  running_services = []
  for container in client.containers.list():
    labels = container.labels
    service = labels.get("com.docker.compose.service")
    if service and container.status == "running":
      running_services.append(service)

  return service_name in running_services

def pause_service(service_name):
  if not is_service_running(service_name):
    print(f"[INFO] {service_name} is already paused.")
    return False

  print(f"[INFO] Pausing {service_name}...")
  container = client.containers.get(service_name)
  container.pause()

  start_time = time.time()
  while True:
    if not is_service_running(service_name):
      print(f"[INFO] {service_name} is now paused.")
      return True

    if time.time() - start_time > MAX_WAIT_SECONDS:
      print(f"[WARN] Timeout while pausing {service_name}.")
      break

    time.sleep(0.5)

def unpause_service(service_name):
  if is_service_running(service_name):
    print(f"[INFO] {service_name} is already running.")
    return True
  
  print(f"[INFO] Unpausing {service_name}...")
  container = client.containers.get(service_name)
  container.unpause()

  start_time = time.time()
  while True:
    if is_service_running(service_name):
      print(f"[INFO] {service_name} is now running.")
      return True

    if time.time() - start_time > MAX_WAIT_SECONDS:
      print(f"[WARN] Timeout while unpausing {service_name}.")
      break

    time.sleep(0.5)