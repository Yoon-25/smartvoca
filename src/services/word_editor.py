#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 단어장 편집 규칙: 입력 검사, 추가·수정·삭제, 일차 구성 변경 판정 (REQ-001, REQ-002, ADR-013)
# 파일 위치: src/services/word_editor.py

from dataclasses import dataclass, replace

from src.models.word import Word
from src.storage.word_csv import ALLOWED_POS, MEANING_SEPARATOR


@dataclass(frozen=True)
class WordInput:
    """편집 화면이 넘기는 입력값. 뜻은 '/'로 나눈 문자열 그대로 받는다."""

    english: str
    pos: str
    meaning_text: str


def parse_meanings(meaning_text: str) -> list[str]:
    """'해/연도' -> ['해', '연도']. 빈 토큰은 버린다 (단어장 CSV 규칙과 같다)."""
    tokens = (token.strip() for token in meaning_text.split(MEANING_SEPARATOR))
    return [token for token in tokens if token]


def validate_word_input(data: WordInput, words: list[Word], editing_key: str | None = None) -> list[str]:
    """입력 오류 문구 목록을 돌려준다. 비어 있으면 저장할 수 있다.

    editing_key: 수정 중인 단어의 키. 자기 자신과의 중복은 허용한다.
    """
    errors: list[str] = []
    english = data.english.strip()
    if not english:
        errors.append("영단어를 입력하세요.")
    if data.pos not in ALLOWED_POS:
        errors.append(f"품사는 {', '.join(ALLOWED_POS)} 중 하나여야 합니다.")
    if not parse_meanings(data.meaning_text):
        errors.append("뜻을 한 개 이상 입력하세요. 여러 뜻은 '/'로 나눕니다.")
    if english:
        key = english.lower()
        if key != editing_key and any(word.key == key for word in words):
            errors.append(f"이미 있는 단어입니다: {english}")
    return errors


def find_word(words: list[Word], key: str) -> Word | None:
    return next((word for word in words if word.key == key), None)


def add_word(words: list[Word], data: WordInput) -> list[Word]:
    """맨 뒤에 추가한다. 호출 전에 validate_word_input을 통과시킨다."""
    return _renumber([*words, _build_word(data, 0)])


def update_word(words: list[Word], key: str, data: WordInput) -> list[Word]:
    """키가 key인 단어를 고쳐 쓴다. 영단어가 바뀌면 키도 바뀐다."""
    updated = [_build_word(data, word.index) if word.key == key else word for word in words]
    return _renumber(updated)


def delete_word(words: list[Word], key: str) -> list[Word]:
    return _renumber([word for word in words if word.key != key])


def day_layout_changed(saved_keys: list[str], draft: list[Word]) -> bool:
    """단어 순서나 개수가 바뀌었는지. 바뀌면 일차 구성이 달라진다 (ADR-011).

    뜻이나 품사만 고친 경우는 키 순서가 그대로이므로 False다.
    """
    return saved_keys != [word.key for word in draft]


def _build_word(data: WordInput, index: int) -> Word:
    english = data.english.strip()
    return Word(
        key=english.lower(),
        english=english,
        pos=data.pos,
        meanings=parse_meanings(data.meaning_text),
        index=index,
    )


def _renumber(words: list[Word]) -> list[Word]:
    """번호(index)를 0부터 다시 매긴다. 원래 객체는 바꾸지 않는다."""
    return [replace(word, index=position) for position, word in enumerate(words)]
