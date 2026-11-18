#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 학습 이력으로 기간별 보고서 텍스트 생성과 파일 저장 (REQ-011)
# 파일 위치: src/services/report_builder.py

import os
from collections.abc import Iterable
from datetime import date, datetime, timedelta

from src.models.history_record import ACTIVITY_MEMORIZE, ACTIVITY_QUIZ, CORRECT_MARK, HistoryRecord
from src.services.stats import aggregate

PERIOD_7_DAYS = 7
PERIOD_30_DAYS = 30
PERIOD_ALL = None  # 전체 기간

PERIOD_LABELS = {PERIOD_7_DAYS: "최근 7일", PERIOD_30_DAYS: "최근 30일", PERIOD_ALL: "전체"}

TOP_WRONG_COUNT = 10
TOP_WRONG_MIN_ATTEMPTS = 3  # 출제 3회 미만인 단어는 자주 틀린 단어로 보지 않는다

REPORT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
REPORT_FILE_FORMAT = "report_%Y%m%d_%H%M%S"


def filter_period(records: Iterable[HistoryRecord], period_days: int | None, today: date) -> list[HistoryRecord]:
    """기간에 해당하는 이력 행만 고른다. 최근 N일 = 오늘 포함 N일 (프로세스 설계 10.2절)."""
    if period_days is None:
        return [record for record in records if record.timestamp.date() <= today]

    start = today - timedelta(days=period_days - 1)
    return [record for record in records if start <= record.timestamp.date() <= today]


def build_report(
    records: Iterable[HistoryRecord],
    period_days: int | None,
    today: date,
    now: datetime,
    word_keys: set[str] | None = None,
    skipped: int = 0,
) -> str:
    """기간 안의 이력으로 보고서 텍스트를 만든다.

    records: 전체 이력 (이 함수가 기간을 거른다)
    word_keys: 단어장의 소문자 키 집합. 주면 "단어장에 없는 단어" 수를 적는다.
    skipped: 이력 읽기에서 무시한 행 수 (하단에 적는다)
    """
    period_records = filter_period(records, period_days, today)
    quiz_rows = [record for record in period_records if record.activity == ACTIVITY_QUIZ]
    memorize_rows = [record for record in period_records if record.activity == ACTIVITY_MEMORIZE]

    study_days = {record.timestamp.date() for record in period_records}
    memorized_words = {record.english.lower() for record in memorize_rows}
    session_ids = {record.session_id for record in quiz_rows}
    correct_count = sum(1 for record in quiz_rows if record.correct == CORRECT_MARK)

    lines = [
        "스마트 보카 학습 보고서",
        f"기간: {PERIOD_LABELS[period_days]} ({_period_text(period_days, today)})",
        f"생성 시각: {now.strftime(REPORT_TIME_FORMAT)}",
        "",
        f"학습 일수: {len(study_days)}일",
        f"암기 단어 수: {len(memorized_words)}개",
        f"시험 횟수: {len(session_ids)}회",
        f"평균 정답률: {_accuracy_text(correct_count, len(quiz_rows))}",
        "",
        "자주 틀린 단어 Top 10 (출제 3회 이상)",
    ]
    lines.extend(_top_wrong_lines(quiz_rows))

    if word_keys is not None:
        unknown = {record.english.lower() for record in period_records} - word_keys
        lines.extend(["", f"단어장에 없는 단어: {len(unknown)}개"])

    lines.extend(["", f"무시한 이력 행: {skipped}개"])
    return "\n".join(lines) + "\n"


def save_report(text: str, reports_dir: str, now: datetime) -> str:
    """보고서를 새 파일로 저장하고 경로를 돌려준다. 같은 초에 여러 번 만들면 _2, _3을 붙인다 (데이터 설계서 8절).

    기존 파일은 덮어쓰지 않는다 (배타적 생성 모드 'x').
    """
    os.makedirs(reports_dir, exist_ok=True)
    base_name = now.strftime(REPORT_FILE_FORMAT)

    suffix = 1
    while True:
        name = f"{base_name}.txt" if suffix == 1 else f"{base_name}_{suffix}.txt"
        path = os.path.join(reports_dir, name)
        try:
            with open(path, "x", encoding="utf-8") as report_file:
                report_file.write(text)
            return path
        except FileExistsError:
            suffix += 1


def _period_text(period_days: int | None, today: date) -> str:
    if period_days is None:
        return f"처음 ~ {today.isoformat()}"
    start = today - timedelta(days=period_days - 1)
    return f"{start.isoformat()} ~ {today.isoformat()}"


def _accuracy_text(correct_count: int, quiz_count: int) -> str:
    if quiz_count == 0:
        return "해당 없음 (시험 기록 없음)"
    return f"{correct_count / quiz_count * 100:.1f}% (정답 {correct_count} / 시험 {quiz_count})"


def _top_wrong_lines(quiz_rows: list[HistoryRecord]) -> list[str]:
    stats = aggregate(quiz_rows)
    display_names = {record.english.lower(): record.english for record in quiz_rows}

    candidates = [
        (key, stat) for key, stat in stats.items() if stat.attempts >= TOP_WRONG_MIN_ATTEMPTS
    ]
    # 오답률 내림차순, 같으면 오답 수 내림차순, 그래도 같으면 키 순서
    candidates.sort(key=lambda item: (-item[1].wrong_rate, -item[1].wrong, item[0]))

    if not candidates:
        return ["  해당 없음 (출제 3회 이상인 단어가 없습니다)"]

    lines = []
    for rank, (key, stat) in enumerate(candidates[:TOP_WRONG_COUNT], start=1):
        lines.append(
            f"  {rank}. {display_names[key]} - 오답률 {stat.wrong_rate * 100:.1f}% "
            f"(출제 {stat.attempts}회, 오답 {stat.wrong}회)"
        )
    return lines
