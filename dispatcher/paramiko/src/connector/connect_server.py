import paramiko
import re
from utils import ansi_sequences

class SSHConnector:
  def __init__(self, host: str, port: int = 22):
    self.host = host
    self.port = port

  def record_login(self, username: str, password: str):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(self.host, port=self.port, username=username, password=password, timeout=10)
    client.close()

  def replay_history(self, chan, username: str, password: str, history: list[str]):
    try:
      client = paramiko.SSHClient()
      client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      client.connect(self.host, port=self.port, username=username, password=password, timeout=10)

      shell = client.invoke_shell()
      shell.settimeout(5)

      self._wait_for_prompt(shell)

      output = ""
      cwd = "~"

      if history:
        for i, cmd in enumerate(history):
          shell.send(cmd + "\n")
          if i == len(history) - 1:
            output, cwd = self._receive_until_prompt(shell, cmd)

      shell.close()
      client.close()
      return output, cwd

    except Exception as e:
      print(f"Error forwarding to {self.host}: {e}\r\n")
      chan.close()

  def execute_command(self, command: str, username: str, password: str, dir_cmd=None):
    try:
      client = paramiko.SSHClient()
      client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      client.connect(self.host, port=self.port, username=username, password=password, timeout=10)

      shell = client.invoke_shell()
      shell.settimeout(5)

      self._wait_for_prompt(shell)

      if dir_cmd:
        shell.send(dir_cmd + "\n")
        self._wait_for_prompt(shell)

      shell.send(command + "\n")
      output, cwd = self._receive_until_prompt(shell, command)

      shell.close()
      client.close()

      return output, cwd

    except Exception as e:
      return f"Error: {e}\r\n", "~"

  def _wait_for_prompt(self, shell):
    try:
      while True:
        data = shell.recv(1024)
        if not data:
          break
        if b"$ " in data or b"# " in data:
          break
    except Exception:
      pass

  def _receive_until_prompt(self, shell, sent_cmd: str = "") -> tuple[str, str]:
    output = b""
    prompt_line = b""

    try:
      while True:
        data = shell.recv(1024)
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

    for i, line in enumerate(lines):
      if sent_cmd.encode("utf-8") in line.strip():
        continue
      if i == len(lines) - 1:
        try:
          line_str = line.decode("utf-8", errors="ignore")
          prompt_str = prompt_line.decode("utf-8", errors="ignore").strip()
          cleaned_line_str = ansi_sequences.remove_prompt(line_str)
          cleaned_lines.append(cleaned_line_str.encode("utf-8"))
        except Exception:
          cleaned_lines.append(line)
      else:
        cleaned_lines.append(line)

    output_lines = b"\n".join(cleaned_lines).decode("utf-8", errors="ignore")

    cwd = "~"
    prompt_str = prompt_line.decode("utf-8", errors="ignore").strip()
    match = re.search(r"@[^:]+:(.*?)[\$#] ?", prompt_str)
    if match:
      cwd = match.group(1).strip()

    return output_lines, cwd
