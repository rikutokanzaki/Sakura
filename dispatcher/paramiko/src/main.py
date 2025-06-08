import socket
import threading
import paramiko
from auth import auth_user
from connector import connect_server
from session import handler

HOST = "0.0.0.0"
PORT = 22

class SSHProxyServer(paramiko.ServerInterface):
  def __init__(self):
    self.event = threading.Event()
    self.username = None
    self.password = None
    self.authenticator = auth_user.Authenticator()

  def check_auth_password(self, username, password):
    self.username = username
    self.password = password

    try:
      connect_server.record_in_heralding(username=username, password=password)
    except Exception as e:
      pass

    if self.authenticator.authenticate(username, password):
      return paramiko.AUTH_SUCCESSFUL
    else:
      return paramiko.AUTH_FAILED

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

def start_proxy():
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  sock.bind((HOST, PORT))
  sock.listen(100)
  print(f"SSH Proxy listening on {HOST}:{PORT}")

  while True:
    try:
      client, addr = sock.accept()
      print(f"Connection from {addr}")

      transport = paramiko.Transport(client)
      host_key = paramiko.RSAKey(filename="/certs/ssh_host_rsa_key")
      transport.add_server_key(host_key)
      server = SSHProxyServer()

      try:
        transport.start_server(server=server)
      except paramiko.SSHException:
        print("SSH negotiation failed")
        continue
      except EOFError:
        print("Client closed connection during handshake (EOF)")
        continue
      except Exception as e:
        print(f"Unexpected error during SSH handshake: {e}")
        continue

      try:
        chan = transport.accept(20)
        if chan is None:
          print("No channel")
          continue

        username = server.username
        password = server.password

        threading.Thread(
          target=handler.handle_session,
          args=(chan, username, password),
          daemon=True
        ).start()

      except EOFError:
        print("Client closed connection after authentication (EOF)")
      except Exception as e:
        print(f"Error during session handling: {e}")

    except Exception as e:
      print(f"Error acceptiong connection: {e}")

if __name__ == "__main__":
  start_proxy()