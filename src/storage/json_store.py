#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 설정(settings.json)과 진도(progress.json) 읽기·쓰기 (REQ-005, REQ-006)
# 파일 위치: src/storage/json_store.py

import json
import os
from dataclasses import dataclass, field
from datetime import date

from src.models.progress import Progress
from src.models.settings import Settings
from src.storage.atomic_write import atomic_write_text

# 데이터 설계서 6.1절 허용 범위
WORDS_PER_DAY_RANGE = (10, 100)
RATIO_RANGE = (0.0, 0.5)
QUESTION_COUNT_MIN = 1


@dataclass
class SettingsLoadResult:
    settings: Settings
    warnings: list[str] = field(default_factory=list)


def load_settings(path: str) -> SettingsLoadResult:
    """설정 파일을 읽는다. 없거나 깨졌으면 기본값을 쓴다.

    범위를 벗어나거나 타입이 다른 키만 기본값으로 바꾸고 경고 목록에 담는다.
    깨진 JSON 파일은 *.bak으로 이름을 바꾸고 보존한다 (아키텍처 설계서 8절).
    """
    defaults = Settings()
    data = _read_json_object(path)
    if data is None:
        return SettingsLoadResult(defaults)

    warnings: list[str] = []
    settings = Settings(
        words_per_day=_int_in_range(data, "words_per_day", WORDS_PER_DAY_RANGE, defaults.words_per_day, warnings),
        prev_review_ratio=_ratio(data, "prev_review_ratio", defaults.prev_review_ratio, warnings),
        wrong_review_ratio=_ratio(data, "wrong_review_ratio", defaults.wrong_review_ratio, warnings),
        default_question_count=_int_in_range(
            data,
            "default_question_count",
            (QUESTION_COUNT_MIN, float("inf")),
            defaults.default_question_count,
            warnings,
        ),
    )
    return SettingsLoadResult(settings, warnings)


def save_settings(path: str, settings: Settings) -> None:
    data = {
        "words_per_day": settings.words_per_day,
        "prev_review_ratio": round(settings.prev_review_ratio, 2),
        "wrong_review_ratio": round(settings.wrong_review_ratio, 2),
        "default_question_count": settings.default_question_count,
    }
    atomic_write_text(path, _dump(data))


def load_progress(path: str) -> Progress:
    """진도 파일을 읽는다. 없거나 깨졌으면 current_day=1로 시작한다."""
    data = _read_json_object(path)
    if data is None:
        return Progress()

    current_day = data.get("current_day", 1)
    if not _is_int(current_day) or current_day < 1:
        current_day = 1

    return Progress(current_day=current_day, last_study_date=_parse_date(data.get("last_study_date")))


def save_progress(path: str, progress: Progress) -> None:
    data = {
        "current_day": progress.current_day,
        "last_study_date": progress.last_study_date.isoformat() if progress.last_study_date else None,
    }
    atomic_write_text(path, _dump(data))


def _read_json_object(path: str) -> dict | None:
    """JSON 객체를 읽는다. 파일이 없으면 None. 깨졌으면 *.bak으로 옮기고 None."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as json_file:
            data = json.load(json_file)
    except ValueError:
        # JSONDecodeError 포함. 손상 파일은 지우지 않고 보존한다
        os.replace(path, path + ".bak")
        return None
    return data if isinstance(data, dict) else None


def _int_in_range(data: dict, key: str, bounds: tuple, default: int, warnings: list[str]) -> int:
    if key not in data:
        return default
    value = data[key]
    low, high = bounds
    if not _is_int(value) or not low <= value <= high:
        warnings.append(f"{key}: 허용 범위를 벗어나 기본값 {default}을 사용합니다.")
        return default
    return value


def _ratio(data: dict, key: str, default: float, warnings: list[str]) -> float:
    if key not in data:
        return default
    value = data[key]
    low, high = RATIO_RANGE
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        warnings.append(f"{key}: 허용 범위를 벗어나 기본값 {default}을 사용합니다.")
        return default
    return round(float(value), 2)


def _parse_date(value) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _is_int(value) -> bool:
    # bool은 int의 하위 타입이므로 따로 막는다
    return isinstance(value, int) and not isinstance(value, bool)


def _dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"
