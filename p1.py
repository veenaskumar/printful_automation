import requests

api_key = "8NDoNkeGWdSm2PP8cZu0onv5lfRhxED75h6oXzXe"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

response = requests.get("https://api.printful.com/store", headers=headers)
print(response.json())
