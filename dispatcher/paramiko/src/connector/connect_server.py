import paramiko
import re

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
  
def execute_on_cowrie(command: str, username: str, password: str, dir_cmd) -> str:
  try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect("cowrie", port=2222, username=username, password=password, timeout=10)

    shell = client.invoke_shell()
    shell.settimeout(5)

    _wait_for_prompt(shell)

    if dir_cmd:
      shell.send(dir_cmd + "\n")
      _wait_for_prompt(shell)

    shell.send(command + "\n")

    output, cwd = _receive_until_prompt(shell, sent_cmd=command)

    shell.close()
    client.close()
    return output, cwd

  except Exception as e:
    return f"Cowrie error: {e}\r\n", "~"

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
          output, cwd = _receive_until_prompt(shell, sent_cmd=cmd)

    shell.close()
    client.close()
    return output, cwd
  
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
  prompt_line = b""

  try:
    while True:
      data = shell.recv(1024)
      print(f"data: {data}")
      if not data:
        break
      output += data
      if b"$ " in data or b"# " in data:
        prompt_line = data
        break
  except Exception:
    pass

  lines = output.split(b"\n")
  cleaned_lines = []

  for line in lines:
    if sent_cmd.encode("utf-8") in line.strip():
      continue
    cleaned_lines.append(line)
  
  output_lines = b"\n".join(cleaned_lines).decode("utf-8", errors="ignore")

  cwd = "~"
  prompt_str = prompt_line.decode("utf-8", errors="ignore").strip()
  match = re.search(r"@[^:]+:(.*?)[\$#] ?", prompt_str)
  if match:
    cwd = match.group(1).strip()
  
  print(f"output_lines: {output_lines}")
  print(f"cwd: {cwd}")

  return output_lines, cwd