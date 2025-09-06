from session import set_prompt
from reader import line_reader
from utils import set_motd
from connector import connect_server
from utils import ansi_sequences, log_event
import os
import time
import requests
import threading

UPDATE_SESSION_URL = "http://launcher:5000/session/update/cowrie"
_UPDATE_LOCK = threading.Lock()
_LAST_UPDATE_AT = 0.0
UPDATE_INTERVAL = 1.5

def _post_update():
  try:
    requests.post(UPDATE_SESSION_URL, timeout=2)
  except Exception as e:
    print(f"Session update failed: {e}")

def update_session(force=False):
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

def handle_session(chan, username, password, addr, start_time, cowrie_launched=False):
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
      except:
        src_ip, src_port = "unknown", 0

      log_event.log_command_event(src_ip, src_port, username, cmd, cwd)

      if cmd.lower() in ["exit", "quit", "exit;", "quit;"]:
        break

      if not cowrie_launched:
        history.append(cmd)

        try:
          res = requests.post("http://launcher:5000/trigger/cowrie", timeout=5)
          if res.status_code == 200:
            print("Cowrie started. Transferring session...")
          else:
            print(f"Failed to start Cowrie (HTTP {res.status_code})")
            break
        except Exception as e:
          print(f"Error triggering Cowrie: {e}")
          break

        cowrie_launched = True
        output, cwd = cowrie_connector.replay_history(chan, username, password, history)
        clean_output = ansi_sequences.strip_ansi_sequences(output)
        chan.send(clean_output.encode("utf-8"))
        update_session(force=True)
        continue

      output, cwd = cowrie_connector.execute_command(cmd, username, password, dir_cmd)
      if cwd != "~":
        dir_cmd = f"cd {cwd}"
      else:
        dir_cmd = ""
      prompt = prompt_manager.get_prompt(username, hostname, cwd)
      reader.update_prompt(prompt)
      clean_output = ansi_sequences.strip_ansi_sequences(output)
      chan.send(clean_output.encode("utf-8"))
      update_session()

  except Exception as e:
    print(f"Error handling session: {e}")

  finally:
    duration = time.time() - start_time
    log_event.log_session_close(
      src_ip=addr[0],
      src_port=addr[1],
      username=username,
      duration=duration,
      message="Session closed"
    )
    reader.cleanup_terminal()
    chan.close()
