import os
import json
import datetime
import requests
from requests.auth import HTTPBasicAuth

WP_URL = os.environ["WP_URL"]
WP_USER = os.environ["WP_USER"]
WP_APP_PASSWORD = os.environ["WP_APP_PASSWORD"]

ARTICLE_FILE = "article.json"
LOG_FILE = "logs/post_log.jsonl"

def main():
    with open(ARTICLE_FILE, "r", encoding="utf-8") as f:
        article = json.load(f)

    payload = {
        "title": article["title"],
        "content": article["content"],
        "status": "draft",
    }
    if "excerpt" in article:
        payload["excerpt"] = article["excerpt"]
    if "slug" in article:
        payload["slug"] = article["slug"]

    auth = HTTPBasicAuth(WP_USER, WP_APP_PASSWORD)

    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "title": article["title"],
    }

    try:
        resp = requests.post(WP_URL, json=payload, auth=auth, timeout=30)
        log_entry["http_status"] = resp.status_code
        if resp.status_code in (200, 201):
            data = resp.json()
            log_entry["post_id"] = data.get("id")
            log_entry["post_url"] = data.get("link")
            log_entry["result"] = "success"
        else:
            log_entry["result"] = "failed"
            log_entry["response_body"] = resp.text[:1000]
    except Exception as e:
        log_entry["result"] = "error"
        log_entry["error"] = str(e)

    os.makedirs("logs", exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    print(json.dumps(log_entry, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
