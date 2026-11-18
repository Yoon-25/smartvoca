#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 1차 "확인 불가" 1,460개를 한국어 위키낱말사전 뜻 풀이와 자동 대조 (이슈 #7)
# 파일 위치: ai-agent/claude/261118_사전대조/script/verify_unverified.py
# 판정: 확인됨(같은 품사 뜻 일치) / 품사 확인 필요(다른 품사에서만 일치) / 뜻 풀이 없음 / 재확인 필요(자동 비교 불일치)

import csv
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("verify_common", os.path.join(HERE, "verify_with_ko_wiktionary.py"))
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)

BASE = common.BASE
RAW = os.path.join(BASE, "data", "ko_wiktionary_raw_unverified.json")
RESULT_CSV = common.RESULT_CSV
OUT_CSV = os.path.join(BASE, "미확인1460_대조결과_261118.csv")


def main() -> int:
    with open(RAW, encoding="utf-8") as raw_file:
        pages = json.load(raw_file)["pages"]
    with open(RESULT_CSV, encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.reader(csv_file))[1:]

    out_rows = []
    counts: dict[str, int] = {}
    for row in rows:
        if row[4] != "확인 불가":
            continue
        number, english, pos, meaning = row[0], row[1], row[2], row[3]
        senses = common.english_senses(pages.get(english) or "")
        same_pos = senses.get(pos, []) + senses.get("미상", [])
        all_senses = [s for values in senses.values() for s in values]
        if not all_senses:
            verdict, note = "뜻 풀이 없음", "위키낱말사전 항목 없음 또는 뜻 없음"
        elif common.matches(meaning, same_pos):
            verdict, note = "확인됨", "같은 품사 뜻 풀이와 일치"
        elif common.matches(meaning, all_senses):
            verdict, note = "품사 확인 필요", "다른 품사에서는 일치"
        else:
            verdict = "재확인 필요"
            note = " / ".join(same_pos[:3]) if same_pos else " / ".join(all_senses[:3])
        counts[verdict] = counts.get(verdict, 0) + 1
        out_rows.append([number, english, pos, meaning, verdict, note])

    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["번호", "영단어", "품사(CSV)", "뜻(CSV)", "판정", "위키낱말사전 뜻 풀이"])
        writer.writerows(out_rows)
    print(counts, sum(counts.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
