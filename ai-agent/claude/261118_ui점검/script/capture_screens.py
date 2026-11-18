#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-18 - smartvoca - 주요 화면을 오프스크린으로 렌더링해 PNG로 저장 (UI 점검용, 실제 data/ 는 건드리지 않음)
# 파일 위치: ai-agent/claude/261118_ui점검/script/capture_screens.py
# 실행: 프로젝트 루트에서 `python ai-agent/claude/261118_ui점검/script/capture_screens.py`

import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
OUT = os.path.join(ROOT, "ai-agent", "claude", "261118_ui점검", "shots")

from PyQt6 import QtGui, QtWidgets  # noqa: E402

from src.models.progress import Progress  # noqa: E402
from src.models.settings import Settings  # noqa: E402
from src.storage.word_csv import load_words  # noqa: E402
from src.ui.main_window import MainWindow  # noqa: E402


def save(widget, name):
    widget.grab().save(os.path.join(OUT, name))


def main():
    app = QtWidgets.QApplication(sys.argv)
    # 오프스크린 환경에 한글 글꼴이 없을 수 있어 Windows 기본 한글 글꼴을 지정한다
    app.setFont(QtGui.QFont("Malgun Gothic", 10))
    words = load_words(os.path.join(ROOT, "data", "voca_2000.csv")).words
    temp = tempfile.mkdtemp()
    window = MainWindow(words, Settings(), Progress(), os.path.join(temp, "p.json"), os.path.join(temp, "h.csv"), os.path.join(temp, "reports"))
    window.resize(800, 560)
    window.show()
    app.processEvents()
    save(window, "01_home.png")

    window._start_memorize()
    app.processEvents()
    save(window, "02_memorize.png")
    window._remove_memorize_view()

    window._stack.setCurrentIndex(1)
    app.processEvents()
    save(window, "03_quiz_setup.png")

    window._on_menu("보고서")
    app.processEvents()
    save(window, "04_report_empty.png")
    window._on_menu("단어장")
    app.processEvents()
    save(window, "05_word_list.png")
    print("saved to", OUT)


if __name__ == "__main__":
    main()
