#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 불일치 의심 단어를 한국어 위키낱말사전(ko.wiktionary) 표제어로 조회해 원문 저장 (이슈 #7)
# 파일 위치: ai-agent/claude/261118_사전대조/script/fetch_ko_wiktionary.py
# 출처: 한국어 위키낱말사전 (CC BY-SA 4.0). 공개 MediaWiki API를 배치(50개)로 호출한다.

import csv
import json
import os
import time
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
RESULT_CSV = os.path.join(ROOT, "ai-agent", "claude", "261118_사전대조", "대조결과_261118.csv")
OUT = os.path.join(ROOT, "ai-agent", "claude", "261118_사전대조", "data", "ko_wiktionary_raw.json")
API = "https://ko.wiktionary.org/w/api.php"
USER_AGENT = "smartvoca-study-tool/0.1 (personal vocabulary review; contact: repo owner)"


def targets() -> list[str]:
    with open(RESULT_CSV, encoding="utf-8-sig", newline="") as csv_file:
        return [row[1] for row in csv.reader(csv_file) if len(row) > 4 and row[4] == "불일치 의심"]


def fetch_batch(titles: list[str]) -> dict:
    params = {
        "action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
        "format": "json", "formatversion": "2", "redirects": "1",
        "titles": "|".join(titles),
    }
    request = urllib.request.Request(API + "?" + urllib.parse.urlencode(params),
                                     headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    words = targets()
    print("targets", len(words), flush=True)
    result = {}
    for start in range(0, len(words), 50):
        batch = words[start:start + 50]
        data = fetch_batch(batch)
        for page in data.get("query", {}).get("pages", []):
            title = page.get("title", "")
            if page.get("missing"):
                result[title] = None
                continue
            revisions = page.get("revisions", [])
            result[title] = revisions[0]["slots"]["main"]["content"] if revisions else None
        time.sleep(1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as out:
        json.dump({"source": "https://ko.wiktionary.org (CC BY-SA 4.0)", "pages": result}, out, ensure_ascii=False, indent=1)
    found = sum(1 for v in result.values() if v)
    print(f"done: requested {len(words)}, pages found {found}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
