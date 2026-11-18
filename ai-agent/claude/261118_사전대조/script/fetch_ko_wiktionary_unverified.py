#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 1차 대조 "확인 불가" 1,460개를 한국어 위키낱말사전 표제어로 조회해 원문 저장 (이슈 #7)
# 파일 위치: ai-agent/claude/261118_사전대조/script/fetch_ko_wiktionary_unverified.py
# 출처: 한국어 위키낱말사전 (CC BY-SA 4.0). 공개 MediaWiki API, 50개씩 배치, 배치 사이 1초 대기.

import csv
import json
import os
import time

import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("fetch_common", os.path.join(HERE, "fetch_ko_wiktionary.py"))
fetch_common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_common)

ROOT = fetch_common.ROOT
RESULT_CSV = fetch_common.RESULT_CSV
OUT = os.path.join(ROOT, "ai-agent", "claude", "261118_사전대조", "data", "ko_wiktionary_raw_unverified.json")


def targets() -> list[str]:
    with open(RESULT_CSV, encoding="utf-8-sig", newline="") as csv_file:
        return sorted({row[1] for row in csv.reader(csv_file) if len(row) > 4 and row[4] == "확인 불가"})


BATCH_PAUSE_SECONDS = 5
MAX_RETRIES = 6


def fetch_with_retry(batch: list[str]) -> dict:
    """429(요청 과다)가 오면 대기 시간을 늘려 다시 시도한다."""
    import urllib.error

    for attempt in range(MAX_RETRIES):
        try:
            return fetch_common.fetch_batch(batch)
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == MAX_RETRIES - 1:
                raise
            wait = 30 * (attempt + 1)
            print(f"429 received, waiting {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def main() -> int:
    words = targets()
    print("targets", len(words), flush=True)
    result = {}
    for start in range(0, len(words), 50):
        batch = words[start:start + 50]
        data = fetch_with_retry(batch)
        for page in data.get("query", {}).get("pages", []):
            title = page.get("title", "")
            if page.get("missing"):
                result[title] = None
                continue
            revisions = page.get("revisions", [])
            result[title] = revisions[0]["slots"]["main"]["content"] if revisions else None
        time.sleep(BATCH_PAUSE_SECONDS)
    with open(OUT, "w", encoding="utf-8") as out:
        json.dump({"source": "https://ko.wiktionary.org (CC BY-SA 4.0)", "pages": result}, out, ensure_ascii=False, indent=1)
    found = sum(1 for v in result.values() if v)
    print(f"done: requested {len(words)}, pages found {found}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
