#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 웹 버전 흐름 테스트: 홈, 암기, 시험, 설정, 단어장, 보고서 (REQ-001~011, 웹 버전)
# 파일 위치: tests/test_web_app.py

import csv
import io
import json
import os
import tempfile
import unittest

from src.storage.json_store import load_progress
from src.storage.word_csv import load_words
from src.storage.history_csv import read_records
from src.web.app import create_app
from src.web.controller import StudyController, WebPaths

# 한 일차(10개)보다 많은 12개 단어로 만든다. 하루 단어 수는 10으로 설정한다
SAMPLE_WORDS = [
    ("apple", "명사", "사과"), ("book", "명사", "책"), ("cat", "명사", "고양이"),
    ("dog", "명사", "개"), ("eat", "동사", "먹다"), ("fish", "명사", "물고기"),
    ("green", "형용사", "초록색의"), ("house", "명사", "집"), ("ice", "명사", "얼음"),
    ("jump", "동사", "뛰다"), ("king", "명사", "왕"), ("lamp", "명사", "램프"),
]
SAMPLE_SETTINGS = {"words_per_day": 10, "prev_review_ratio": 0.0, "wrong_review_ratio": 0.0,
                   "default_question_count": 5}


def _write_word_file(path: str):
    with open(path, "w", encoding="utf-8", newline="") as word_file:
        writer = csv.writer(word_file)
        writer.writerow(["번호", "영단어", "품사", "뜻"])
        for number, (english, pos, meaning) in enumerate(SAMPLE_WORDS, start=1):
            writer.writerow([number, english, pos, meaning])


class WebTestBase(unittest.TestCase):

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = temp_dir.name
        self.paths = WebPaths(
            word_file=os.path.join(root, "voca.csv"),
            settings_file=os.path.join(root, "settings.json"),
            progress_file=os.path.join(root, "progress.json"),
            history_file=os.path.join(root, "study_history.csv"),
            reports_dir=os.path.join(root, "reports"),
        )
        _write_word_file(self.paths.word_file)
        with open(self.paths.settings_file, "w", encoding="utf-8") as settings_file:
            json.dump(SAMPLE_SETTINGS, settings_file)

        self.controller = StudyController.load(self.paths)
        self.app = create_app(self.paths, controller=self.controller)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()


class HomeAndWordsTest(WebTestBase):

    def test_REQ001_home_shows_today_day_and_range(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn("1일차", text)
        self.assertIn("단어 1 ~ 10", text)

    def test_REQ002_words_page_filters_by_english_or_meaning(self):
        response = self.client.get("/words?q=고양이")
        text = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("cat", text)
        self.assertNotIn(">dog<", text)

    def test_REQ002_words_page_lists_skipped_rows(self):
        with open(self.paths.word_file, "a", encoding="utf-8", newline="") as word_file:
            word_file.write("13,,명사,빈칸\n")
        controller = StudyController.load(self.paths)
        client = create_app(self.paths, controller=controller).test_client()
        text = client.get("/words").get_data(as_text=True)
        self.assertIn("건너뛴 행 (1개)", text)
        self.assertIn("빈 칸", text)


class MemorizeFlowTest(WebTestBase):

    def test_REQ003_memorize_reveal_writes_history_once_per_card(self):
        self.client.post("/memorize/start")
        self.client.post("/memorize/reveal")
        self.client.post("/memorize/reveal")  # 같은 카드는 한 번만 기록
        records = read_records(self.paths.history_file)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].activity, "암기")

    def test_REQ005_completing_last_card_advances_day(self):
        self.client.post("/memorize/start")
        for _ in range(10):
            self.client.post("/memorize/next")
        progress = load_progress(self.paths.progress_file)
        self.assertEqual(progress.current_day, 2)
        self.assertIsNotNone(progress.last_study_date)
        self.assertIsNone(self.controller.memorize_session)

    def test_REQ003_next_on_last_card_does_not_complete_before_reaching_it(self):
        self.client.post("/memorize/start")
        self.client.post("/memorize/next")
        self.assertEqual(load_progress(self.paths.progress_file).current_day, 1)
        self.assertIsNotNone(self.controller.memorize_session)

    def test_REQ003_abandon_keeps_progress(self):
        self.client.post("/memorize/start")
        self.client.post("/memorize/reveal")
        self.client.post("/memorize/abandon")
        self.assertIsNone(self.controller.memorize_session)
        self.assertEqual(load_progress(self.paths.progress_file).current_day, 1)


