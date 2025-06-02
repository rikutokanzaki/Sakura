import time
import docker

MAX_WAIT_SECONDS = 10
client = docker.from_env()

LINKED_SERVICES = {
  "snare": ["snare", "tanner_redis", "tanner_phpox", "tanner_api", "tanner"],
}

def is_service_running(service_name):
  running_services = []
  for container in client.containers.list():
    labels = container.labels
    service = labels.get("com.docker.compose.service")
    if service and container.status == "running":
      running_services.append(service)

  return service_name in running_services

def pause_services(service_names):
  for name in service_names:
    if not is_service_running(name):
      print(f"[INFO] {name} is already paused.")
      continue

    print(f"[INFO] Pausing {name}...")
    container = client.containers.get(name)
    container.pause()

    start_time = time.time()
    while True:
      if not is_service_running(name):
        print(f"[INFO] {name} is now paused.")
        break

      if time.time() - start_time > MAX_WAIT_SECONDS:
        print(f"[WARN] Timeout while pausing {name}.")
        break

      time.sleep(0.5)

def unpause_services(service_names):
  for name in service_names:
    if is_service_running(name):
      print(f"[INFO] {name} is already running.")
      continue

    print(f"[INFO] Unpausing {name}...")
    container = client.containers.get(name)
    container.unpause()

    start_time = time.time()
    while True:
      if is_service_running(name):
        print(f"[INFO] {name} is now running.")
        break

      if time.time() - start_time > MAX_WAIT_SECONDS:
        print(f"[WARN] Timeout while unpausing {name}.")
        break

      time.sleep(0.5)
