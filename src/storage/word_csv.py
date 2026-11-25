#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 단어장 CSV 읽기·쓰기 (REQ-001, REQ-002)
# 파일 위치: src/storage/word_csv.py

import csv
import io
import os
import shutil
from dataclasses import dataclass, field

from src.models.word import Word
from src.storage.atomic_write import atomic_write_text

# 데이터 설계서 2.1, 2.3 기준
HEADER = ["번호", "영단어", "품사", "뜻"]
ALLOWED_POS = ("명사", "동사", "형용사", "부사")
MEANING_SEPARATOR = "/"


class WordFileError(Exception):
    """단어 파일 형식이 맞지 않아 로드를 중단할 때 발생한다 (예: 헤더 불일치)."""


@dataclass
class SkipInfo:
    """건너뛴 행 정보. line_no는 파일의 줄 번호(헤더 = 1)."""

    line_no: int
    reason: str


@dataclass
class LoadResult:
    words: list[Word] = field(default_factory=list)
    skipped: list[SkipInfo] = field(default_factory=list)


def load_words(path: str) -> LoadResult:
    """단어장 CSV를 읽어 단어 목록과 건너뛴 행 목록을 돌려준다.

    헤더가 정확히 HEADER와 같지 않으면 WordFileError를 발생시킨다.
    행 단위 오류(열 개수, 빈 칸, 품사, 중복)는 건너뛰고 skipped에 모은다.
    BOM이 붙은 파일도 읽는다. 완전히 빈 줄은 무시한다.
    """
    result = LoadResult()
    seen_keys: set[str] = set()

    # utf-8-sig: 엑셀이 붙이는 BOM이 있어도 헤더를 정확히 비교하기 위함
    with open(path, encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.reader(csv_file)

        header = next(reader, [])
        if [cell.strip() for cell in header] != HEADER:
            raise WordFileError(f"헤더가 맞지 않습니다: {','.join(header)}")

        for row in reader:
            line_no = reader.line_num
            if not any(cell.strip() for cell in row):
                continue

            if len(row) != 4:
                result.skipped.append(SkipInfo(line_no, "열 개수 오류"))
                continue

            _, english, pos, meaning_text = (cell.strip() for cell in row)
            if not english or not meaning_text:
                result.skipped.append(SkipInfo(line_no, "빈 칸"))
                continue

            if pos not in ALLOWED_POS:
                result.skipped.append(SkipInfo(line_no, f"품사 오류: {pos}"))
                continue

            key = english.lower()
            if key in seen_keys:
                result.skipped.append(SkipInfo(line_no, f"중복: {english}"))
                continue

            meanings = [token.strip() for token in meaning_text.split(MEANING_SEPARATOR)]
            meanings = [token for token in meanings if token]
            if not meanings:
                result.skipped.append(SkipInfo(line_no, "빈 칸"))
                continue

            seen_keys.add(key)
            result.words.append(
                Word(key=key, english=english, pos=pos, meanings=meanings, index=len(result.words))
            )

    return result


def save_words(path: str, words: list[Word]) -> None:
    """단어 목록을 REQ-001과 같은 형식의 CSV로 저장한다.

    번호는 1부터 다시 매긴다. 저장은 임시 파일을 거쳐 원본을 교체하므로
    쓰기가 실패해도 기존 파일이 남는다 (REQ-002).
    """
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(HEADER)
    for number, word in enumerate(words, start=1):
        meaning_text = MEANING_SEPARATOR.join(word.meanings)
        writer.writerow([number, word.english, word.pos, meaning_text])

    atomic_write_text(path, buffer.getvalue())


BACKUP_SUFFIX = ".bak"


def save_words_with_backup(path: str, words: list[Word]) -> str | None:
    """기존 파일을 '<원본>.bak'으로 복사해 둔 뒤 저장한다 (ADR-013).

    기존 파일이 없으면 백업은 만들지 않고 None을 돌려준다. 있으면 백업 경로를 돌려준다.
    """
    backup_path = None
    if os.path.exists(path):
        backup_path = path + BACKUP_SUFFIX
        shutil.copy2(path, backup_path)
    save_words(path, words)
    return backup_path
