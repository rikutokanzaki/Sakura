import paramiko

def record_in_heralding(username: str, password: str) -> str:
  client = paramiko.SSHClient()
  client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  client.connect("heralding", port=22, username=username, password=password, timeout=10)

def execute_on_heralding(command: str, username: str, password: str) -> str:
  try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("heralding", port=22, username=username, password=password, timeout=10)

    shell = client.invoke_shell()
    shell.settimeout(5)

    _wait_for_prompt(shell)

    shell.send(command + "\n")

    output = _receive_until_prompt(shell, sent_cmd=command)

    shell.close()
    client.close()
    return output.decode("utf-8", errors="ignore")

  except Exception as e:
    return f"Heralding error: {e}\r\n"
  
def execute_on_cowrie(command: str, username: str, password: str) -> str:
  try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("cowrie", port=2222, username=username, password=password, timeout=10)

    shell = client.invoke_shell()
    shell.settimeout(5)

    _wait_for_prompt(shell)

    shell.send(command + "\n")

    output = _receive_until_prompt(shell, sent_cmd=command)

    shell.close()
    client.close()
    return output.decode("utf-8", errors="ignore")

  except Exception as e:
    return f"Cowrie error: {e}\r\n"

def forward_to_cowrie(chan, username: str, password: str, history: list[str]):
  try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("cowrie", port=2222, username=username, password=password, timeout=10)
    shell = client.invoke_shell()
    shell.settimeout(5)

    _wait_for_prompt(shell)

    if history:
      for i, cmd in enumerate(history):
        shell.send(cmd + "\n")

        if i == len(history) - 1:
          output = _receive_until_prompt(shell, sent_cmd=cmd)

    shell.close()
    client.close()
    return output.decode("utf-8", errors="ignore")
  
  except Exception as e:
    print(f"Error forwarding to Cowrie: {e}\r\n")
    chan.close()

def _wait_for_prompt(shell):
  try:
    while True:
      data = shell.recv(1024)
      if not data:
        break
      if b"$ " in data or b"# " in data:
        break
  
  except Exception:
    pass

def _receive_until_prompt(shell, sent_cmd: str = "") -> bytes:
  output = b""
  try:
    while True:
      data = shell.recv(1024)
      if not data:
        break
      output += data
      if b"$ " in data or b"# " in data:
        break
  except Exception:
    pass

  lines = output.split(b"\n")
  cleaned_lines = []

  for line in lines:
    if sent_cmd.encode("utf-8") in line.strip():
      continue
    cleaned_lines.append(line)

  return b"\n".join(cleaned_lines)