#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - kaikki.org 영어 Wiktionary JSONL을 스트리밍하며 단어장 1~1883번 단어만 추출 (이슈 #7)
# 파일 위치: ai-agent/claude/261118_사전대조/script/extract_kaikki_subset.py
# 원본 3.4GB는 저장하지 않고, 필요한 항목만 subset JSON으로 남긴다. 출처: kaikki.org (Wiktionary, CC BY-SA)

import csv
import json
import os
import sys
import urllib.request

SOURCE_URL = "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
WORD_CSV = os.path.join(ROOT, "data", "voca_2000.csv")
OUT_PATH = os.path.join(ROOT, "ai-agent", "claude", "261118_사전대조", "data", "kaikki_subset.json")
LIMIT_NUMBER = 1883


def load_target_words() -> dict:
    targets = {}
    with open(WORD_CSV, encoding="utf-8-sig", newline="") as csv_file:
        for row in csv.DictReader(csv_file):
            number = int(row["번호"])
            if number <= LIMIT_NUMBER:
                targets[row["영단어"].strip().lower()] = {
                    "number": number, "english": row["영단어"], "pos": row["품사"], "meaning": row["뜻"],
                }
    return targets


def main() -> int:
    targets = load_target_words()
    print(f"targets: {len(targets)}", flush=True)
    found = {}
    scanned = 0
    with urllib.request.urlopen(SOURCE_URL, timeout=120) as response:
        for raw_line in response:
            scanned += 1
            if scanned % 500000 == 0:
                print(f"scanned {scanned:,} lines, found {len(found)}", flush=True)
            # 빠른 사전 검사: 단어 문자열이 줄 안에 있을 때만 파싱한다
            line = raw_line.decode("utf-8", errors="replace")
            entry = json.loads(line)
            word = str(entry.get("word", "")).lower()
            if word not in targets:
                continue
            glosses = []
            for sense in entry.get("senses", [])[:5]:
                glosses.extend(sense.get("glosses", [])[:1])
            korean = [t.get("word", "") for t in entry.get("translations", []) if t.get("lang_code") == "ko"]
            found.setdefault(word, []).append({
                "pos": entry.get("pos", ""),
                "glosses": glosses,
                "korean_translations": korean,
            })
    result = {"source": SOURCE_URL, "license": "CC BY-SA (Wiktionary via kaikki.org)", "words": found}
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as out:
        json.dump(result, out, ensure_ascii=False, indent=1)
    print(f"done: scanned {scanned:,}, matched words {len(found)} of {len(targets)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
