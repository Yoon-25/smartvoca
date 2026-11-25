# 스마트 보카 테스트 정의서

**파일 위치**: `docs/VocaFlashcard_Test_Specification_v1.3_261125.md`
**작성일**: 2026-11-18
**버전**: v1.3 (승인, 2026-11-25, 저장하지 않은 웹 초안 보호와 실행 잠금 TC-161~176 추가, 실행 176개)
**설명**: 요구사항(REQ-001~011)과 자동 테스트(unittest)·수동 점검 항목을 연결하고, 테스트 ID(TC)를 확정한다.
**기준 문서**: `VocaFlashcard_Requirement_Spec_v1.2_261125.md` (8절 추적 매트릭스), `VocaFlashcard_Architecture_Design_v1.5_261125.md`, `VocaFlashcard_Process_Logic_v1.2_261125.md`

---

## 1. 목적과 범위

- 구현된 기능이 명세서의 수용 기준을 만족하는지 자동 테스트와 수동 점검으로 확인한다.
- 명세서 8절은 테스트 ID를 "예정"으로 두었다. 이 문서에서 실제 테스트 메서드에 TC ID를 부여하고 확정한다.
- 웹 버전(ADR-012)의 흐름 테스트 20개(TC-113~132)를 포함한다. 웹 화면은 같은 요구사항(REQ-001~011)을 HTTP 요청 수준에서 확인한다.

## 2. 테스트 환경

| 항목 | 값 |
|------|----|
| Python | 3.11.9 |
| PyQt6 / Qt | 6.12.0 / 6.12.0 |
| 테스트 프레임워크 | `unittest` (ADR-007) |
| 화면 테스트 | `QT_QPA_PLATFORM=offscreen`으로 화면 없이 실행 (`tests/test_ui_smoke.py`, `test_report_flow.py`, `test_word_list_flow.py`, `test_settings_dialog.py`, `test_shortcuts.py`) |

실행 명령 (프로젝트 루트):

```
python -m unittest discover -s tests -t .
```

한 파일만 실행: `python -m unittest tests.test_quiz`

## 3. 테스트 수준

