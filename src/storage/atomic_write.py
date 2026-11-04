#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 임시 파일을 쓴 뒤 원본과 교체하는 공통 저장 함수
# 파일 위치: src/storage/atomic_write.py

import os
import tempfile


def atomic_write_text(path: str, content: str) -> None:
    """content를 UTF-8로 path에 저장한다.

    같은 폴더에 임시 파일을 먼저 쓰고 os.replace로 교체한다.
    쓰기 도중 실패하면 임시 파일을 지우고 원본은 그대로 둔다 (명세서 REQ-002, NFR-002).
    """
    directory = os.path.dirname(os.path.abspath(path))
    file_descriptor, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as temp_file:
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, path)
    except BaseException:
        # 실패 시 임시 파일만 정리한다. 원본 path는 건드리지 않는다.
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise
