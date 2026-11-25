#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 동시 실행 방지 잠금 테스트: 살아 있는 주인, 죽은 주인, 손상된 잠금, 해제 (이슈 #14, ADR-012)
# 파일 위치: tests/test_instance_lock.py

import json
import os
import subprocess
import sys
import tempfile
import unittest

from src.storage.instance_lock import (
    LOCK_FILE_NAME,
    AlreadyRunningError,
    InstanceLock,
    is_process_alive,
    read_owner,
)


def _sleeping_process() -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])


def _exited_pid() -> int:
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()
    return process.pid


class InstanceLockTest(unittest.TestCase):

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.dir = temp_dir.name
        self.lock_path = os.path.join(self.dir, LOCK_FILE_NAME)

    def _write_lock(self, app: str, pid: int) -> None:
        with open(self.lock_path, "w", encoding="utf-8") as lock_file:
            json.dump({"app": app, "pid": pid}, lock_file)

    def test_ISSUE14_first_instance_creates_lock_and_release_removes_it(self):
        lock = InstanceLock(self.dir, "데스크톱 버전")
        lock.acquire()
        self.assertEqual(read_owner(self.lock_path).pid, os.getpid())
        lock.release()
        self.assertFalse(os.path.exists(self.lock_path))

    def test_ISSUE14_second_instance_is_refused_while_first_is_alive(self):
        child = _sleeping_process()
        self.addCleanup(child.kill)
        self._write_lock("데스크톱 버전", child.pid)

        with self.assertRaises(AlreadyRunningError) as raised:
            InstanceLock(self.dir, "웹 버전").acquire()
        self.assertIn("이미 실행 중", str(raised.exception))
        self.assertEqual(raised.exception.owner.app, "데스크톱 버전")

    def test_ISSUE14_stale_lock_from_dead_process_is_cleaned_up(self):
        self._write_lock("웹 버전", _exited_pid())
        lock = InstanceLock(self.dir, "데스크톱 버전")
        lock.acquire()
        self.assertEqual(read_owner(self.lock_path).app, "데스크톱 버전")
        lock.release()

    def test_ISSUE14_unreadable_lock_is_not_removed_automatically(self):
        with open(self.lock_path, "w", encoding="utf-8") as lock_file:
            lock_file.write("")
        with self.assertRaises(AlreadyRunningError):
            InstanceLock(self.dir, "웹 버전").acquire()
        self.assertTrue(os.path.exists(self.lock_path))

    def test_ISSUE14_release_does_not_remove_someone_elses_lock(self):
        lock = InstanceLock(self.dir, "데스크톱 버전")
        lock.acquire()
        self._write_lock("웹 버전", os.getpid() + 999999)
        lock.release()
        self.assertEqual(read_owner(self.lock_path).app, "웹 버전")

    def test_ISSUE14_is_process_alive_detects_running_and_finished_processes(self):
        self.assertTrue(is_process_alive(os.getpid()))
        self.assertFalse(is_process_alive(_exited_pid()))


if __name__ == "__main__":
    unittest.main()
