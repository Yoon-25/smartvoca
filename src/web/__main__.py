#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 웹 버전 시작점: 127.0.0.1에서 Flask 서버 실행 (웹 버전, 로컬 전용)
# 파일 위치: src/web/__main__.py
# 실행: 프로젝트 루트에서 `python -m src.web`, 브라우저에서 http://127.0.0.1:5000

import sys

from src.paths import DATA_DIR, HISTORY_FILE, PROGRESS_FILE, REPORTS_DIR, SETTINGS_FILE, WORD_FILE
from src.storage.instance_lock import AlreadyRunningError, InstanceLock
from src.web.app import create_app
from src.web.controller import WebPaths

# 로컬 전용. 외부 네트워크에 열지 않도록 주소를 고정한다 (ADR-012)
HOST = "127.0.0.1"
PORT = 5000


def main() -> int:
    # 데스크톱과 웹은 같은 데이터를 쓰므로 동시에 실행하지 않는다 (이슈 #14, ADR-012)
    lock = InstanceLock(DATA_DIR, "웹 버전")
    try:
        lock.acquire()
    except AlreadyRunningError as error:
        print(f"[중단] {error}")
        return 1
    try:
        return _serve()
    finally:
        lock.release()


def _serve() -> int:
    paths = WebPaths(
        word_file=WORD_FILE,
        settings_file=SETTINGS_FILE,
        progress_file=PROGRESS_FILE,
        history_file=HISTORY_FILE,
        reports_dir=REPORTS_DIR,
    )
    app = create_app(paths)
    controller = app.config["CONTROLLER"]
    print(f"스마트 보카 웹 버전: http://{HOST}:{PORT} (종료: Ctrl+C)")
    try:
        # debug=False: 디버거 콘솔은 로컬이라도 열지 않는다
        app.run(host=HOST, port=PORT, debug=False)
    finally:
        # 종료할 때 저장하지 않은 변경이 있으면 알린다 (이슈 #13)
        message = controller.unsaved_exit_message()
        if message:
            print(f"\n[경고] {message}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
