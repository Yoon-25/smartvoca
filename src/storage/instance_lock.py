#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 데스크톱·웹 동시 실행 방지: 데이터 폴더의 잠금 파일 (이슈 #14, ADR-012)
# 파일 위치: src/storage/instance_lock.py

import ctypes
import json
import os
import sys
from dataclasses import dataclass

LOCK_FILE_NAME = ".smartvoca.lock"

# Windows 프로세스 확인용 상수 (OpenProcess, GetExitCodeProcess)
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_STILL_ACTIVE = 259
_ERROR_ACCESS_DENIED = 5


@dataclass(frozen=True)
class LockOwner:
    app: str
    pid: int


class AlreadyRunningError(Exception):
    """다른 버전이 같은 데이터 폴더를 쓰고 있을 때 발생한다."""

    def __init__(self, message: str, owner: LockOwner | None = None):
        super().__init__(message)
        self.owner = owner


def is_process_alive(pid: int) -> bool:
    """pid가 살아 있는지 본다. 종료시키지 않는다.

    Windows의 os.kill(pid, 0)은 프로세스를 끝내 버릴 수 있으므로 쓰지 않는다.
    """
    if sys.platform == "win32":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            # 권한이 없어 열지 못한 것은 살아 있는 프로세스로 본다 (안전한 쪽)
            return ctypes.get_last_error() == _ERROR_ACCESS_DENIED
        try:
            exit_code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return True
            return exit_code.value == _STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_owner(lock_path: str) -> LockOwner | None:
    """잠금 파일의 주인을 읽는다. 읽을 수 없으면 None."""
    try:
        with open(lock_path, encoding="utf-8") as lock_file:
            data = json.load(lock_file)
        return LockOwner(app=str(data["app"]), pid=int(data["pid"]))
    except (OSError, ValueError, KeyError, TypeError):
        return None


class InstanceLock:
    """데이터 폴더당 하나의 실행만 허용한다.

    잠금 파일이 있고 주인 프로세스가 살아 있으면 AlreadyRunningError를 낸다.
    주인이 죽은 잠금(비정상 종료)은 자동으로 치운다.
    내용을 읽을 수 없는 잠금은 다른 실행이 막 시작 중일 수 있으므로 치우지 않고 막는다.
    """

    def __init__(self, data_dir: str, app_name: str):
        self._path = os.path.join(data_dir, LOCK_FILE_NAME)
        self._app = app_name
        self._held = False

    @property
    def path(self) -> str:
        return self._path

    def acquire(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        for _attempt in range(2):
            try:
                fd = os.open(self._path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                owner = read_owner(self._path)
                if owner is None:
                    raise AlreadyRunningError(self._unreadable_message())
                if owner.pid == os.getpid():
                    # 같은 프로세스가 남긴 잠금: 이어서 쓴다
                    self._held = True
                    return
                if is_process_alive(owner.pid):
                    raise AlreadyRunningError(self._busy_message(owner), owner)
                # 주인이 이미 종료됨 (비정상 종료 등): 잠금을 치우고 다시 만든다
                self._remove_quietly()
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as lock_file:
                json.dump({"app": self._app, "pid": os.getpid()}, lock_file, ensure_ascii=False)
            self._held = True
            return
        raise AlreadyRunningError(self._unreadable_message())

    def release(self) -> None:
        """내가 만든 잠금만 지운다."""
        if not self._held:
            return
        owner = read_owner(self._path)
        if owner is not None and owner.pid == os.getpid():
            self._remove_quietly()
        self._held = False

    def _remove_quietly(self) -> None:
        try:
            os.remove(self._path)
        except FileNotFoundError:
            pass

    def _busy_message(self, owner: LockOwner) -> str:
        return (
            f"스마트 보카가 이미 실행 중입니다 ({owner.app}, PID {owner.pid}).\n"
            "데스크톱과 웹 버전은 같은 데이터를 쓰므로 동시에 실행할 수 없습니다.\n"
            "실행 중인 창을 먼저 닫아 주세요."
        )

    def _unreadable_message(self) -> str:
        return (
            "다른 실행이 시작 중이거나 잠금 파일이 손상되었습니다.\n"
            "실행 중인 창을 닫은 뒤 다시 시도하세요.\n"
            f"문제가 계속되면 다음 파일을 지우세요: {self._path}"
        )
