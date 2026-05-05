#!/usr/bin/env python3
"""Set Telegram bot menu button to open a Web App dashboard.

Usage:
  TELEGRAM_BOT_TOKEN=... python3 tools/telegram_set_webapp_button.py --url https://lifebucket.me/dashboard/
"""
import argparse
import json
import os
import urllib.request
import urllib.parse


def tg_api(token: str, method: str, params: dict):
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True, help="HTTPS URL for Telegram Web App")
    p.add_argument("--text", default="Open Dashboard", help="Button text")
    args = p.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_STT_BOT_TOKEN")
    if not token:
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN (or TELEGRAM_STT_BOT_TOKEN)")

    if not args.url.startswith("https://"):
        raise SystemExit("Web App URL must be https://")

    menu_button = {
        "type": "web_app",
        "text": args.text,
        "web_app": {"url": args.url},
    }

    # Set globally for all private chats with this bot
    resp = tg_api(token, "setChatMenuButton", {"menu_button": json.dumps(menu_button)})
    print(json.dumps(resp, ensure_ascii=False))


if __name__ == "__main__":
    main()
