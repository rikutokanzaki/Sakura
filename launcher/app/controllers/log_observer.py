import os
import time
import json
import threading
from app.controllers import session_manager

class CowrieLogObserver:
  def __init__(self, log_path, poll_interval=2):
    self.log_path = log_path
    self.poll_interval = poll_interval
    self._last_size = 0
    self._running = False
    self._thread = None
  
  def start(self):
    if not self._running:
      self._running = True
      self._thread = threading.Thread(target=self._observe_log, daemon=True)
      self._thread.start()
  
  def stop(self):
    self._running = False
    if self._thread:
      self._thread.join()
  
  def _observe_log(self):
    while self._running:
      try:
        current_size = os.path.getsize(self.log_path)
        if current_size > self._last_size:
          with open(self.log_path, 'r', encoding='utf-8')as f:
            f.seek(self._last_size)
            new_lines = f.read().strip().splitlines()
            if new_lines:
              print("[LOG OBSERVER] Detected new cowrie.json line. Updating session...")
              session_manager.update_session("cowrie")
              print("[LOG OBSERVER] Session has been updated.")
          self._last_size = current_size
      except FileNotFoundError:
        print("cowrie.json not found.")
        pass
      time.sleep(self.poll_interval)