import time
import threading
from app.controllers import docker_manager

SESSION_TIMEOUT = 300

_services = {}
_services_lock = threading.Lock()

linked_map = {
    "snare": ["tanner_redis", "tanner_phpox", "tanner_api", "tanner"]
  }

class ServiceSession:
  def __init__(self, service_name, linked_services=None, persist=False):
    self.service_names = [service_name] + (linked_services or [])
    self._last_trigger_time = time.time()
    self._session_active = threading.Event()
    self._stop_observer = threading.Event()
    self.stop_lock = threading.Lock()
    self.persist = persist
    self._observer_thread = threading.Thread(target=self.session_observer, daemon=True)
    self._observer_thread.start()

  def set_persist(self, value: bool):
    self.persist = value
    if value:
      self._session_active.set()

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

      if self.persist:
        self._session_active.wait(timeout=3600)
        continue

      now = time.time()
      timeout = SESSION_TIMEOUT - (now - self._last_trigger_time)
      if timeout <= 0:
        timeout = 0.1

      if self._session_active.wait(timeout):
        continue

      with self.stop_lock:
        running_services = [s for s in self.service_names if docker_manager.is_service_running(s)]
        if running_services:
          print(f"[INFO] Stopping {running_services} due to session timeout.")
          docker_manager.stop_services(running_services)
        else:
          print(f"[INFO] Services already stopped: {self.service_names}")

      print(f"[INFO] Waiting for new session to reactive for {self.service_names}...")
      self._session_active.wait()

def ensure_session(service_name: str, persist: bool = False):
  with _services_lock:
    if service_name not in _services:
      linked = linked_map.get(service_name, [])
      print(f"[INFO] Creating session tracker for service: {service_name} with linked: {linked}, persist={persist}")
      _services[service_name] = ServiceSession(service_name, linked_services=linked, persist=persist)
    return _services[service_name]

def update_session(service_name: str, persist: bool = False):
  session = ensure_session(service_name, persist=persist)
  session.update()
  if persist:
    session.set_persist(True)

def is_session_active(service_name: str):
  with _services_lock:
    return _services.get(service_name, None) and _services[service_name].is_active()

def stop_all_sessions():
  with _services_lock:
    for session in _services.values():
      session.stop()
    _services.clear()
