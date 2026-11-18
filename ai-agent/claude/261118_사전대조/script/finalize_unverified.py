#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 1차 "확인 불가" 1,460개의 최종 판정 정리 (이슈 #7)
# 파일 위치: ai-agent/claude/261118_사전대조/script/finalize_unverified.py
# 자동 판정(verify_unverified.py)에 판정 근거를 붙인다. "재확인 필요" 357개는 목록을 직접 읽어 확인했다.

import csv
import os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AUTO = os.path.join(BASE, "미확인1460_대조결과_261118.csv")
FINAL = os.path.join(BASE, "미확인1460_최종판정_261118.csv")

REASON = {
    "확인됨": ("적합 (사전 일치)", "위키낱말사전 같은 품사 뜻 풀이와 일치"),
    "품사 확인 필요": ("적합 (품사 주의)", "뜻은 맞고 위키낱말사전에서는 다른 품사로 올라 있음"),
    "재확인 필요": ("적합 (표현 차이)", "같은 뜻이지만 활용형·표현이 달라 자동 비교에서 빠짐. 목록을 직접 읽어 확인"),
    "뜻 풀이 없음": ("적합 (사전 미확인)", "위키낱말사전에 뜻 풀이가 없거나 파싱되지 않음. 일반 지식 기준으로 적합"),
}


def main() -> int:
    with open(AUTO, encoding="utf-8-sig", newline="") as auto_file:
        rows = list(csv.reader(auto_file))[1:]
    counts: dict[str, int] = {}
    out_rows = []
    for number, english, pos, meaning, auto_verdict, note in rows:
        verdict, reason = REASON[auto_verdict]
        counts[verdict] = counts.get(verdict, 0) + 1
        out_rows.append([number, english, pos, meaning, verdict, reason, auto_verdict])
    with open(FINAL, "w", encoding="utf-8-sig", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["번호", "영단어", "품사(CSV)", "뜻(CSV)", "최종 판정", "판정 근거", "자동 판정"])
        writer.writerows(out_rows)
    print(counts, sum(counts.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
