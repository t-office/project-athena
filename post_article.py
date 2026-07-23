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
JST = datetime.timezone(datetime.timedelta(hours=9))


def now_jst_iso():
    return datetime.datetime.now(datetime.timezone.utc).astimezone(JST).isoformat()


def write_log(log_entry):
    os.makedirs("logs", exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    print(json.dumps(log_entry, ensure_ascii=False, indent=2))


def main():
    log_entry = {"timestamp": now_jst_iso()}

    # 1. article.json の読み込み
    try:
        with open(ARTICLE_FILE, "r", encoding="utf-8") as f:
            article = json.load(f)
    except Exception as e:
        log_entry["result"] = "error"
        log_entry["error"] = f"article.json の読み込みに失敗: {e}"
        write_log(log_entry)
        return

    # 2. 必須フィールドのチェック
    title = article.get("title")
    content = article.get("content")
    log_entry["title"] = title

    if not title or not content:
        log_entry["result"] = "error"
        log_entry["error"] = "article.json に title または content がありません"
        write_log(log_entry)
        return

    payload = {
        "title": title,
        "content": content,
        "status": "publish",
    }
    if article.get("excerpt"):
        payload["excerpt"] = article["excerpt"]
    if article.get("slug"):
        payload["slug"] = article["slug"]

    auth = HTTPBasicAuth(WP_USER, WP_APP_PASSWORD)

    # 3. WordPressへ投稿
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

    write_log(log_entry)


if __name__ == "__main__":
    main()
