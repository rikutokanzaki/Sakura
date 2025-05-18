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
    self._thread = threading.Thread(target=self._observe_log, daemon=True)
  
  def start(self):
    self._thread.start()
  
  def _observe_log(self):
    while True:
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
        print("[LOG OBSERVER] cowrie.json not found.")
      time.sleep(self.poll_interval)