#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 단어장 뜻·품사를 kaikki subset(Wiktionary)과 대조해 일치/불일치/확인 불가로 분류 (이슈 #7)
# 파일 위치: ai-agent/claude/261118_사전대조/script/compare_meanings.py

import csv
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
WORD_CSV = os.path.join(ROOT, "data", "voca_2000.csv")
SUBSET = os.path.join(ROOT, "ai-agent", "claude", "261118_사전대조", "data", "kaikki_subset.json")
REPORT = os.path.join(ROOT, "ai-agent", "claude", "261118_사전대조", "대조결과_261118.csv")

POS_MAP = {"명사": "noun", "동사": "verb", "형용사": "adj", "부사": "adv"}


def tokens(text: str) -> list[str]:
    return [t.strip() for t in text.replace(",", "/").split("/") if t.strip()]


def overlaps(csv_meaning: str, korean: list[str]) -> bool:
    for mine in tokens(csv_meaning):
        for theirs in korean:
            if mine == theirs or mine in theirs or theirs in mine:
                return True
    return False


def main() -> int:
    with open(SUBSET, encoding="utf-8") as subset_file:
        words = json.load(subset_file)["words"]

    rows = []
    with open(WORD_CSV, encoding="utf-8-sig", newline="") as csv_file:
        for row in csv.DictReader(csv_file):
            number, english, pos, meaning = row["번호"], row["영단어"], row["품사"], row["뜻"]
            if int(number) > 1883:
                continue
            entries = words.get(english.lower(), [])
            if not entries:
                rows.append([number, english, pos, meaning, "확인 불가", "사전 항목 없음", ""])
                continue
            korean = [k for e in entries for k in e["korean_translations"]]
            pos_list = sorted({e["pos"] for e in entries})
            pos_ok = POS_MAP.get(pos) in pos_list
            gloss = " | ".join(g for e in entries for g in e["glosses"][:2])[:200]
            if not korean:
                status, note = "확인 불가", "한국어 번역 없음"
            elif overlaps(meaning, korean):
                status, note = "일치", ""
            else:
                status, note = "불일치 의심", "한국어 번역: " + ", ".join(sorted(set(korean))[:8])
            if not pos_ok:
                note = (note + "; " if note else "") + f"품사 확인 필요 (사전: {','.join(pos_list)})"
            rows.append([number, english, pos, meaning, status, note, gloss])

    with open(REPORT, "w", encoding="utf-8-sig", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["번호", "영단어", "품사(CSV)", "뜻(CSV)", "판정", "비고", "영어 뜻(사전)"])
        writer.writerows(rows)

    counts = {}
    for row in rows:
        counts[row[4]] = counts.get(row[4], 0) + 1
    print(counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
