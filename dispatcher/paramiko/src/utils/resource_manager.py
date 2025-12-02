import logging

logger = logging.getLogger(__name__)

def close_channel(channel):
  if channel is None:
    return

  try:
    channel.close()
  except Exception:
    logger.exception("Failed to close channel")

def close_shell(shell):
  if shell is None:
    return

  try:
    shell.close()
  except Exception:
    logger.exception("Failed to close shell")

def close_transport(transport):
  if transport is None:
    return

  try:
    transport.close()
  except Exception:
    logger.exception("Failed to close transport")

def close_client(client):
  if client is None:
    return

  try:
    client.close()
  except Exception:
    logger.exception("Failed to close SSH client")

def close_socket(sock):
  if sock is None:
    return

  try:
    sock.close()
  except Exception:
    logger.exception("Failed to close socket")

def close_server(server):
  if server is None:
    return

  try:
    server.close()
  except Exception:
    logger.exception("Failed to close server")

def close_ssh_connection(client=None, shell=None, transport=None, channel=None):
  close_shell(shell)
  close_channel(channel)
  close_transport(transport)
  close_client(client)

def close_proxy_connection(server=None, transport=None, client=None):
  close_server(server)
  close_transport(transport)
  close_socket(client)
