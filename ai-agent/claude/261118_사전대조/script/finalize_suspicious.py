#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 불일치 의심 140개의 최종 판정 정리 (이슈 #7)
# 파일 위치: ai-agent/claude/261118_사전대조/script/finalize_suspicious.py
# 2차 자동 판정(위키낱말사전)에 사람이 읽고 내린 판정을 더한다. 판정 근거는 "비고" 열에 적는다.

import csv
import os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SECOND = os.path.join(BASE, "2차대조결과_261118.csv")
FINAL = os.path.join(BASE, "최종판정_261118.csv")

# 사람 판정: 위키낱말사전에 같은 뜻이 있고 표현(어간·활용)만 다른 항목
PHRASING_ONLY = {"show", "big", "fast", "hot", "hard", "simple", "dark", "heavy", "full", "true", "loud",
                 "beautiful", "able", "carefully", "confuse", "land", "pretend", "scream", "transfer",
                 "handsome", "heal"}
# 위키낱말사전에서 해당 뜻을 찾지 못했지만 일반 지식으로 적합한 항목
KNOWLEDGE_OK = {"confidence", "factor", "stress", "faint", "wake", "wish", "young", "warm", "wrong",
                "well", "shrink", "withdraw", "wreck", "peak"}
# 품사 확인 필요였으나 뜻은 적합 (low: 형용사 '낮은'은 맞고, 명사 '저점'도 있음)
POS_NOTE_OK = {"low"}


def decide(english: str, verdict_2nd: str) -> tuple[str, str]:
    if english in POS_NOTE_OK:
        return "적합", "형용사 뜻 적합. 명사 뜻은 별도 항목으로 보완 가능"
    if english in PHRASING_ONLY:
        return "적합 (표현 차이)", "위키낱말사전에 같은 뜻이 있고 활용형만 다름"
    if english in KNOWLEDGE_OK:
        return "적합 (사전 미확인)", "위키낱말사전에 해당 뜻 없음. 일반 지식 기준으로 적합"
    if verdict_2nd == "확인됨":
        return "적합 (사전 일치)", "위키낱말사전 뜻 풀이와 일치"
    return "검토 필요", "자동 판정과 사람 판정이 다름"


def main() -> int:
    with open(SECOND, encoding="utf-8-sig", newline="") as second_file:
        rows = list(csv.reader(second_file))[1:]
    counts: dict[str, int] = {}
    out_rows = []
    for number, english, pos, meaning, verdict_2nd, note in rows:
        verdict, reason = decide(english, verdict_2nd)
        counts[verdict] = counts.get(verdict, 0) + 1
        out_rows.append([number, english, pos, meaning, verdict, reason, verdict_2nd])
    with open(FINAL, "w", encoding="utf-8-sig", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["번호", "영단어", "품사(CSV)", "뜻(CSV)", "최종 판정", "판정 근거", "2차 자동 판정"])
        writer.writerows(out_rows)
    print(counts, sum(counts.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
