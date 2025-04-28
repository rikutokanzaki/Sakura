import subprocess
import time

MAX_WAIT_SECONDS = 10

def is_service_running(service_name):
  result = subprocess.run(
    ["docker", "compose", "ps", "--status=running", "--services"],
    capture_output=True,
    text=True
  )

  running_services = result.stdout.strip().splitlines()
  return service_name in running_services

def pause_service(service_name):
  if not is_service_running(service_name):
    print(f"[INFO] {service_name} is already paused.")
    return False

  print(f"[INFO] Pausing {service_name}...")
  subprocess.run(["docker", "compose", "pause", service_name])

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
  subprocess.run(["docker", "compose", "unpause", service_name])

  start_time = time.time()
  while True:
    if is_service_running(service_name):
      print(f"[INFO] {service_name} is now running.")
      return True

    if time.time() - start_time > MAX_WAIT_SECONDS:
      print(f"[WARN] Timeout while unpausing {service_name}.")
      break

    time.sleep(0.5)