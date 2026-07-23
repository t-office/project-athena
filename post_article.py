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


def now_jst():
    return datetime.datetime.now(datetime.timezone.utc).astimezone(JST)


def today_str():
    return now_jst().strftime("%Y-%m-%d")


def write_log(log_entry):
    os.makedirs("logs", exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    print(json.dumps(log_entry, ensure_ascii=False, indent=2))


def already_posted_today_in_log():
    """logs/post_log.jsonl に本日(JST)分のsuccess記録があるか確認"""
    if not os.path.exists(LOG_FILE):
        return False
    today = today_str()
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("result") == "success" and entry.get("timestamp", "").startswith(today):
                    return True
    except Exception:
        return False
    return False


def already_posted_today_in_wp(auth):
    """
    ログのpush漏れに備えた保険。WordPress側に本日(JST)作成の投稿が
    既に存在するかを直接確認する。
    注意: WordPress REST APIのafterパラメータがpost_date/post_date_gmt
    どちらを基準にするかは環境依存の可能性があるため、実機で必ず
    「日付境界(12時直後)」の挙動を確認すること。
    """
    start_jst = now_jst().replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc_iso = start_jst.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    params = {
        "after": start_utc_iso,
        "status": "publish,draft,future,pending",
        "per_page": 1,
        "context": "edit",
    }
    try:
        resp = requests.get(WP_URL, params=params, auth=auth, timeout=30)
        if resp.status_code == 200:
            return len(resp.json()) > 0
        return False  # 確認自体が失敗した場合はログ側判定のみに委ねる
    except Exception:
        return False


def main():
    log_entry = {"timestamp": now_jst().isoformat()}

    try:
        with open(ARTICLE_FILE, "r", encoding="utf-8") as f:
            article = json.load(f)
    except Exception as e:
        log_entry["result"] = "error"
        log_entry["error"] = f"article.json の読み込みに失敗: {e}"
        write_log(log_entry)
        return

    title = article.get("title")
    content = article.get("content")
    log_entry["title"] = title

    if not title or not content:
        log_entry["result"] = "error"
        log_entry["error"] = "article.json に title または content がありません"
        write_log(log_entry)
        return

    auth = HTTPBasicAuth(WP_USER, WP_APP_PASSWORD)

    force = os.environ.get("FORCE_POST") == "1"

    if not force:
        if already_posted_today_in_log():
            log_entry["result"] = "skipped_duplicate"
            log_entry["reason"] = "本日分の投稿ログが既に存在(ログベース判定)"
            write_log(log_entry)
            print("本日は既に投稿済みのためスキップしました。")
            return

        if already_posted_today_in_wp(auth):
            log_entry["result"] = "skipped_duplicate"
            log_entry["reason"] = "本日分の投稿がWordPress側に既に存在(WP側判定)"
            write_log(log_entry)
            print("本日は既に投稿済みのためスキップしました(WordPress側で検出)。")
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
