#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 한국어 위키낱말사전 뜻 풀이와 단어장 뜻을 대조 (이슈 #7, 불일치 의심 140개)
# 파일 위치: ai-agent/claude/261118_사전대조/script/verify_with_ko_wiktionary.py

import csv
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
BASE = os.path.join(ROOT, "ai-agent", "claude", "261118_사전대조")
RAW = os.path.join(BASE, "data", "ko_wiktionary_raw.json")
RESULT_CSV = os.path.join(BASE, "대조결과_261118.csv")
OUT_CSV = os.path.join(BASE, "2차대조결과_261118.csv")

POS_HEADERS = {"명사": "명사", "동사": "동사", "형용사": "형용사", "부사": "부사"}
SENSE_LINE = re.compile(r"^#\s*(?!\*)(.+)$")


def clean(text: str) -> str:
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"'''?", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def english_senses(wikitext: str) -> dict:
    """영어 섹션에서 품사별 뜻 풀이 줄을 모은다."""
    english = wikitext
    start = english.find("== 영어 ==")
    if start >= 0:
        english = english[start + len("== 영어 =="):]
        nxt = re.search(r"\n== [^=]", english)
        if nxt:
            english = english[:nxt.start()]
    senses: dict[str, list[str]] = {}
    current = None
    for line in english.splitlines():
        header = re.match(r"^=+\s*([^=]+?)\s*=+\s*$", line)
        if header:
            title = header.group(1)
            current = next((v for k, v in POS_HEADERS.items() if k in title), None)
            if current is None and title != "영어":
                current = "미상"
            continue
        if current is None:
            # 품사 제목 없이 바로 나온 뜻 풀이는 "미상"으로 모은다
            if re.match(r"^#", line):
                current = "미상"
            else:
                continue
        match = SENSE_LINE.match(line)
        if match:
            senses.setdefault(current, []).append(clean(match.group(1)))
    return senses


def tokens(text: str) -> list[str]:
    # 괄호 안 설명은 떼고 비교한다. 예: 이(치아) -> 이
    text = re.sub(r"\([^)]*\)", "", text)
    return [t.strip() for t in text.replace(",", "/").split("/") if t.strip()]


def matches(csv_meaning: str, sense_texts: list[str]) -> bool:
    for mine in tokens(csv_meaning):
        for sense in sense_texts:
            if len(mine) >= 1 and mine in sense:
                return True
    return False


def main() -> int:
    with open(RAW, encoding="utf-8") as raw_file:
        pages = json.load(raw_file)["pages"]
    with open(RESULT_CSV, encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.reader(csv_file))
    header, body = rows[0], rows[1:]

    out_rows = []
    counts: dict[str, int] = {}
    for row in body:
        if row[4] != "불일치 의심":
            continue
        number, english, pos, meaning = row[0], row[1], row[2], row[3]
        senses = english_senses(pages.get(english) or "")
        same_pos = senses.get(pos, []) + senses.get("미상", [])
        all_senses = [s for values in senses.values() for s in values]
        if not all_senses:
            verdict, note = "확인 불가", "한국어 위키낱말사전 항목 없음 또는 뜻 없음"
        elif matches(meaning, same_pos):
            verdict, note = "확인됨", "같은 품사 뜻 풀이와 일치"
        elif matches(meaning, all_senses):
            verdict, note = "품사 확인 필요", "다른 품사에서는 일치"
        else:
            verdict = "불일치 재확인"
            note = " / ".join(same_pos[:3]) if same_pos else " / ".join(all_senses[:3])
        counts[verdict] = counts.get(verdict, 0) + 1
        out_rows.append([number, english, pos, meaning, verdict, note])

    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["번호", "영단어", "품사(CSV)", "뜻(CSV)", "2차 판정", "한국어 위키낱말사전 뜻 풀이"])
        writer.writerows(out_rows)
    print(counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
