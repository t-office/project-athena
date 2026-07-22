import requests

resp = requests.post("https://httpbin.org/post", json={"title": "test"})
print(resp.status_code)
print(resp.text)