class QuizFlowTest(WebTestBase):

    def _start_short_quiz(self, count: int = 2):
        return self.client.post("/quiz/start", data={
            "count": str(count), "direction": "한→영", "types": ["단답형"],
        })

    def test_REQ004_quiz_correct_answer_is_graded_and_recorded(self):
        self._start_short_quiz(2)
        question = self.controller.quiz_session.current
        self.client.post("/quiz/submit", data={"answer": question.accepted[0]})
        page = self.client.get("/quiz").get_data(as_text=True)
        self.assertIn("정답입니다.", page)

        self.client.post("/quiz/next")
        self.client.post("/quiz/submit", data={"answer": "wrong-answer-zzz"})
        self.client.post("/quiz/next")

        result_page = self.client.get("/quiz").get_data(as_text=True)
        self.assertIn("시험 결과", result_page)
        self.assertIn("1 / 2 정답", result_page)
        records = read_records(self.paths.history_file)
        quiz_rows = [record for record in records if record.activity == "시험"]
        self.assertEqual(len(quiz_rows), 2)
        self.assertEqual(sorted(record.correct for record in quiz_rows), ["O", "X"])

    def test_REQ004_quiz_setup_rejects_invalid_count(self):
        response = self.client.post("/quiz/start", data={
            "count": "0", "direction": "한→영", "types": ["단답형"],
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("/quiz/setup", response.headers["Location"])
        self.assertIsNone(self.controller.quiz_session)

    def test_REQ008_quiz_setup_rejects_missing_question_type(self):
        with self.assertRaises(ValueError):
            self.controller.start_quiz(2, "한→영", [])

    def test_REQ004_multiple_choice_requires_selection(self):
        self.controller.start_quiz(1, "영→한", ["4지선다"])
        response = self.client.post("/quiz/submit", data={})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.controller.quiz_session.is_submitted)
        self.assertEqual(self.controller.quiz_session.position, 0)


class RenderTest(WebTestBase):

    def test_REQ004_choice_and_ox_questions_render_their_inputs(self):
        self.controller.start_quiz(1, "영→한", ["4지선다"])
        page = self.client.get("/quiz").get_data(as_text=True)
        self.assertIn('name="choice" value="0"', page)

        self.controller.quiz_abandon()
        self.controller.start_quiz(1, "영→한", ["OX"])
        page = self.client.get("/quiz").get_data(as_text=True)
        self.assertIn('name="answer" value="O"', page)
        self.assertIn('name="answer" value="X"', page)

    def test_REQ003_memorize_card_shows_meaning_only_after_reveal(self):
        self.client.post("/memorize/start")
        self.assertNotIn("사과", self.client.get("/memorize").get_data(as_text=True))  # 첫 카드 apple·사과
        self.client.post("/memorize/reveal")
        self.assertIn("사과", self.client.get("/memorize").get_data(as_text=True))

    def test_REQ001_user_text_is_escaped_in_pages(self):
        self.controller.words[0].english = "<script>x</script>"
        page = self.client.get("/words").get_data(as_text=True)
        self.assertNotIn("<script>x</script>", page)
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", page)


class SettingsTest(WebTestBase):

    def _form(self, **overrides):
        data = {"words_per_day": "10", "prev_review_percent": "20", "wrong_review_percent": "10",
                "default_question_count": "5"}
        data.update(overrides)
        return data

    def test_REQ005_changing_words_per_day_requires_confirmation(self):
        self.client.post("/settings", data=self._form(words_per_day="15"))
        with open(self.paths.settings_file, encoding="utf-8") as settings_file:
            self.assertEqual(json.load(settings_file)["words_per_day"], 10)

        self.client.post("/settings", data=self._form(words_per_day="15", confirm_change="1"))
        with open(self.paths.settings_file, encoding="utf-8") as settings_file:
            self.assertEqual(json.load(settings_file)["words_per_day"], 15)

    def test_REQ006_out_of_range_ratio_is_rejected(self):
        self.client.post("/settings", data=self._form(prev_review_percent="60"))
        self.assertEqual(self.controller.settings.prev_review_ratio, 0.0)

    def test_REQ006_ratio_is_saved_as_fraction(self):
        self.client.post("/settings", data=self._form(prev_review_percent="25"))
        self.assertAlmostEqual(self.controller.settings.prev_review_ratio, 0.25)

    def test_ADR011_settings_cannot_change_while_in_progress(self):
        self.controller.start_memorize()
        self.controller.memorize_reveal()
        self.client.post("/settings", data=self._form(default_question_count="3"))
        self.assertEqual(self.controller.settings.default_question_count, 5)


class ReportTest(WebTestBase):

    def test_REQ011_report_without_history_creates_no_file(self):
        text = self.client.post("/report", data={"period": "all"}).get_data(as_text=True)
        self.assertIn("이력이 없습니다", text)
        self.assertFalse(os.path.exists(self.paths.reports_dir))

    def test_REQ011_report_is_saved_after_study(self):
        self.client.post("/memorize/start")
        self.client.post("/memorize/reveal")
        text = self.client.post("/report", data={"period": "7"}).get_data(as_text=True)
        self.assertIn("저장 위치", text)
        self.assertIn("학습 일수: 1일", text)
        self.assertEqual(len(os.listdir(self.paths.reports_dir)), 1)


class WordEditTest(WebTestBase):
    """단어장 편집 (ADR-013): 초안 편집, 저장 확인, 백업, 취소, 불러오기, 진행 중 차단."""

    def _file_word_count(self) -> int:
        return len(load_words(self.paths.word_file).words)

    def test_REQ001_add_changes_draft_only_until_saved(self):
        self.client.post("/words/new", data={"english": "zebra", "pos": "명사", "meanings": "얼룩말"})
        self.assertEqual(len(self.controller.words), 13)
        self.assertTrue(self.controller.word_dirty)
        self.assertEqual(self._file_word_count(), 12)

    def test_REQ001_add_duplicate_shows_error_and_keeps_draft(self):
        response = self.client.post("/words/new", data={"english": "APPLE", "pos": "명사", "meanings": "사과"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("이미 있는 단어", response.get_data(as_text=True))
        self.assertEqual(len(self.controller.words), 12)

    def test_REQ001_meaning_only_edit_saves_without_confirmation(self):
        self.client.post("/words/apple/edit", data={"english": "apple", "pos": "명사", "meanings": "사과 / 열매"})
        self.client.post("/words/save", data={})
        self.assertFalse(self.controller.word_dirty)
        self.assertEqual(load_words(self.paths.word_file).words[0].meanings, ["사과", "열매"])

    def test_ADR013_layout_change_needs_confirmation_before_save(self):
        self.client.post("/words/new", data={"english": "zebra", "pos": "명사", "meanings": "얼룩말"})
        self.client.post("/words/save", data={})
        self.assertEqual(self._file_word_count(), 12)
        self.assertTrue(self.controller.word_dirty)

        self.client.post("/words/save", data={"confirm_change": "1"})
        self.assertEqual(self._file_word_count(), 13)
        self.assertFalse(self.controller.word_dirty)

    def test_ADR013_save_keeps_previous_file_as_backup(self):
        self.client.post("/words/apple/delete", data={})
        self.client.post("/words/save", data={"confirm_change": "1"})
        self.assertTrue(os.path.exists(self.paths.word_file + ".bak"))
        self.assertEqual(len(load_words(self.paths.word_file + ".bak").words), 12)

    def test_ADR013_discard_restores_file_contents(self):
        self.client.post("/words/book/delete", data={})
        self.client.post("/words/discard", data={"confirm_discard": "1"})
        self.assertEqual(len(self.controller.words), 12)
        self.assertFalse(self.controller.word_dirty)

    def test_ADR013_import_loads_draft_without_touching_file(self):
        csv_bytes = "번호,영단어,품사,뜻\n1,ant,명사,개미\n2,bee,명사,벌\n".encode("utf-8")
        response = self.client.post(
            "/words/import",
            data={"file": (io.BytesIO(csv_bytes), "new.csv")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual([word.english for word in self.controller.words], ["ant", "bee"])
        self.assertTrue(self.controller.word_dirty)
        self.assertEqual(self._file_word_count(), 12)

    def test_ADR013_skipped_rows_warn_before_save(self):
        with open(self.paths.word_file, "a", encoding="utf-8", newline="") as word_file:
            word_file.write("13,,명사,빈칸\n")
        self.controller = StudyController.load(self.paths)
        self.app = create_app(self.paths, controller=self.controller)
        client = self.app.test_client()

        client.post("/words/apple/delete", data={})
        client.post("/words/save", data={})
        self.assertEqual(self._file_word_count(), 12)
        client.post("/words/save", data={"confirm_change": "1"})
        self.assertEqual(self._file_word_count(), 11)

    def test_ADR013_editing_is_blocked_while_learning(self):
        self.controller.start_memorize()
        self.controller.memorize_reveal()
        self.client.post("/words/new", data={"english": "zebra", "pos": "명사", "meanings": "얼룩말"})
        self.assertEqual(len(self.controller.words), 12)
        self.assertFalse(self.controller.word_dirty)

    def test_REQ001_dirty_banner_appears_on_other_pages(self):
        self.client.post("/words/new", data={"english": "zebra", "pos": "명사", "meanings": "얼룩말"})
        self.assertIn("저장하지 않은 단어 변경이 있습니다", self.client.get("/").get_data(as_text=True))


class DraftProtectionTest(WebTestBase):
    """저장하지 않은 웹 초안 보호 (이슈 #13, ADR-013): 자동 보관, 복원, 저장·취소 시 정리, 종료 경고."""

    def _draft_path(self) -> str:
        return self.paths.word_file + ".draft"

    def _restart(self) -> "StudyController":
        return StudyController.load(self.paths)

    def test_ADR013_edit_autosaves_draft_file(self):
        self.client.post("/words/new", data={"english": "zebra", "pos": "명사", "meanings": "얼룩말"})
        self.assertTrue(os.path.exists(self._draft_path()))
        self.assertEqual(len(load_words(self._draft_path()).words), 13)
        self.assertEqual(len(load_words(self.paths.word_file).words), 12)

    def test_ADR013_restart_restores_unsaved_draft(self):
        self.client.post("/words/new", data={"english": "zebra", "pos": "명사", "meanings": "얼룩말"})
        restarted = self._restart()
        self.assertEqual(len(restarted.words), 13)
        self.assertTrue(restarted.word_dirty)
        self.assertTrue(restarted.draft_restored)
        self.assertEqual(len(load_words(self.paths.word_file).words), 12)

    def test_ADR013_restored_draft_keeps_layout_change_check(self):
        self.client.post("/words/new", data={"english": "zebra", "pos": "명사", "meanings": "얼룩말"})
        restarted = self._restart()
        self.assertTrue(any("일차 구성" in warning for warning in restarted.word_save_warnings()))

    def test_ADR013_save_removes_draft_file(self):
        self.client.post("/words/new", data={"english": "zebra", "pos": "명사", "meanings": "얼룩말"})
        self.client.post("/words/save", data={"confirm_change": "1"})
        self.assertFalse(os.path.exists(self._draft_path()))
        self.assertFalse(self._restart().word_dirty)

    def test_ADR013_discard_removes_draft_file(self):
        self.client.post("/words/new", data={"english": "zebra", "pos": "명사", "meanings": "얼룩말"})
        self.client.post("/words/discard", data={"confirm_discard": "1"})
        self.assertFalse(os.path.exists(self._draft_path()))
        self.assertEqual(len(self.controller.words), 12)

    def test_ADR013_restored_notice_is_shown(self):
        self.client.post("/words/new", data={"english": "zebra", "pos": "명사", "meanings": "얼룩말"})
        client = create_app(self.paths, controller=self._restart()).test_client()
        self.assertIn("복원했습니다", client.get("/words").get_data(as_text=True))

    def test_ADR013_exit_message_only_when_unsaved(self):
        self.assertIsNone(self.controller.unsaved_exit_message())
        self.client.post("/words/new", data={"english": "zebra", "pos": "명사", "meanings": "얼룩말"})
        self.assertIn("초안", self.controller.unsaved_exit_message())

    def test_ADR013_corrupt_draft_is_ignored_with_message(self):
        with open(self._draft_path(), "w", encoding="utf-8") as draft_file:
            draft_file.write("틀린,헤더\n1,a,명사,뜻\n")
        restarted = self._restart()
        self.assertFalse(restarted.word_dirty)
        self.assertEqual(len(restarted.words), 12)
        self.assertIn("무시", restarted.load_error)


if __name__ == "__main__":
    unittest.main()
