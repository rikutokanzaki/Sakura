import logging
from auth import auth_user
from connector import connect_server
from session import handler
from utils import log_event
import socket
import threading
import paramiko
import time
import requests

logging.basicConfig(
  level=logging.WARNING,
  format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)

HOST = "0.0.0.0"
PORT = 22

HOST_KEY = paramiko.RSAKey(filename="/certs/ssh_host_rsa_key")

class SSHProxyServer(paramiko.ServerInterface):
  def __init__(self, client_addr):
    self.event = threading.Event()
    self.username = None
    self.password = None
    self.authenticator = auth_user.Authenticator()
    self.heralding_connector = connect_server.SSHConnector(host="heralding")
    self.client_addr = client_addr
    self.cowrie_launched = False

  def check_auth_password(self, username, password):
    self.username = username
    self.password = password

    try:
      self.heralding_connector.record_login(username=username, password=password)
    except Exception:
      logger.exception("Failed to record login via heralding_connector")

    auth_success = self.authenticator.authenticate(username, password)
    log_event.log_auth_event(self.client_addr, HOST, PORT, username, password, auth_success)

    if auth_success:
      threading.Thread(target=self._trigger_cowrie, daemon=True).start()

    return paramiko.AUTH_SUCCESSFUL if auth_success else paramiko.AUTH_FAILED

  def close(self):
    if self.heralding_connector:
      try:
        self.heralding_connector.close()
      except Exception:
        logger.exception("Failed to close heralding_connector")

  def check_channel_request(self, kind, chanid):
    if kind == "session":
      return paramiko.OPEN_SUCCEEDED
    return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

  def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
    return True

  def check_channel_shell_request(self, channel):
    return True

  def check_channel_exec_request(self, channel, command):
    return True

  def _trigger_cowrie(self):
    try:
      res = requests.post("http://launcher:5000/trigger/cowrie", timeout=5)
      if res.status_code == 200:
        logger.info("Cowrie started in auth stage")
        self.cowrie_launched = True
      else:
        logger.error("Failed to start cowrie at auth (HTTP %s)", res.status_code)
    except Exception:
      logger.exception("Error triggering cowrie at auth")

def start_proxy():
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.bind((HOST, PORT))
  sock.listen(100)
  logger.info("SSH Proxy listening on %s:%s", HOST, PORT)

  while True:
    client = None
    transport = None
    server = None

    try:
      client, addr = sock.accept()
      logger.info("Connection from %s", addr)

      transport = paramiko.Transport(client)
      transport.add_server_key(HOST_KEY)
      server = SSHProxyServer(addr)

      try:
        transport.start_server(server=server)
      except paramiko.SSHException:
        logger.warning("SSH negotiation failed")
        server.close()

        try:
          transport.close()
        except Exception:
          logger.exception("Failed to close transport after SSHException")

        try:
          client.close()
        except Exception:
          logger.exception("Failed to close client after SSHException")

        continue

      except EOFError:
        logger.info("Client closed connection during handshake (EOF)")
        server.close()

        try:
          transport.close()
        except Exception:
          logger.exception("Failed to close transport after EOFError")

        try:
          client.close()
        except Exception:
          logger.exception("Failed to close client after EOFError")

        continue

      except Exception:
        logger.exception("Unexpected error during SSH handshake")
        server.close()

        try:
          transport.close()
        except Exception:
          logger.exception("Failed to close transport after unexpected error")

        try:
          client.close()
        except Exception:
          logger.exception("Failed to close client after unexpected error")

        continue

      try:
        chan = transport.accept(20)

        if chan is None:
          logger.warning("No channel")
          server.close()
          transport.close()
          client.close()

          continue

        username = server.username
        password = server.password

        start_time = time.time()

        threading.Thread(
          target=handler.handle_session,
          args=(chan, username, password, addr, start_time, server.cowrie_launched),
          daemon=True
        ).start()

        server.close()

      except EOFError:
        logger.info("Client closed connection after authentication (EOF)")
        server.close()

        try:
          transport.close()
        except Exception:
          logger.exception("Failed to close transport after post-auth EOFError")

        try:
          client.close()
        except Exception:
          logger.exception("Failed to close client after post-auth EOFError")

      except Exception:
        logger.exception("Error during session handling")
        server.close()

        try:
          transport.close()
        except Exception:
          logger.exception("Failed to close transport after session error")

        try:
          client.close()
        except Exception:
          logger.exception("Failed to close client after session error")

    except Exception:
      logger.exception("Error accepting connection")

      try:
        if server:
          server.close()
      except Exception:
        logger.exception("Failed to close server after accept error")

      try:
        if transport:
          transport.close()
      except Exception:
        logger.exception("Failed to close transport after accept error")

      try:
        if client:
          client.close()
      except Exception:
        logger.exception("Failed to close client after accept error")

if __name__ == "__main__":
  start_proxy()
