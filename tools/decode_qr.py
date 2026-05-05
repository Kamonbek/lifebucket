#!/usr/bin/env python3
"""
Decode QR codes from a local image path or image URL using free public services.

Primary backend (free, no API key):
  - api.qrserver.com/v1/read-qr-code/
Secondary fallback for URL input:
  - zxing.org/w/decode.jsp?u=<image_url>

Usage:
  python3 tools/decode_qr.py --file /path/to/qr.jpg
  python3 tools/decode_qr.py --url https://example.com/qr.png
"""

import argparse
import json
import mimetypes
import os
import re
import sys
import urllib.parse
import urllib.request


def _multipart_form(field_name: str, file_path: str):
    boundary = "----HermesQRBoundary7MA4YWxkTrZu0gW"
    ctype = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    filename = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    body = []
    body.append(f"--{boundary}\r\n".encode())
    body.append(
        (
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n"
        ).encode()
    )
    body.append(file_bytes)
    body.append(f"\r\n--{boundary}--\r\n".encode())
    payload = b"".join(body)
    content_type = f"multipart/form-data; boundary={boundary}"
    return payload, content_type


def decode_with_qrserver_file(file_path: str):
    payload, content_type = _multipart_form("file", file_path)
    req = urllib.request.Request(
        "https://api.qrserver.com/v1/read-qr-code/",
        data=payload,
        headers={
            "Content-Type": content_type,
            "User-Agent": "HermesQR/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", "ignore")
    data = json.loads(raw)
    return extract_qr_texts(data), {"backend": "qrserver_file", "raw": data}


def decode_with_qrserver_url(image_url: str):
    endpoint = "https://api.qrserver.com/v1/read-qr-code/?fileurl=" + urllib.parse.quote(image_url, safe="")
    req = urllib.request.Request(endpoint, headers={"User-Agent": "HermesQR/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", "ignore")
    data = json.loads(raw)
    return extract_qr_texts(data), {"backend": "qrserver_url", "raw": data}


def decode_with_zxing_url(image_url: str):
    endpoint = "https://zxing.org/w/decode.jsp?u=" + urllib.parse.quote(image_url, safe="")
    req = urllib.request.Request(endpoint, headers={"User-Agent": "HermesQR/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "ignore")

    # Capture result from page text.
    m = re.search(r"Parsed Result</th>\s*<td><pre>(.*?)</pre>", html, re.S | re.I)
    if m:
        result = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if result:
            return [result], {"backend": "zxing_url", "raw_excerpt": result[:500]}

    if "No barcode found" in html:
        return [], {"backend": "zxing_url", "raw_excerpt": "No barcode found"}
    return [], {"backend": "zxing_url", "raw_excerpt": "No parsed result"}


def extract_qr_texts(resp_json):
    texts = []
    if not isinstance(resp_json, list):
        return texts
    for entry in resp_json:
        for sym in entry.get("symbol", []):
            txt = sym.get("data")
            err = sym.get("error")
            if txt and not err:
                texts.append(txt)
    # deduplicate preserving order
    out = []
    seen = set()
    for t in texts:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", help="Local image path")
    g.add_argument("--url", help="Public image URL")
    args = p.parse_args()

    attempts = []

    try:
        if args.file:
            if not os.path.exists(args.file):
                raise FileNotFoundError(args.file)
            texts, meta = decode_with_qrserver_file(args.file)
            attempts.append(meta)
            if texts:
                print(json.dumps({"ok": True, "texts": texts, "backend": meta["backend"]}, ensure_ascii=False))
                return
            print(json.dumps({"ok": False, "error": "No QR detected", "attempts": attempts}, ensure_ascii=False))
            return

        # URL mode
        texts, meta = decode_with_qrserver_url(args.url)
        attempts.append(meta)
        if texts:
            print(json.dumps({"ok": True, "texts": texts, "backend": meta["backend"]}, ensure_ascii=False))
            return

        # Fallback: download URL and decode as file upload (more reliable when remote blocks fetches)
        try:
            tmp_path, _ = urllib.request.urlretrieve(args.url)
            texts3, meta3 = decode_with_qrserver_file(tmp_path)
            meta3["backend"] = "qrserver_file_from_url"
            attempts.append(meta3)
            if texts3:
                print(json.dumps({"ok": True, "texts": texts3, "backend": meta3["backend"], "attempts": attempts}, ensure_ascii=False))
                return
        except Exception as e:
            attempts.append({"backend": "download_then_file", "error": str(e)})

        texts2, meta2 = decode_with_zxing_url(args.url)
        attempts.append(meta2)
        if texts2:
            print(json.dumps({"ok": True, "texts": texts2, "backend": meta2["backend"], "attempts": attempts}, ensure_ascii=False))
            return

        print(json.dumps({"ok": False, "error": "No QR detected", "attempts": attempts}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e), "attempts": attempts}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
