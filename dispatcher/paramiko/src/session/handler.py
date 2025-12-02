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

def _is_cowrie_connection_error(output: str) -> bool:
  error_patterns = [
    "Name or service not known",
    "Connection refused",
    "No route to host",
    "Connection reset by peer",
    "Operation timed out"
  ]
  return any(pattern in output for pattern in error_patterns)

def handle_session(chan, username: str, password: str, addr: tuple, start_time: float, cowrie_launched: bool = False) -> None:
  history = []
  dir_cmd = ""

  hostname = str(os.getenv('HOST_NAME'))[:9]
  cwd = "~"

  prompt_manager = set_prompt.PromptManager()
  prompt = prompt_manager.get_prompt(username, hostname, cwd)
  reader = line_reader.LineReader(chan, username, password, prompt, history)

  cowrie_connector = connect_server.SSHConnector(host="cowrie", port=2222)

  motd_lines = set_motd.get_motd_lines(hostname)
  for line in motd_lines:
    sent_line = line.rstrip() + "\r\n"
    chan.send(sent_line.encode("utf-8"))
    time.sleep(0.005)

  if cowrie_launched:
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

      log_event.log_command_event(src_ip, src_port, username, cmd, cwd)

      if cmd.lower() in ["exit", "quit", "exit;", "quit;"]:
        break

      if not cowrie_launched:
        history.append(cmd)

        try:
          res = requests.post("http://launcher:5000/trigger/cowrie", timeout=5)
          if res.status_code == 200:
            logger.info("Cowrie started. Transferring session...")
          else:
            logger.error("Failed to start Cowrie (HTTP %s)", res.status_code)
            chan.send(b"Service unavailable. Session terminated.\r\n")
            break
        except Exception:
          logger.exception("Error triggering Cowrie")
          chan.send(b"Service unavailable. Session terminated.\r\n")
          break

        cowrie_launched = True
        output, cwd = cowrie_connector.replay_history(chan, username, password, history)

        if _is_cowrie_connection_error(output):
          logger.error("Cowrie connection failed during replay_history")
          chan.send(b"Connection to backend lost. Session terminated.\r\n")
          break

        dir_cmd = _build_dir_cmd(cwd)
        prompt = prompt_manager.get_prompt(username, hostname, cwd)
        reader.update_prompt(prompt)

        clean_output = ansi_sequences.strip_ansi_sequences(output)
        chan.send(clean_output.encode("utf-8"))
        update_session(force=True)
        continue

      dir_cmd = _build_dir_cmd(cwd)
      output, cwd = cowrie_connector.execute_command(cmd, username, password, dir_cmd)

      if _is_cowrie_connection_error(output):
        logger.error("Cowrie connection lost during command execution")
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
    duration = time.time() - start_time
    log_event.log_session_close(
      src_ip=addr[0],
      src_port=addr[1],
      username=username,
      duration=duration,
      message="Session closed"
    )

    try:
      reader.cleanup_terminal()
    except Exception:
      logger.exception("Failed to cleanup terminal")

    resource_manager.close_channel(chan)

    try:
      if chan.transport:
        resource_manager.close_transport(chan.transport)
    except Exception:
      logger.exception("Failed to close transport from channel")
