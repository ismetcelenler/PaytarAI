import requests
import pprint

url = "http://127.0.0.1:8000/api/v1/chat"
payload = {
    "message": "öksüren hayvana ne yapılır",
    "user_role": "veterinarian",
    "input_source": "text"
}

try:
    response = requests.post(url, json=payload)
    print("STATUS:", response.status_code)
    pprint.pprint(response.json())
except Exception as e:
    print("ERROR:", e)
