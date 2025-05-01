import time
import threading
from app.controller import docker_manager

SESSION_TIMEOUT = 60

_services = {}
_services_lock = threading.Lock()

class ServiceSession:
  def __init__(self, service_name):
    self.service_name = service_name
    self._last_trigger_time = time.time()
    self._session_active = threading.Event()
    self._stop_observer = threading.Event()
    self.pause_lock = threading.Lock()
    self._observer_thread = threading.Thread(target=self.session_observer, daemon=True)
    self._observer_thread.start()

  def update(self):
    self._last_trigger_time = time.time()
    self._session_active.set()

  def is_active(self):
    return self._session_active.is_set()
  
  def stop(self):
    self._stop_observer.set()
    self._session_active.set()
  
  def session_observer(self):
    while not self._stop_observer.is_set():
      self._session_active.clear()
      now = time.time()

      timeout = SESSION_TIMEOUT - (now - self._last_trigger_time)
      if timeout <= 0:
        timeout = 0.1

      if self._session_active.wait(timeout):
        continue

      with self.pause_lock:
        if docker_manager.is_service_running(self.service_name):
          print(f"[INFO] Pausing {self.service_name} due to session timeout.")
          docker_manager.pause_service(self.service_name)
        else:
          print(f"[INFO] {self.service_name} is already paused.")

      print(f"[INFO] Waiting for new session to reactive for {self.service_name}...")
      self._session_active.wait()
  
def update_session(service_name: str):
  with _services_lock:
    if service_name not in _services:
      print(f"[INFO] Creating session tracker for service: {service_name}")
      _services[service_name] = ServiceSession(service_name)

    _services[service_name].update()

def is_session_active(service_name: str):
  with _services_lock:
    return _services.get(service_name, None) and _services[service_name].is_active()
  
def stop_all_sessions():
  with _services_lock:
    for session in _services.values():
      session.stop()
    _services.clear()