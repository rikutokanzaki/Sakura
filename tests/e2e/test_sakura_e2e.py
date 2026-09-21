import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import paramiko
import pytest
import requests


LAUNCHER_URL = "http://launcher:5000"
OPENRESTY_URL = "http://openresty"
SSH_HOST = "paramiko"
SSH_PORT = 22
SSH_USERNAME = "test-user"
SSH_PASSWORD = "somepassword"
PARAMIKO_LOG = Path("/logs/paramiko/paramiko.log")


def wait_for_http(url: str, timeout: float = 60) -> None:
  deadline = time.monotonic() + timeout
  while time.monotonic() < deadline:
    try:
      response = requests.get(url, timeout=2)
      if response.status_code < 500:
        return
    except requests.RequestException:
      pass
    time.sleep(1)
  pytest.fail(f"Timed out waiting for {url}")


def read_paramiko_modes() -> set[str]:
  if not PARAMIKO_LOG.exists():
    return set()

  modes = set()
  for line in PARAMIKO_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
    try:
      record = json.loads(line)
    except json.JSONDecodeError:
      continue
    mode = record.get("mode")
    if mode:
      modes.add(mode)
  return modes


def run_ssh_command(command: str) -> str:
  client = paramiko.SSHClient()
  client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  try:
    client.connect(
      SSH_HOST,
      port=SSH_PORT,
      username=SSH_USERNAME,
      password=SSH_PASSWORD,
      timeout=10,
      banner_timeout=10,
      auth_timeout=10,
    )
    _, stdout, _ = client.exec_command(command, timeout=15)
    return stdout.read().decode("utf-8", errors="replace")
  finally:
    client.close()


def test_launcher_applies_all_modes():
  wait_for_http(f"{LAUNCHER_URL}/")

  for mode in ("dynamic", "static", "standalone"):
    response = requests.post(f"{LAUNCHER_URL}/apply-mode/{mode}", timeout=15)
    assert response.status_code == 200, response.text
    assert response.json()["mode"] == mode


def test_rotate_mode_reaches_all_modes():
  deadline = time.monotonic() + 12
  observed = set()
  while time.monotonic() < deadline:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
      client.connect(
        SSH_HOST,
        port=SSH_PORT,
        username=SSH_USERNAME,
        password=SSH_PASSWORD,
        timeout=5,
        banner_timeout=5,
        auth_timeout=5,
      )
    except (paramiko.SSHException, OSError):
      pass
    finally:
      client.close()

    observed.update(read_paramiko_modes())
    if {"dynamic", "static", "standalone"}.issubset(observed):
      break
    time.sleep(0.5)

  assert {"dynamic", "static", "standalone"}.issubset(observed), observed


def test_connection_control_rejects_bad_auth_and_allows_concurrent_sessions():
  bad_client = paramiko.SSHClient()
  bad_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  try:
    with pytest.raises(paramiko.AuthenticationException):
      bad_client.connect(
        SSH_HOST,
        port=SSH_PORT,
        username=SSH_USERNAME,
        password="wrong-password",
        timeout=10,
        banner_timeout=10,
        auth_timeout=10,
      )
  finally:
    bad_client.close()

  with ThreadPoolExecutor(max_workers=3) as executor:
    outputs = list(executor.map(run_ssh_command, ["echo connection-a", "echo connection-b", "echo connection-c"]))

  assert outputs == ["connection-a\n", "connection-b\n", "connection-c\n"]


def test_session_update_endpoint_keeps_connection_session_active():
  response = requests.post(f"{LAUNCHER_URL}/session/update/cowrie", timeout=5)
  assert response.status_code == 200
  assert response.text == "Updated cowrie session"
