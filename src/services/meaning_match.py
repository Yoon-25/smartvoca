#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 뜻 겹침 판정 (ADR-005, REQ-009)
# 파일 위치: src/services/meaning_match.py

from src.models.word import Word


def meaning_tokens(meaning: str) -> set[str]:
    """뜻 문자열을 '/'로 나눈 토큰 집합. 앞뒤 공백은 제거한다."""
    return {token.strip() for token in meaning.split("/") if token.strip()}


def overlaps(a: Word, b: Word) -> bool:
    """두 단어의 뜻 토큰이 하나라도 같으면 True. 같은 단어 비교는 호출하는 쪽이 막는다."""
    return bool(set(a.meanings) & set(b.meanings))
