import os
import requests

API_KEY = os.getenv("LLM_API_KEY")
if not API_KEY:
    raise SystemExit("Set LLM_API_KEY in your environment first")

url = "https://generativelanguage.googleapis.com/v1/models"

resp = requests.get(url, params={"key": API_KEY}, timeout=30)
print("Status", resp.status_code)
print(resp.text[:4000])  # print first chunk so it is readable
