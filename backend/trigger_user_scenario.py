import requests
import time

# Retry logic to wait for server startup
for i in range(5):
    try:
        response = requests.post(
            "http://127.0.0.1:8000/check-grammar",
            data={"base_url": "https://knightvestresidential.com/", "menu_options": "careers"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        break
    except Exception as e:
        print(f"Attempt {i+1} failed: {e}")
        time.sleep(2)
