from handler import line_reader
from connector import connect_server
import paramiko
import requests
import datetime
import os
import time

def get_motd_lines(hostname):
  motd_file_path = os.path.join(os.path.dirname(__file__), "/config/motd.txt")

  now = datetime.datetime.now(datetime.timezone.utc).strftime("%a %b %d %H:%M:%S UTC %Y")

  formatted_hostname = (hostname + ":").ljust(10)

  try:
    with open(motd_file_path, "r", encoding="utf-8") as f:
      lines = f.readlines()

    return [line.format(now=now, hostname=formatted_hostname) for line in lines]
  except Exception as e:
    print(f"Failed to read motd file: {e}")
    fallback_message = f"Welcome. (Host: 192.168.100.3 Time: {now})"
    return [fallback_message]

def get_prompt(username, hostname, cwd="~"):
  prompt = f"{username}@{hostname}:{cwd}$ "
  return prompt

def get_cowrie_prompt(username, password):
  try:
    res = requests.post("http://launcher:5000/trigger/cowrie", timeout=5)
    if res.status_code != 200:
      print(f"Failed to trigger Cowrie: HTTP {res.status_code}")
      return "~$ "

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("cowrie", port=2222, username=username, password=password, timeout=10)

    shell = client.invoke_shell()
    shell.settimeout(5)

    output = b""
    while True:
      try:
        data = shell.recv(1024)
        if not data:
          break
        output += data
        if b"$ " in data or b"# " in data:
          break
      except Exception:
        break

    client.close()

    lines = output.decode("utf-8", errors="ignore").splitlines()
    for line in reversed(lines):
      if line.strip().endswith("$") or line.strip().endswith("#"):
        return line.strip() + " "
    return "~$ "

  except Exception as e:
    print(f"Error getting Cowrie prompt: {e}")
    return "~$ "

def handle_session(chan, username, password):
  history = []
  dir_cmd = ""
  cowrie_launched = False

  hostname = str(os.getenv('HOST_NAME'))[:9]
  cwd = "~"

  prompt = get_prompt(username, hostname, cwd)
  reader = line_reader.LineReader(chan, prompt)

  motd_lines = get_motd_lines(hostname)
  for line in motd_lines:
    sent_line = line.rstrip() + "\r\n"
    chan.send(sent_line.encode("utf-8"))
    time.sleep(0.005)

  try:
    while True:
      cmd = reader.read()

      if not cmd:
        continue

      if cmd.lower() in ["exit", "quit"]:
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
        chan.send(output.encode("utf-8"))
        continue

      output, cwd = connect_server.execute_on_cowrie(cmd, username, password, dir_cmd)
      if cwd != "~":
        dir_cmd = f"cd {cwd}"
      else:
        dir_cmd = ""
      prompt = get_prompt(username, hostname, cwd)
      reader.update_prompt(prompt)
      chan.send(output.encode("utf-8"))

  except Exception as e:
    print(f"Error handling session: {e}")
  finally:
    reader.cleanup_terminal()
    chan.close()
