import os
import requests
from requests.auth import HTTPBasicAuth

WP_URL = os.environ["WP_URL"]
WP_USER = os.environ["WP_USER"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]

payload = {
    "title": "固定テストタイトル",
    "content": "これはRoutineから投稿したテスト本文です。",
    "status": "draft"
}

auth = HTTPBasicAuth(WP_USER, WP_APP_PASSWORD)
resp = requests.post(WP_URL, json=payload, auth=auth, timeout=30)

print("ステータスコード:", resp.status_code)
print("レスポンス内容:")
print(resp.text)
