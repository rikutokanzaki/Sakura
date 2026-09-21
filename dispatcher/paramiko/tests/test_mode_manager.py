from mode.mode_manager import ModeManager


def make_manager(configured_mode="dynamic", rotate_interval=10):
  manager = object.__new__(ModeManager)
  manager._configured_mode = configured_mode
  manager._rotate_interval = rotate_interval
  manager._next_rotation_at = None
  return manager


def test_normalize_mode_accepts_supported_values_and_defaults_invalid_values():
  manager = make_manager()

  assert manager._normalize_mode(" STATIC ") == "static"
  assert manager._normalize_mode("rotate") == "rotate"
  assert manager._normalize_mode("") == "dynamic"
  assert manager._normalize_mode("unsupported") == "dynamic"


def test_resolve_mode_returns_configured_mode_without_rotation():
  manager = make_manager("standalone")

  assert manager._resolve_mode(12345) == "standalone"


def test_resolve_mode_cycles_through_modes_at_rotate_interval():
  manager = make_manager("rotate", 10)

  assert manager._resolve_mode(0) == "dynamic"
  assert manager._resolve_mode(10) == "static"
  assert manager._resolve_mode(20) == "standalone"
  assert manager._resolve_mode(30) == "dynamic"


def test_rotation_uses_fixed_next_timestamps_without_accumulating_work_time(monkeypatch):
  manager = make_manager("rotate", 10)
  manager._current_mode = "dynamic"
  manager._next_rotation_at = 100
  applied_modes = []
  monkeypatch.setattr(manager, "_apply_mode_to_launcher", applied_modes.append)

  manager._advance_rotation_if_due(100.5)
  assert manager._current_mode == "static"
  assert manager._next_rotation_at == 110

  # A slow check advances from the scheduled timestamp, not from 100.5.
  manager._advance_rotation_if_due(110.5)
  assert manager._current_mode == "standalone"
  assert manager._next_rotation_at == 120
  assert applied_modes == ["static", "standalone"]


def test_rotation_catches_up_missed_scheduled_boundaries(monkeypatch):
  manager = make_manager("rotate", 10)
  manager._current_mode = "dynamic"
  manager._next_rotation_at = 100
  applied_modes = []
  monkeypatch.setattr(manager, "_apply_mode_to_launcher", applied_modes.append)

  manager._advance_rotation_if_due(131)

  assert manager._current_mode == "static"
  assert manager._next_rotation_at == 140
  assert applied_modes == ["static", "standalone", "dynamic", "static"]


def test_rotate_apply_is_limited_to_standard_and_ssh_profiles():
  manager = make_manager("rotate")

  manager._selected_profile = "standard"
  assert manager._should_manage_rotate_apply()
  manager._selected_profile = "ssh"
  assert manager._should_manage_rotate_apply()
  manager._selected_profile = "http"
  assert not manager._should_manage_rotate_apply()
