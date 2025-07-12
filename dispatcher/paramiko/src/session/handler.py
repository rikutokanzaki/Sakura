from session import set_prompt
from reader import line_reader
from utils import set_motd
from connector import connect_server
from utils import ansi_sequences
import os
import time
import requests

def handle_session(chan, username, password):
  history = []
  dir_cmd = ""
  cowrie_launched = False

  hostname = str(os.getenv('HOST_NAME'))[:9]
  cwd = "~"

  prompt = set_prompt.get_prompt(username, hostname, cwd)
  reader = line_reader.LineReader(chan, prompt)

  motd_lines = set_motd.get_motd_lines(hostname)
  for line in motd_lines:
    sent_line = line.rstrip() + "\r\n"
    chan.send(sent_line.encode("utf-8"))
    time.sleep(0.005)

  try:
    while True:
      cmd = reader.read()

      if not cmd:
        continue

      if cmd.lower() in ["exit", "quit", "exit;", "quit;"]:
        break

      if not cowrie_launched:
        history.append(cmd)

        try:
          res = requests.post("http://launcher:5000/trigger/cowrie", timeout=5)
          if res.status_code == 200:
            print("Cowrie unpaused. Transferring session...")
          else:
            print(f"Failed to unpause Cowrie (HTTP {res.status_code})")
            break
        except Exception as e:
          print(f"Error triggering Cowrie: {e}")
          break

        cowrie_launched = True
        output, cwd = connect_server.forward_to_cowrie(chan, username, password, history)
        clean_output = ansi_sequences.strip_ansi_sequences(output)
        chan.send(clean_output.encode("utf-8"))
        continue

      output, cwd = connect_server.execute_on_cowrie(cmd, username, password, dir_cmd)
      if cwd != "~":
        dir_cmd = f"cd {cwd}"
      else:
        dir_cmd = ""
      prompt = set_prompt.get_prompt(username, hostname, cwd)
      reader.update_prompt(prompt)
      clean_output = ansi_sequences.strip_ansi_sequences(output)
      chan.send(clean_output.encode("utf-8"))

  except Exception as e:
    print(f"Error handling session: {e}")
  finally:
    reader.cleanup_terminal()
    chan.close()
