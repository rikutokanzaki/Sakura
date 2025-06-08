import requests
import paramiko

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