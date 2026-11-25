#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-25 - smartvoca - 웹 버전 흐름 테스트: 홈, 암기, 시험, 설정, 단어장, 보고서 (REQ-001~011, 웹 버전)
# 파일 위치: tests/test_web_app.py

import csv
import json
import os
import tempfile
import unittest

from src.storage.json_store import load_progress
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


if __name__ == "__main__":
    unittest.main()
