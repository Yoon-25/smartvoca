#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 데스크톱 실행 점검 (이슈 #14 확인): 임시 데이터 폴더로 창 기동과 잠금 거부를 확인
# 파일 위치: ai-agent/claude/251125_데스크톱점검/script/desktop_smoke.py

import json
import os
import shutil
import subprocess
import sys
import tempfile

os.environ["QT_QPA_PLATFORM"] = "offscreen"
PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT)

from PyQt6 import QtCore, QtWidgets  # noqa: E402

import src.main as desktop  # noqa: E402
from src.storage.instance_lock import LOCK_FILE_NAME  # noqa: E402


def use_temp_data(temp_dir: str) -> None:
    """실제 data/ 대신 임시 폴더를 쓰도록 경로 상수를 바꾼다. 원본은 복사만 한다."""
    for name in ("voca_2000.csv",):
        shutil.copy(os.path.join(PROJECT, "data", name), temp_dir)
    desktop.DATA_DIR = temp_dir
    desktop.WORD_FILE = os.path.join(temp_dir, "voca_2000.csv")
    desktop.SETTINGS_FILE = os.path.join(temp_dir, "settings.json")
    desktop.PROGRESS_FILE = os.path.join(temp_dir, "progress.json")
    desktop.HISTORY_FILE = os.path.join(temp_dir, "study_history.csv")
    desktop.REPORTS_DIR = os.path.join(temp_dir, "reports")


def run_case_window_opens() -> None:
    """잠금이 없을 때 창이 뜨고 정상 종료되는지 확인한다."""
    temp_dir = tempfile.mkdtemp()
    use_temp_data(temp_dir)
    shown = {"window": False}
    original_show = desktop.MainWindow.show

    def show_and_quit(self):
        original_show(self)
        shown["window"] = True
        QtCore.QTimer.singleShot(1000, QtWidgets.QApplication.instance().quit)

    desktop.MainWindow.show = show_and_quit
    with_silenced_dialogs(lambda: desktop.main())
    desktop.MainWindow.show = original_show
    print("[창 기동] 창 표시:", "성공" if shown["window"] else "실패")
    print("[창 기동] 종료 후 잠금 파일 남음:", os.path.exists(os.path.join(temp_dir, LOCK_FILE_NAME)))


def run_case_refused_when_running() -> None:
    """다른 실행이 잠금을 쥐고 있을 때 거부되는지 확인한다."""
    temp_dir = tempfile.mkdtemp()
    use_temp_data(temp_dir)
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        with open(os.path.join(temp_dir, LOCK_FILE_NAME), "w", encoding="utf-8") as lock_file:
            json.dump({"app": "웹 버전", "pid": child.pid}, lock_file)
        messages = []
        code = with_silenced_dialogs(lambda: desktop.main(), warnings=messages)
        print("[잠금 거부] 반환 코드:", code, "(기대값 1)")
        print("[잠금 거부] 안내 창 문구:", messages[0][:40] if messages else "없음")
    finally:
        child.kill()


def with_silenced_dialogs(action, warnings=None):
    """안내 창이 실행을 막지 않도록 막고, 경고 문구는 기록한다."""
    recorded = warnings if warnings is not None else []

    def fake_warning(_parent, _title, message, *_args, **_kwargs):
        recorded.append(message)
        return QtWidgets.QMessageBox.StandardButton.Ok

    original = (QtWidgets.QMessageBox.warning, QtWidgets.QMessageBox.information, QtWidgets.QMessageBox.question)
    QtWidgets.QMessageBox.warning = staticmethod(fake_warning)
    QtWidgets.QMessageBox.information = staticmethod(lambda *a, **k: QtWidgets.QMessageBox.StandardButton.Ok)
    QtWidgets.QMessageBox.question = staticmethod(lambda *a, **k: QtWidgets.QMessageBox.StandardButton.No)
    try:
        return action()
    finally:
        QtWidgets.QMessageBox.warning, QtWidgets.QMessageBox.information, QtWidgets.QMessageBox.question = original


if __name__ == "__main__":
    run_case_window_opens()
    run_case_refused_when_running()
