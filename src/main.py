#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-04 - smartvoca - 프로그램 시작점: 설정·단어장·진도 로드 후 메인 창 표시
# 파일 위치: src/main.py
# 실행: 프로젝트 루트에서 `python -m src.main`

import os
import sys

from PyQt6 import QtWidgets

from src.storage.json_store import load_progress, load_settings
from src.storage.word_csv import WordFileError, load_words
from src.ui.main_window import MainWindow

# 경로 상수는 이 파일에만 둔다 (아키텍처 설계서 6.3절)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
WORD_FILE = os.path.join(DATA_DIR, "voca_2000.csv")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")
HISTORY_FILE = os.path.join(DATA_DIR, "study_history.csv")

SKIP_PREVIEW_COUNT = 5


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)

    settings_result = load_settings(SETTINGS_FILE)
    if settings_result.warnings:
        QtWidgets.QMessageBox.warning(None, "설정 경고", "\n".join(settings_result.warnings))

    words = _load_word_list()
    progress = load_progress(PROGRESS_FILE)

    window = MainWindow(words, settings_result.settings, progress, PROGRESS_FILE, HISTORY_FILE)
    window.show()
    return app.exec()


def _load_word_list() -> list:
    try:
        result = load_words(WORD_FILE)
    except FileNotFoundError:
        QtWidgets.QMessageBox.warning(None, "단어장 오류", f"단어장 파일을 찾을 수 없습니다.\n{WORD_FILE}")
        return []
    except WordFileError as error:
        QtWidgets.QMessageBox.warning(None, "단어장 오류", f"{error}\n기존 단어장을 사용할 수 없어 빈 단어장으로 시작합니다.")
        return []

    if result.skipped:
        preview = "\n".join(f"{skip.line_no}행: {skip.reason}" for skip in result.skipped[:SKIP_PREVIEW_COUNT])
        QtWidgets.QMessageBox.information(
            None,
            "건너뛴 행",
            f"{len(result.skipped)}개 행을 건너뛰었습니다.\n{preview}",
        )
    return result.words


if __name__ == "__main__":
    sys.exit(main())