| 수준 | 대상 | 파일 |
|------|------|------|
| 단위 | 저장소(`storage/`), 서비스(`services/`), 모델 | `test_storage`, `test_history_csv`, `test_json_store`, `test_day_planner`, `test_memorize_session`, `test_quiz`, `test_report_builder` |
| 단어장 편집 규칙, 백업 저장 (ADR-013) | `services/word_editor.py`, `storage/word_csv.py` | `test_word_editor` |
| 실행 잠금, 시작 모듈 (ADR-012, 이슈 #14) | `storage/instance_lock.py`, `src/main.py`, `src/web/__main__.py` | `test_instance_lock`, `test_entrypoints` |
| 웹 흐름 (Flask test client) | 라우트, 암기·시험 흐름, 설정 검사, 보고서 저장, HTML 렌더링·이스케이프 | `test_web_app` |
| 화면 흐름 (offscreen) | 메인 창, 암기·시험·보고서·단어장·설정 화면과 상태 전환 | `test_ui_smoke`, `test_report_flow`, `test_word_list_flow`, `test_settings_dialog`, `test_shortcuts`, `test_word_editing_flow` |
| 수동 점검 | 실제 화면 배치, 글자 크기, 한글 표시 | M-01 (아래 8절) |

## 4. 요구사항별 TC 요약

| 요구사항 | 명세서 예정 범위 (8절) | 테스트 수 | 확정 TC 범위 | 비고 |
|---|---|---|---|---|
| REQ-001 | 단어 데이터 로드 | 14 | TC-001 ~ TC-014 | TC-001~003 |
| REQ-002 | 단어장 불러오기·저장 | 5 | TC-015 ~ TC-019 | TC-004~005 |
| REQ-003 | 단어 암기 | 15 | TC-020 ~ TC-034 | TC-006~007 |
| REQ-004 | 시험 출제·채점 (기본) | 8 | TC-035 ~ TC-042 | TC-008~009 |
| REQ-005 | 일차별 진도 | 22 | TC-043 ~ TC-064 | TC-010~012 |
| REQ-006 | 복습 단어 추가 | 15 | TC-065 ~ TC-079 | TC-013~014 |
| REQ-007 | 출제 가중치 | 4 | TC-080 ~ TC-083 | TC-015~016 |
| REQ-008 | 출제 방향 선택 | 1 | TC-084 ~ TC-084 | TC-017 |
| REQ-009 | 문제 유형과 채점 | 10 | TC-085 ~ TC-094 | TC-018~020 |
| REQ-010 | 학습 이력 기록 | 5 | TC-095 ~ TC-099 | TC-021~022 |
| REQ-011 | 보고서 생성 | 13 | TC-100 ~ TC-112 | TC-023~024 |

- 확정 TC 범위는 테스트 메서드 순서(요구사항 → 파일 → 메서드명)로 부여했다. 명세서 예정 범위와 숫자가 다르다.
- 명세서 8절의 예정 범위는 이 문서의 확정 범위로 대체한다. 명세서 개정은 별도 승인 후 진행한다.
- 요구사항 하나에 여러 테스트가 대응하는 것이 정상이다. 테스트 이름에 REQ ID가 포함되므로 역방향 검색이 가능하다.
- 웹 TC(TC-113~132)는 명세서 8절 예정 범위에 없던 항목이다. 웹 추가(ADR-012)에 따라 추가했다.
- 단어장 편집 TC(TC-133~160)는 ADR-013 추가에 따라 추가했다. 웹 10개, 규칙 11개, 데스크톱 흐름 7개다.

## 5. TC 상세 목록

| TC ID | 요구사항 | 테스트 파일 | 테스트 메서드 |
|---|---|---|---|
| TC-001 | REQ-001 | `test_storage.py` | `test_REQ001_blank_lines_are_ignored_and_index_follows_kept_order` |
| TC-002 | REQ-001 | `test_storage.py` | `test_REQ001_duplicate_english_keeps_first_only` |
| TC-003 | REQ-001 | `test_storage.py` | `test_REQ001_header_mismatch_raises_word_file_error` |
| TC-004 | REQ-001 | `test_storage.py` | `test_REQ001_header_with_bom_is_accepted` |
| TC-005 | REQ-001 | `test_storage.py` | `test_REQ001_meanings_are_split_by_slash` |
| TC-006 | REQ-001 | `test_storage.py` | `test_REQ001_pos_outside_allowed_list_is_skipped` |
| TC-007 | REQ-001 | `test_storage.py` | `test_REQ001_real_word_file_loads_2000_words_without_skips` |
| TC-008 | REQ-001 | `test_storage.py` | `test_REQ001_row_with_empty_english_or_meaning_is_skipped` |
| TC-009 | REQ-001 | `test_storage.py` | `test_REQ001_row_with_wrong_column_count_is_skipped_with_line_number` |
| TC-010 | REQ-001 | `test_word_list_flow.py` | `test_REQ001_bad_header_shows_warning_and_keeps_current_list` |
| TC-011 | REQ-001 | `test_word_list_flow.py` | `test_REQ001_load_emits_words_and_shows_skipped_link` |
| TC-012 | REQ-001 | `test_word_list_flow.py` | `test_REQ001_loading_words_updates_home_and_quiz_setup` |
| TC-013 | REQ-001 | `test_word_list_flow.py` | `test_REQ001_search_hides_rows_that_do_not_match_english_or_meaning` |
| TC-014 | REQ-001 | `test_word_list_flow.py` | `test_REQ001_table_shows_every_word_and_empty_message_when_none` |
| TC-015 | REQ-002 | `test_storage.py` | `test_REQ002_failed_save_keeps_original_file_and_removes_temp` |
| TC-016 | REQ-002 | `test_storage.py` | `test_REQ002_save_renumbers_from_one` |
| TC-017 | REQ-002 | `test_storage.py` | `test_REQ002_saved_file_loads_back_with_same_words` |
| TC-018 | REQ-002 | `test_word_list_flow.py` | `test_REQ002_save_failure_warns_and_keeps_existing_file` |
| TC-019 | REQ-002 | `test_word_list_flow.py` | `test_REQ002_saved_file_loads_back_to_same_words` |
| TC-020 | REQ-003 | `test_memorize_session.py` | `test_REQ003_cards_follow_new_prev_wrong_order_with_kind_labels` |
| TC-021 | REQ-003 | `test_memorize_session.py` | `test_REQ003_finished_session_is_not_in_progress` |
| TC-022 | REQ-003 | `test_memorize_session.py` | `test_REQ003_fresh_session_is_not_in_progress` |
| TC-023 | REQ-003 | `test_memorize_session.py` | `test_REQ003_going_back_does_not_repeat_record_for_seen_card` |
| TC-024 | REQ-003 | `test_memorize_session.py` | `test_REQ003_moving_to_another_card_allows_reveal_again_for_new_card` |
| TC-025 | REQ-003 | `test_memorize_session.py` | `test_REQ003_next_on_last_card_finishes_session` |
| TC-026 | REQ-003 | `test_memorize_session.py` | `test_REQ003_previous_does_nothing_on_first_card` |
| TC-027 | REQ-003 | `test_memorize_session.py` | `test_REQ003_reveal_creates_one_memorize_record_per_card` |
| TC-028 | REQ-003 | `test_memorize_session.py` | `test_REQ003_revealing_a_card_makes_session_in_progress` |
| TC-029 | REQ-003 | `test_shortcuts.py` | `test_REQ003_left_key_moves_back_and_stops_at_first_card` |
| TC-030 | REQ-003 | `test_shortcuts.py` | `test_REQ003_right_key_moves_next_but_never_completes_on_last_card` |
| TC-031 | REQ-003 | `test_shortcuts.py` | `test_REQ003_space_reveals_once_and_records_history` |
| TC-032 | REQ-003 | `test_ui_smoke.py` | `test_REQ003_finishing_day_writes_history_and_moves_to_next_day` |
| TC-033 | REQ-003 | `test_ui_smoke.py` | `test_REQ003_leaving_in_progress_session_asks_first` |
| TC-034 | REQ-003 | `test_ui_smoke.py` | `test_REQ003_opening_memorize_shows_memorize_page` |
| TC-035 | REQ-004 | `test_quiz.py` | `test_REQ004_cannot_submit_twice_for_same_question` |
| TC-036 | REQ-004 | `test_quiz.py` | `test_REQ004_count_is_capped_at_word_count` |
| TC-037 | REQ-004 | `test_quiz.py` | `test_REQ004_must_submit_before_next` |
| TC-038 | REQ-004 | `test_quiz.py` | `test_REQ004_question_count_is_respected_and_words_are_unique` |
| TC-039 | REQ-004 | `test_quiz.py` | `test_REQ004_score_and_wrong_words_after_all_questions` |
| TC-040 | REQ-004 | `test_quiz.py` | `test_REQ004_submit_creates_one_quiz_history_row_with_session_id` |
| TC-041 | REQ-004 | `test_ui_smoke.py` | `test_REQ004_leaving_unfinished_quiz_asks_first` |
| TC-042 | REQ-004 | `test_ui_smoke.py` | `test_REQ004_quiz_runs_to_result_and_writes_quiz_history` |
| TC-043 | REQ-005 | `test_day_planner.py` | `test_REQ005_2000_words_by_20_gives_100_days` |
| TC-044 | REQ-005 | `test_day_planner.py` | `test_REQ005_day_1_is_first_n_words` |
| TC-045 | REQ-005 | `test_day_planner.py` | `test_REQ005_last_day_contains_only_remaining_words` |
| TC-046 | REQ-005 | `test_day_planner.py` | `test_REQ005_last_day_set_can_be_smaller_than_n` |
| TC-047 | REQ-005 | `test_day_planner.py` | `test_REQ005_partial_last_day_is_counted` |
| TC-048 | REQ-005 | `test_day_planner.py` | `test_REQ005_word_2000_is_in_day_100` |
| TC-049 | REQ-005 | `test_json_store.py` | `test_REQ005_bool_is_not_accepted_as_integer` |
| TC-050 | REQ-005 | `test_json_store.py` | `test_REQ005_broken_progress_is_moved_to_bak` |
| TC-051 | REQ-005 | `test_json_store.py` | `test_REQ005_day_below_1_or_bad_date_is_corrected` |
| TC-052 | REQ-005 | `test_json_store.py` | `test_REQ005_missing_file_starts_at_day_1` |
| TC-053 | REQ-005 | `test_json_store.py` | `test_REQ005_save_then_load_round_trip` |
| TC-054 | REQ-005 | `test_json_store.py` | `test_REQ005_words_per_day_out_of_range_falls_back_to_default` |
| TC-055 | REQ-005 | `test_memorize_session.py` | `test_REQ005_completing_day_moves_to_next_day_and_sets_date` |
| TC-056 | REQ-005 | `test_memorize_session.py` | `test_REQ005_relearning_an_old_day_does_not_move_back` |
| TC-057 | REQ-005 | `test_settings_dialog.py` | `test_REQ005_cancelled_dialog_saves_nothing` |
| TC-058 | REQ-005 | `test_settings_dialog.py` | `test_REQ005_changing_words_per_day_asks_before_accepting` |
| TC-059 | REQ-005 | `test_settings_dialog.py` | `test_REQ005_fields_show_current_values_and_percent_for_ratios` |
| TC-060 | REQ-005 | `test_settings_dialog.py` | `test_REQ005_other_changes_accept_without_asking` |
| TC-061 | REQ-005 | `test_settings_dialog.py` | `test_REQ005_restore_defaults_fills_fields_without_saving` |
| TC-062 | REQ-005 | `test_settings_dialog.py` | `test_REQ005_result_converts_percent_back_to_decimal` |
| TC-063 | REQ-005 | `test_settings_dialog.py` | `test_REQ005_saved_settings_persist_and_update_quiz_setup` |
| TC-064 | REQ-005 | `test_ui_smoke.py` | `test_REQ005_empty_word_list_disables_start` |
| TC-065 | REQ-006 | `test_day_planner.py` | `test_REQ006_card_order_is_new_then_prev_then_wrong` |
| TC-066 | REQ-006 | `test_day_planner.py` | `test_REQ006_day_1_has_no_previous_review` |
| TC-067 | REQ-006 | `test_day_planner.py` | `test_REQ006_float_noise_does_not_break_half` |
| TC-068 | REQ-006 | `test_day_planner.py` | `test_REQ006_half_rounds_up_not_to_even` |
| TC-069 | REQ-006 | `test_day_planner.py` | `test_REQ006_memorized_keys_are_lowercase` |
| TC-070 | REQ-006 | `test_day_planner.py` | `test_REQ006_no_memorization_on_previous_day_gives_empty_review` |
| TC-071 | REQ-006 | `test_day_planner.py` | `test_REQ006_previous_day_review_uses_only_memorized_words` |
| TC-072 | REQ-006 | `test_day_planner.py` | `test_REQ006_review_word_is_not_repeated_as_new_word` |
| TC-073 | REQ-006 | `test_day_planner.py` | `test_REQ006_set_has_n_words_without_duplicates` |
| TC-074 | REQ-006 | `test_day_planner.py` | `test_REQ006_word_without_wrong_answer_is_not_a_wrong_candidate` |
| TC-075 | REQ-006 | `test_day_planner.py` | `test_REQ006_wrong_review_picks_from_top_candidates_only` |
| TC-076 | REQ-006 | `test_json_store.py` | `test_REQ006_broken_json_is_moved_to_bak_and_defaults_used` |
| TC-077 | REQ-006 | `test_json_store.py` | `test_REQ006_missing_file_gives_defaults_without_warnings` |
| TC-078 | REQ-006 | `test_json_store.py` | `test_REQ006_ratio_with_wrong_type_falls_back_to_default` |
| TC-079 | REQ-006 | `test_json_store.py` | `test_REQ006_save_then_load_round_trip` |
| TC-080 | REQ-007 | `test_quiz.py` | `test_REQ007_minimum_weight_is_half` |
| TC-081 | REQ-007 | `test_quiz.py` | `test_REQ007_table_examples_from_process_design` |
| TC-082 | REQ-007 | `test_quiz.py` | `test_REQ007_unseen_word_has_weight_4` |
| TC-083 | REQ-007 | `test_quiz.py` | `test_REQ007_word_with_high_weight_is_drawn_more_often` |
| TC-084 | REQ-008 | `test_quiz.py` | `test_REQ008_mixed_direction_produces_both_directions` |
| TC-085 | REQ-009 | `test_quiz.py` | `test_REQ009_choice_answer_by_index_and_text` |
| TC-086 | REQ-009 | `test_quiz.py` | `test_REQ009_choice_question_has_four_options_including_answer_and_no_overlap` |
| TC-087 | REQ-009 | `test_quiz.py` | `test_REQ009_meaning_tokens_split_on_slash_and_trim` |
| TC-088 | REQ-009 | `test_quiz.py` | `test_REQ009_ox_answer_is_case_insensitive` |
| TC-089 | REQ-009 | `test_quiz.py` | `test_REQ009_ox_question_uses_only_o_or_x_answers` |
| TC-090 | REQ-009 | `test_quiz.py` | `test_REQ009_short_answer_accepts_all_words_with_same_meaning` |
| TC-091 | REQ-009 | `test_quiz.py` | `test_REQ009_short_answer_ignores_case_and_spaces` |
| TC-092 | REQ-009 | `test_quiz.py` | `test_REQ009_words_sharing_a_meaning_overlap` |
| TC-093 | REQ-009 | `test_quiz.py` | `test_REQ009_wrong_short_answer_shows_correct_answer` |
| TC-094 | REQ-009 | `test_shortcuts.py` | `test_REQ009_number_key_selects_matching_choice` |
| TC-095 | REQ-010 | `test_history_csv.py` | `test_REQ010_append_and_read_round_trip` |
| TC-096 | REQ-010 | `test_history_csv.py` | `test_REQ010_first_append_creates_file_with_header_once` |
| TC-097 | REQ-010 | `test_history_csv.py` | `test_REQ010_malformed_rows_are_ignored` |
| TC-098 | REQ-010 | `test_history_csv.py` | `test_REQ010_missing_file_reads_as_empty` |
| TC-099 | REQ-010 | `test_quiz.py` | `test_REQ010_session_id_format` |
| TC-100 | REQ-011 | `test_day_planner.py` | `test_REQ011_aggregate_counts_only_quiz_rows` |
| TC-101 | REQ-011 | `test_report_builder.py` | `test_REQ011_all_period_keeps_every_past_record` |
| TC-102 | REQ-011 | `test_report_builder.py` | `test_REQ011_changing_period_changes_numbers` |
| TC-103 | REQ-011 | `test_report_builder.py` | `test_REQ011_counts_study_days_memorized_words_sessions_and_accuracy` |
| TC-104 | REQ-011 | `test_report_builder.py` | `test_REQ011_no_quiz_rows_shows_not_applicable` |
| TC-105 | REQ-011 | `test_report_builder.py` | `test_REQ011_recent_7_days_includes_today_and_six_days_before` |
| TC-106 | REQ-011 | `test_report_builder.py` | `test_REQ011_same_second_adds_suffix_and_never_overwrites` |
| TC-107 | REQ-011 | `test_report_builder.py` | `test_REQ011_saves_utf8_file_with_timestamp_name` |
| TC-108 | REQ-011 | `test_report_builder.py` | `test_REQ011_top_wrong_requires_three_attempts_and_sorts_by_rate` |
| TC-109 | REQ-011 | `test_report_builder.py` | `test_REQ011_unknown_words_and_skipped_rows_are_reported` |
| TC-110 | REQ-011 | `test_report_flow.py` | `test_REQ011_history_creates_report_file_and_shows_preview` |
| TC-111 | REQ-011 | `test_report_flow.py` | `test_REQ011_no_history_shows_message_and_creates_no_file` |
| TC-112 | REQ-011 | `test_report_flow.py` | `test_REQ011_read_history_counts_skipped_rows_but_not_blank_lines` |
| TC-113 | REQ-001 | `test_web_app.py` | `test_REQ001_home_shows_today_day_and_range` |
| TC-114 | REQ-002 | `test_web_app.py` | `test_REQ002_words_page_filters_by_english_or_meaning` |
| TC-115 | REQ-002 | `test_web_app.py` | `test_REQ002_words_page_lists_skipped_rows` |
| TC-116 | REQ-003 | `test_web_app.py` | `test_REQ003_memorize_reveal_writes_history_once_per_card` |
| TC-117 | REQ-005 | `test_web_app.py` | `test_REQ005_completing_last_card_advances_day` |
| TC-118 | REQ-003 | `test_web_app.py` | `test_REQ003_next_on_last_card_does_not_complete_before_reaching_it` |
| TC-119 | REQ-003 | `test_web_app.py` | `test_REQ003_abandon_keeps_progress` |
| TC-120 | REQ-004 | `test_web_app.py` | `test_REQ004_quiz_correct_answer_is_graded_and_recorded` |
| TC-121 | REQ-004 | `test_web_app.py` | `test_REQ004_quiz_setup_rejects_invalid_count` |
| TC-122 | REQ-008 | `test_web_app.py` | `test_REQ008_quiz_setup_rejects_missing_question_type` |
| TC-123 | REQ-004 | `test_web_app.py` | `test_REQ004_multiple_choice_requires_selection` |
| TC-124 | REQ-004 | `test_web_app.py` | `test_REQ004_choice_and_ox_questions_render_their_inputs` |
| TC-125 | REQ-003 | `test_web_app.py` | `test_REQ003_memorize_card_shows_meaning_only_after_reveal` |
| TC-126 | REQ-001 | `test_web_app.py` | `test_REQ001_user_text_is_escaped_in_pages` |
| TC-127 | REQ-005 | `test_web_app.py` | `test_REQ005_changing_words_per_day_requires_confirmation` |
| TC-128 | REQ-006 | `test_web_app.py` | `test_REQ006_out_of_range_ratio_is_rejected` |
| TC-129 | REQ-006 | `test_web_app.py` | `test_REQ006_ratio_is_saved_as_fraction` |
| TC-130 | ADR-011 | `test_web_app.py` | `test_ADR011_settings_cannot_change_while_in_progress` |
| TC-131 | REQ-011 | `test_web_app.py` | `test_REQ011_report_without_history_creates_no_file` |
| TC-132 | REQ-011 | `test_web_app.py` | `test_REQ011_report_is_saved_after_study` |
| TC-133 | REQ-001 | `test_web_app.py` | `test_REQ001_add_changes_draft_only_until_saved` |
| TC-134 | REQ-001 | `test_web_app.py` | `test_REQ001_add_duplicate_shows_error_and_keeps_draft` |
| TC-135 | REQ-001 | `test_web_app.py` | `test_REQ001_meaning_only_edit_saves_without_confirmation` |
| TC-136 | ADR-013 | `test_web_app.py` | `test_ADR013_layout_change_needs_confirmation_before_save` |
| TC-137 | ADR-013 | `test_web_app.py` | `test_ADR013_save_keeps_previous_file_as_backup` |
| TC-138 | ADR-013 | `test_web_app.py` | `test_ADR013_discard_restores_file_contents` |
| TC-139 | ADR-013 | `test_web_app.py` | `test_ADR013_import_loads_draft_without_touching_file` |
| TC-140 | ADR-013 | `test_web_app.py` | `test_ADR013_skipped_rows_warn_before_save` |
| TC-141 | ADR-013 | `test_web_app.py` | `test_ADR013_editing_is_blocked_while_learning` |
| TC-142 | REQ-001 | `test_web_app.py` | `test_REQ001_dirty_banner_appears_on_other_pages` |
| TC-143 | REQ-001 | `test_word_editor.py` | `test_REQ001_empty_english_pos_and_meaning_are_reported` |
| TC-144 | REQ-001 | `test_word_editor.py` | `test_REQ001_duplicate_english_is_rejected_ignoring_case` |
| TC-145 | REQ-001 | `test_word_editor.py` | `test_REQ001_editing_same_word_is_not_a_duplicate` |
| TC-146 | REQ-001 | `test_word_editor.py` | `test_REQ001_parse_meanings_splits_on_slash_and_drops_blanks` |
| TC-147 | REQ-001 | `test_word_editor.py` | `test_REQ001_add_appends_and_renumbers` |
| TC-148 | REQ-001 | `test_word_editor.py` | `test_REQ001_update_changes_key_when_english_changes` |
| TC-149 | REQ-001 | `test_word_editor.py` | `test_REQ001_delete_removes_and_renumbers` |
| TC-150 | ADR-013 | `test_word_editor.py` | `test_ADR013_meaning_only_edit_keeps_day_layout` |
| TC-151 | ADR-013 | `test_word_editor.py` | `test_ADR013_add_or_delete_or_rename_changes_day_layout` |
| TC-152 | ADR-013 | `test_word_editor.py` | `test_ADR013_save_keeps_previous_file_as_backup` |
| TC-153 | ADR-013 | `test_word_editor.py` | `test_ADR013_first_save_creates_no_backup` |
| TC-154 | REQ-001 | `test_word_editing_flow.py` | `test_REQ001_add_edit_delete_change_draft_but_not_file` |
| TC-155 | REQ-001 | `test_word_editing_flow.py` | `test_REQ001_invalid_input_is_rejected_and_draft_unchanged` |
| TC-156 | ADR-013 | `test_word_editing_flow.py` | `test_ADR013_editing_is_blocked_while_learning` |
| TC-157 | ADR-013 | `test_word_editing_flow.py` | `test_ADR013_save_writes_file_and_keeps_backup` |
| TC-158 | ADR-013 | `test_word_editing_flow.py` | `test_ADR013_save_is_cancelled_when_user_declines_warning` |
| TC-159 | ADR-013 | `test_word_editing_flow.py` | `test_ADR013_meaning_only_edit_saves_without_warning` |
| TC-160 | ADR-013 | `test_word_editing_flow.py` | `test_ADR013_discard_restores_file_contents` |
| TC-161 | ADR-013 | `test_web_app.py` | `test_ADR013_edit_autosaves_draft_file` |
| TC-162 | ADR-013 | `test_web_app.py` | `test_ADR013_restart_restores_unsaved_draft` |
| TC-163 | ADR-013 | `test_web_app.py` | `test_ADR013_restored_draft_keeps_layout_change_check` |
| TC-164 | ADR-013 | `test_web_app.py` | `test_ADR013_save_removes_draft_file` |
| TC-165 | ADR-013 | `test_web_app.py` | `test_ADR013_discard_removes_draft_file` |
| TC-166 | ADR-013 | `test_web_app.py` | `test_ADR013_restored_notice_is_shown` |
| TC-167 | ADR-013 | `test_web_app.py` | `test_ADR013_exit_message_only_when_unsaved` |
| TC-168 | ADR-013 | `test_web_app.py` | `test_ADR013_corrupt_draft_is_ignored_with_message` |
| TC-169 | ADR-012 | `test_instance_lock.py` | `test_ISSUE14_first_instance_creates_lock_and_release_removes_it` |
| TC-170 | ADR-012 | `test_instance_lock.py` | `test_ISSUE14_second_instance_is_refused_while_first_is_alive` |
| TC-171 | ADR-012 | `test_instance_lock.py` | `test_ISSUE14_stale_lock_from_dead_process_is_cleaned_up` |
| TC-172 | ADR-012 | `test_instance_lock.py` | `test_ISSUE14_unreadable_lock_is_not_removed_automatically` |
| TC-173 | ADR-012 | `test_instance_lock.py` | `test_ISSUE14_release_does_not_remove_someone_elses_lock` |
| TC-174 | ADR-012 | `test_instance_lock.py` | `test_ISSUE14_is_process_alive_detects_running_and_finished_processes` |
| TC-175 | ADR-012 | `test_entrypoints.py` | `test_ISSUE14_desktop_entrypoint_imports_and_exposes_main` |
| TC-176 | ADR-012 | `test_entrypoints.py` | `test_ISSUE14_web_entrypoint_imports_and_exposes_main` |

## 6. 실행 결과

| 일자 | 실행 | 결과 |
|------|------|------|
| 2026-11-18 | `python -m unittest discover -s tests -t .` | Ran 112 tests, OK |
| 2026-11-25 | `python -m unittest discover -s tests -t .` | Ran 132 tests, OK (기존 112 + 웹 20) |
| 2026-11-25 | `python -m unittest discover -s tests -t .` | Ran 160 tests, OK (웹 20 + 편집 28 포함) |
| 2026-11-25 | `python -m unittest discover -s tests -t .` | Ran 176 tests, OK (편집 28 + 초안 보호 8 + 잠금 6 + 진입점 2 포함) |

## 7. 기능별 확인 방법 (요약)

- 단어장 로드·저장 (REQ-001, 002): CSV 헤더 검사, 건너뛴 행 보고, 임시 파일 교체로 실패 시 원본 보존을 확인한다.
- 암기 (REQ-003): 카드 순서, 뜻 보기 시 이력 1회 기록, 마지막 카드 완료 처리, 단축 키를 확인한다.
- 일차와 복습 (REQ-005, 006): 일차 범위, 전날 복습은 이력으로만 계산 (ADR-008), 오답 복습 후보를 확인한다.
- 시험 (REQ-004, 007~010): 가중치 예시 값, 방향·유형 선택, 4지선다 보기, OX, 단답형 정답 판정, 문제별 1회 채점, 세션ID를 확인한다.
- 보고서 (REQ-011): 기간 필터, 집계 항목, Top 10 규칙 (출제 3회 이상), 무시한 행 수, 중복 없는 파일명을 확인한다.
- 웹 (ADR-012): 홈 일차 표시, 암기 완료 시 진도 증가, 카드당 1회 이력, 시험 채점과 이력, 설정 확인 체크와 범위 검사, 진행 중 설정 저장 차단, 보고서 파일 저장, 사용자 입력 이스케이프를 확인한다.
- 단어장 편집 (ADR-013): 초안 편집, 저장 확인, `.bak` 백업, 취소, 진행 중 차단을 확인한다.

## 8. 수동 점검

| ID | 항목 | 결과 |
|----|------|------|
| M-01 | 암기·시험 화면의 배치, 글자 크기, 보기 배치 (이슈 #5) | 2026-11-18 사용자 점검 완료 |
| M-02 | 웹 화면(`python -m src.web`)을 브라우저에서 열어 암기·시험·설정 흐름과 한글 표시 확인 | 2026-11-25 사용자 점검 완료 (이슈 #9) |

자동 테스트는 화면 픽셀이나 한글 글꼴 렌더링을 검사하지 않는다. 화면 모양은 M-01로 확인한다.

## 9. 한계

- 단축 키 테스트는 `QKeyEvent`를 직접 전달하거나 핸들러를 호출하는 방식이다. 실제 키 입력 이벤트 경로는 검사하지 않는다.
- 위키낱말사전 조회·대조 스크립트(`ai-agent/claude/261118_사전대조/script/`)는 자동 테스트 대상이 아니다. 산출물 검토 기록으로 관리한다.
- 보고서 Top 10에서 오답률과 오답 수가 모두 같을 때의 정렬 순서는 키 문자열 순서로 정한다. 이 규칙은 테스트하지 않는다.
- 웹 테스트는 HTTP 요청 수준이다. 브라우저의 단축 키(JavaScript), 실제 화면 배치, 글꼴은 검사하지 않는다 (M-02).
- 단어장 편집은 메모리 초안을 다룬다. 서버 종료 시 초안 소실과 데스크톱·웹 동시 편집은 자동 테스트 대상이 아니다 (이슈 #13, #14).

## 10. 변경 이력

| 버전 | 날짜 | 내용 |
|------|------|------|
| v1.0 | 2026-11-18 | 최초 작성. TC-001~112 확정, 명세서 8절 예정 범위 대체 |
| v1.1 | 2026-11-25 | 웹 버전 흐름 테스트 TC-113~132 추가 (ADR-012). 실행 결과 132개 OK. M-02 추가 (미실시) |
| v1.2 | 2026-11-25 | 단어장 편집 TC-133~160 추가 (ADR-013). 실행 결과 160개 OK. M-02 사용자 점검 완료 (이슈 #9) |
| v1.3 | 2026-11-25 | 저장하지 않은 웹 초안 보호 TC-161~168(ADR-013), 실행 잠금과 시작 모듈 TC-169~176(ADR-012) 추가. 실행 결과 176개 OK (#13, #14) |
