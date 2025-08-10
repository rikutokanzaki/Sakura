import requests

def notify_launcher():
  try:
    response = requests.post("http://launcher:5000/trigger/cowrie")
    return response.status_code == 200
  except Exception as e:
    print(f"Failed to notify launcher: {e}")
    return False
