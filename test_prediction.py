import requests
import time

url = "http://127.0.0.1:5000/predict"

payload = {
    "cpu_usage": 95,
    "memory_usage": 90,
    "disk_usage": 95,
    "network_latency": 500,
    "request_rate": 2000,
    "pod_restarts": 10,
    "error_rate": 25,
    "response_time": 800
}
for i in range(20):
    response = requests.post(url, json=payload)
    print(f"Sample {i+1}: {response.json()}")
    time.sleep(1)