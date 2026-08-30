import time
import requests
import os
DATASET_ID = "gd_lpfbbndm1xnopbrcr0"

API_TOKEN = os.getenv("BRIGHTDATA_API_KEY")

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Step 1: Trigger collection
response = requests.post(
    "https://api.brightdata.com/datasets/v3/trigger",
    params={"dataset_id": DATASET_ID, "format": "json"},
    headers=headers,
    json=[
        {
            "job_title": "Data Engineer",
            "location": "United States"
        }
    ]
)
response.raise_for_status()
snapshot_id = response.json()["snapshot_id"]
print(f"Snapshot ID: {snapshot_id}")

# Step 2: Poll for completion
while True:
    status_response = requests.get(
        f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
        headers=headers
    )
    status_response.raise_for_status()
    status_data = status_response.json()
    status = status_data.get("status")
    print(f"Status: {status}")

    if status == "ready":
        break
    if status == "failed":
        raise Exception("Collection failed")

    time.sleep(5)

# Step 3: Download results
download_response = requests.get(
    f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json",
    headers=headers
)
download_response.raise_for_status()
results = download_response.json()

print(f"Collected {len(results)} records")
print(results[:2])
