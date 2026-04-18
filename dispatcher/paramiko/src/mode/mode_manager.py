import os
import logging
import threading
import time
import requests

logger = logging.getLogger(__name__)

class ModeManager:
  _instance = None
  _lock = threading.Lock()

  def __new__(cls):
    if cls._instance is None:
      with cls._lock:
        if cls._instance is None:
          cls._instance = super().__new__(cls)
          cls._instance._initialized = False
    return cls._instance

  def __init__(self):
    if self._initialized:
      return

    self._initialized = True
    self._mode_lock = threading.Lock()
    self._configured_mode = self._normalize_mode(os.getenv("DISPATCHER_MODE", "dynamic"))
    self._selected_profile = (os.getenv("SELECTED_PROFILE", "standard") or "standard").lower()
    self._rotate_interval = self._read_rotate_interval()
    self._current_mode = self._resolve_mode(time.time())
    logger.info("ModeManager initialized with mode: %s", self._current_mode)

    self._start_mode_apply_thread_if_required()

  def _read_rotate_interval(self) -> int:
    try:
      interval = int(os.getenv("ROTATE_INTERVAL", "1020"))
      return interval if interval > 0 else 1020
    except (TypeError, ValueError):
      return 1020

  def _resolve_mode(self, now: float) -> str:
    if self._configured_mode != "rotate":
      return self._configured_mode

    modes = ["dynamic", "static", "standalone"]
    slot = int(now // self._rotate_interval) % len(modes)
    return modes[slot]

  def _normalize_mode(self, mode: str) -> str:
    if not mode:
      return "dynamic"

    normalized = mode.strip().lower()
    valid_modes = {"dynamic", "static", "standalone", "rotate"}
    return normalized if normalized in valid_modes else "dynamic"

  def _should_manage_rotate_apply(self) -> bool:
    if self._configured_mode != "rotate":
      return False
    return self._selected_profile in {"standard", "ssh"}

  def _apply_mode_to_launcher(self, mode: str) -> None:
    try:
      response = requests.post(f"http://launcher:5000/apply-mode/{mode}", timeout=2)
      if response.status_code >= 400:
        logger.warning("Failed to apply mode %s via launcher: HTTP %s", mode, response.status_code)
    except requests.exceptions.RequestException as e:
      logger.debug("Mode apply request failed (will retry on next tick): %s", e)
    except Exception as e:
      logger.exception("Unexpected mode apply error: %s", e)

  def _mode_apply_loop(self):
    while True:
      try:
        time.sleep(1)
        with self._mode_lock:
          resolved_mode = self._resolve_mode(time.time())
          if resolved_mode != self._current_mode:
            old_mode = self._current_mode
            self._current_mode = resolved_mode
            logger.info("[mode-rotate] %s -> %s", old_mode, resolved_mode)
            self._apply_mode_to_launcher(resolved_mode)
      except Exception as e:
        logger.exception("Error in mode apply loop: %s", e)

  def _start_mode_apply_thread_if_required(self) -> None:
    if not self._should_manage_rotate_apply():
      return

    self._apply_mode_to_launcher(self._current_mode)

    thread = threading.Thread(target=self._mode_apply_loop, daemon=True)
    thread.start()

  def get_mode(self) -> str:
    with self._mode_lock:
      resolved_mode = self._resolve_mode(time.time())
      if resolved_mode != self._current_mode:
        logger.info("[mode-rotate] %s -> %s", self._current_mode, resolved_mode)
        self._current_mode = resolved_mode
      return self._current_mode

  def set_mode(self, mode: str) -> None:
    normalized_mode = self._normalize_mode(mode)
    valid_modes = ["dynamic", "static", "standalone", "rotate"]

    if normalized_mode not in valid_modes:
      logger.error("Invalid mode: %s. Must be one of %s", mode, valid_modes)
      raise ValueError(f"Invalid mode: {mode}")

    with self._mode_lock:
      old_mode = self._current_mode
      self._current_mode = normalized_mode
      logger.info("Mode changed: %s -> %s", old_mode, normalized_mode)

  def is_dynamic(self) -> bool:
    return self.get_mode() == "dynamic"

  def is_static(self) -> bool:
    return self.get_mode() == "static"

  def is_standalone(self) -> bool:
    return self.get_mode() == "standalone"
