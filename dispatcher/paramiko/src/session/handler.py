from session import set_prompt
from reader import line_reader
from utils import set_motd, ansi_sequences, log_event, resource_manager
from connector import connect_server
import logging
import os
import time
import requests
import threading

logger = logging.getLogger(__name__)

UPDATE_SESSION_URL = "http://launcher:5000/session/update/cowrie"
_UPDATE_LOCK = threading.Lock()
_LAST_UPDATE_AT = 0.0
UPDATE_INTERVAL = 1.5

def _post_update():
  try:
    requests.post(UPDATE_SESSION_URL, timeout=2)
  except Exception:
    logger.exception("Session update failed")

def update_session(force: bool = False) -> None:
  global _LAST_UPDATE_AT
  now = time.time()

  if not force and (now - _LAST_UPDATE_AT) < UPDATE_INTERVAL:
    return

  with _UPDATE_LOCK:
    now = time.time()

    if not force and (now - _LAST_UPDATE_AT) < UPDATE_INTERVAL:
      return
    _LAST_UPDATE_AT = now
    threading.Thread(target=_post_update, daemon=True).start()

def _build_dir_cmd(cwd: str) -> str:
  if not cwd or cwd == "~":
    return ""
  return f"cd {cwd}"

def handle_session(chan, username: str, password: str, addr: tuple, start_time: float, cowrie_launched: bool, cowrie_connector: connect_server.SSHConnector, mode: str, transport=None, client_socket=None) -> None:
  history = []
  dir_cmd = ""

  hostname = str(os.getenv('HOST_NAME'))[:9]
  cwd = "~"

  prompt_manager = set_prompt.PromptManager()
  prompt = prompt_manager.get_prompt(username, hostname, cwd)
  reader = line_reader.LineReader(chan, username, password, prompt, history, cowrie_connector)

  motd_lines = set_motd.get_motd_lines(hostname)
  chan.send(b"\r\n")
  for line in motd_lines:
    sent_line = line.rstrip() + "\r\n"
    chan.send(sent_line.encode("utf-8"))
    time.sleep(0.005)

  if mode == "yozakura" or mode == "tsubomi":
    cowrie_launched = True
    update_session(force=True)
  elif cowrie_launched:
    update_session(force=True)

  try:
    while True:
      cmd = reader.read()

      if not cmd:
        continue

      try:
        src_ip, src_port = chan.getpeername()
      except Exception:
        src_ip, src_port = "unknown", 0

      log_event.log_command_event(src_ip, src_port, username, cmd, cwd, mode)

      if cmd.lower() in ["exit", "quit", "exit;", "quit;"]:
        break

      if not cowrie_launched:
        if mode == "sakura":
          history.append(cmd)

          try:
            res = requests.post("http://launcher:5000/trigger/cowrie", timeout=5)
            if res.status_code == 200:
              logger.info("Cowrie started. Transferring session... (sakura mode)")
            else:
              logger.error("Failed to start Cowrie (HTTP %s)", res.status_code)
              chan.send(b"Service unavailable. Session terminated.\r\n")
              break
          except Exception:
            logger.exception("Error triggering Cowrie")
            chan.send(b"Service unavailable. Session terminated.\r\n")
            break

          cowrie_launched = True

          try:
            output, cwd = cowrie_connector.replay_history(username, password, history)
          except Exception:
            logger.exception("Cowrie connection failed during replay_history")
            chan.send(b"Connection to backend lost. Session terminated.\r\n")
            break

          dir_cmd = _build_dir_cmd(cwd)
          prompt = prompt_manager.get_prompt(username, hostname, cwd)
          reader.update_prompt(prompt)

          clean_output = ansi_sequences.strip_ansi_sequences(output)
          chan.send(clean_output.encode("utf-8"))
          update_session(force=True)
          continue
        else:
          logger.warning("Unexpected state: cowrie not launched in mode %s", mode)
          chan.send(b"Service error. Session terminated.\r\n")
          break

      dir_cmd = _build_dir_cmd(cwd)

      try:
        output, cwd = cowrie_connector.execute_command(cmd, username, password, dir_cmd)
      except Exception:
        logger.exception("Cowrie connection lost during command execution")
        chan.send(b"Connection to backend lost. Session terminated.\r\n")
        break

      dir_cmd = _build_dir_cmd(cwd)
      prompt = prompt_manager.get_prompt(username, hostname, cwd)
      reader.update_prompt(prompt)

      clean_output = ansi_sequences.strip_ansi_sequences(output)
      chan.send(clean_output.encode("utf-8"))
      update_session()

  except EOFError:
    logger.info("Client closed connection (EOF)")

  except Exception:
    logger.exception("Error handling session")

  finally:
    try:
      src_ip, src_port = addr[0], addr[1]
    except Exception:
      src_ip, src_port = "unknown", 0

    duration = time.time() - start_time
    log_event.log_session_close(
      src_ip=src_ip,
      src_port=src_port,
      username=username,
      duration=duration,
      message="Session closed",
      mode=mode
    )

    try:
      reader.cleanup_terminal()
    except Exception:
      logger.exception("Failed to cleanup terminal")

    resource_manager.close_channel(chan)

    if transport is not None:
      try:
        resource_manager.close_transport(transport)
      except Exception:
        logger.exception("Failed to close transport in session cleanup")

    if client_socket is not None:
      try:
        resource_manager.close_socket(client_socket)
      except Exception:
        logger.exception("Failed to close client socket in session cleanup")
