import logging
import requests

logger = logging.getLogger(__name__)

def notify_launcher():
  try:
    response = requests.post("http://launcher:5000/trigger/cowrie")
    return response.status_code == 200
  except Exception:
    logger.exception("Failed to notify launcher")
    return False
