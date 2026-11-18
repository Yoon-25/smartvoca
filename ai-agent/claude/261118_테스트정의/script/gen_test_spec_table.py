#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - tests/ 의 테스트 메서드를 모아 TC ID 매핑 표를 만든다 (테스트 정의서 초안용)
# 파일 위치: ai-agent/claude/261118_테스트정의/script/gen_test_spec_table.py

import glob
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "ai-agent", "claude", "261118_테스트정의", "tc_table.md")

PATTERN = re.compile(r"def (test_REQ(\d{3})_\w+)\(self")


def collect() -> list[tuple[str, str, str]]:
    rows = []
    for path in sorted(glob.glob(os.path.join(ROOT, "tests", "test_*.py"))):
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as test_file:
            for match in PATTERN.finditer(test_file.read()):
                rows.append((match.group(2), name, match.group(1)))
    rows.sort(key=lambda row: (row[0], row[1], row[2]))
    return rows


def main() -> int:
    rows = collect()
    lines = ["| TC ID | 요구사항 | 테스트 파일 | 테스트 메서드 |", "|---|---|---|---|"]
    for index, (req, file_name, method) in enumerate(rows, start=1):
        lines.append(f"| TC-{index:03d} | REQ-{req} | `{file_name}` | `{method}` |")
    with open(OUT, "w", encoding="utf-8", newline="\n") as out:
        out.write("\n".join(lines) + "\n")
    print("rows", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
