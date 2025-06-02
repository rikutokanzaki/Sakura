from handler import line_reader
from connector import connect_server
import paramiko
import requests

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

    lines = output.decode(errors="ignore").splitlines()
    for line in reversed(lines):
      if line.strip().endswith("$") or line.strip().endswith("#"):
        return line.strip() + " "
    return "~$ "

  except Exception as e:
    print(f"Error getting Cowrie prompt: {e}")
    return "~$ "

def handle_session(chan, username, password):
  commands = []
  cowrie_launched = False

  prompt = get_cowrie_prompt(username, password)
  reader = line_reader.LineReader(chan, prompt)

  try:
    while True:
      chan.send(prompt.encode())
      cmd = reader.read()

      if not cmd:
        continue

      if cmd.lower() in ["exit", "quit"]:
        break

      if not cowrie_launched:
        commands.append(cmd)

        try:
          res = requests.post("http://launcher:5000/trigger/cowrie", timeout=5)
          if res.status_code == 200:
            print("Cowrie unpaused. Transferring session...".encode())
          else:
            print(f"Failed to unpause Cowrie (HTTP {res.status_code})".encode())
            break
        except Exception as e:
          print(f"Error triggering Cowrie: {e}".encode())
          break

        cowrie_launched = True
        output = connect_server.forward_to_cowrie(chan, username, password, commands)
        chan.send(output.encode("utf-8"))
        continue

      output = connect_server.execute_on_cowrie(cmd, username, password)
      chan.send(output.encode("utf-8"))

  except Exception as e:
    print(f"Error handling session: {e}")
  finally:
    reader.cleanup_terminal()
    chan.close()
