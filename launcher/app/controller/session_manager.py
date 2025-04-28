import time
import threading
from app.controller import docker_manager

SESSION_TIMEOUT = 60
pause_lock = threading.Lock()

_last_trigger_time = time.time()
_observer_thread = None
_observer_lock = threading.Lock()
_session_active = threading.Event()
_stop_observer = threading.Event()

def update_session():
  global _last_trigger_time, _observer_thread
    
  _last_trigger_time = time.time()

  with _observer_lock:
    _session_active.set()

    if _observer_thread is None or not _observer_thread.is_alive():
      print("[INFO] Starting new session observer.")
      _stop_observer.clear()
      _observer_thread = threading.Thread(target=session_observer, daemon=True)
      _observer_thread.start()

def is_session_active():
  return _session_active.is_set()

def session_observer():
  global _last_trigger_time

  while not _stop_observer.is_set():
    _session_active.clear()
    now = time.time()

    timeout = SESSION_TIMEOUT - (now - _last_trigger_time)
    if timeout <= 0:
      timeout = 0.1
      
    if _session_active.wait(timeout):
      continue
      
    with pause_lock:
      if docker_manager.is_service_running("http-honeypot"):
        print("[INFO] Pausing http-honeypot due to session timeout.")
        docker_manager.pause_service("http-honeypot")
      else:
        print("[INFO] http-honeypot is already paused.")
    
    print("[INFO] Waiting for new session to reactivate...")
    _session_active.wait()