from utils import resource_manager
import logging
import requests
import paramiko

logger = logging.getLogger(__name__)

class PromptManager:
  def __init__(self, launcher_host="launcher", cowrie_host="cowrie", cowrie_port=2222):
    self.launcher_host = launcher_host
    self.cowrie_host = cowrie_host
    self.cowrie_port = cowrie_port

  def get_prompt(self, username, hostname, cwd="~"):
    return f"{username}@{hostname}:{cwd}# "

  def get_cowrie_prompt(self, username, password) -> str:
    client = None
    shell = None
    transport = None

    try:
      res = requests.post(f"http://{self.launcher_host}:5000/trigger/cowrie", timeout=5)
      if res.status_code != 200:
        logger.error("Failed to trigger Cowrie: HTTP %s", res.status_code)
        return "~$ "

      client = paramiko.SSHClient()
      client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      client.connect(self.cowrie_host, port=self.cowrie_port, username=username, password=password, timeout=10)
      transport = client.get_transport()

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

      lines = output.decode("utf-8", errors="ignore").splitlines()
      for line in reversed(lines):
        if line.strip().endswith("$") or line.strip().endswith("#"):
          return line.strip() + " "

      return "~$ "

    except Exception:
      logger.exception("Error getting Cowrie prompt")
      return "~$ "

    finally:
      resource_manager.close_ssh_connection(client=client, shell=shell, transport=transport)
