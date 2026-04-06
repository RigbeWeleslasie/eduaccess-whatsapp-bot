import zipfile
from io import BytesIO
from unittest.mock import patch

from django.test import TestCase

from .ai import generate_question
from .models import TopicProgress, UserProgress


class WhatsAppWebhookTests(TestCase):
    @patch("whatsapp_bot.views.generate_question")
    def test_practice_starts_and_tracks_question(self, mock_generate_question):
        mock_generate_question.return_value = ("What is 2 + 2?", "4", "Maths")

        response = self.client.post(
            "/whatsapp/",
            {"Body": "practice", "From": "whatsapp:+111111111"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Practice question", response.content.decode())

        progress = UserProgress.objects.get(phone_number="whatsapp:+111111111")
        self.assertTrue(progress.awaiting_practice_answer)
        self.assertEqual(progress.last_question, "What is 2 + 2?")
        self.assertEqual(progress.last_answer, "4")
        self.assertEqual(progress.last_topic, "Maths")

    @patch("whatsapp_bot.views.generate_question")
    def test_practice_answer_is_graded_and_score_saved(self, mock_generate_question):
        mock_generate_question.return_value = ("What is 2 + 2?", "4", "Maths")

        self.client.post(
            "/whatsapp/",
            {"Body": "practice", "From": "whatsapp:+222222222"},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "4", "From": "whatsapp:+222222222"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Correct! Well done.", body)
        self.assertIn("Session score: 1/1.", body)
        self.assertIn("Overall progress: 1/1.", body)

        progress = UserProgress.objects.get(phone_number="whatsapp:+222222222")
        self.assertFalse(progress.awaiting_practice_answer)
        self.assertEqual(progress.correct_answers, 1)
        self.assertEqual(progress.total_attempts, 1)
        self.assertEqual(progress.session_correct_answers, 1)
        self.assertEqual(progress.session_total_attempts, 1)

    @patch("whatsapp_bot.views.generate_question")
    def test_maths_fraction_answer_accepts_decimal_equivalent(self, mock_generate_question):
        mock_generate_question.return_value = ("What is 1/2 + 1/4?", "3/4", "Fractions")

        self.client.post(
            "/whatsapp/",
            {"Body": "practice maths", "From": "whatsapp:+212121212"},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "0.75", "From": "whatsapp:+212121212"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertIn("Correct! Well done.", response.content.decode())

    @patch("whatsapp_bot.views.generate_question")
    def test_maths_equation_answer_accepts_variable_form(self, mock_generate_question):
        mock_generate_question.return_value = ("Solve for x: 3x = 18", "6", "Algebra")

        self.client.post(
            "/whatsapp/",
            {"Body": "practice maths", "From": "whatsapp:+313131313"},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "x = 6", "From": "whatsapp:+313131313"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertIn("Correct! Well done.", response.content.decode())

    @patch("whatsapp_bot.views.generate_question")
    def test_maths_percent_answer_accepts_decimal_equivalent(self, mock_generate_question):
        mock_generate_question.return_value = ("Write 25% as a decimal.", "0.25", "Percentages")

        self.client.post(
            "/whatsapp/",
            {"Body": "practice maths", "From": "whatsapp:+414141414"},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "25%", "From": "whatsapp:+414141414"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertIn("Correct! Well done.", response.content.decode())

    @patch("whatsapp_bot.views.generate_question")
    def test_practice_shows_lesson_progress(self, mock_generate_question):
        mock_generate_question.return_value = ("Solve for x: x + 7 = 15", "8", "Algebra")

        response = self.client.post(
            "/whatsapp/",
            {"Body": "practice maths", "From": "whatsapp:+515151515"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertIn("Lesson 1/3.", response.content.decode())

    @patch("whatsapp_bot.views.generate_question")
    def test_plain_practice_continues_same_lesson_topic(self, mock_generate_question):
        mock_generate_question.side_effect = [
            ("Solve for x: x + 7 = 15", "8", "Algebra"),
            ("Solve for x: x + 9 = 14", "5", "Algebra"),
        ]

        phone_number = "whatsapp:+616161616"
        self.client.post(
            "/whatsapp/",
            {"Body": "practice maths", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        self.client.post(
            "/whatsapp/",
            {"Body": "8", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "practice", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )

        body = response.content.decode()
        self.assertIn("Practice question (Algebra", body)
        self.assertIn("Lesson 2/3.", body)

    @patch("whatsapp_bot.views.generate_question")
    def test_lesson_completes_and_recommends_next_topic(self, mock_generate_question):
        mock_generate_question.side_effect = [
            ("Solve for x: x + 7 = 15", "8", "Algebra"),
            ("Solve for x: x + 9 = 14", "5", "Algebra"),
            ("Solve for x: x + 4 = 10", "6", "Algebra"),
        ]

        phone_number = "whatsapp:+717171717"
        self.client.post(
            "/whatsapp/",
            {"Body": "practice maths", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        self.client.post(
            "/whatsapp/",
            {"Body": "8", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        self.client.post(
            "/whatsapp/",
            {"Body": "practice", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        self.client.post(
            "/whatsapp/",
            {"Body": "5", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        self.client.post(
            "/whatsapp/",
            {"Body": "practice", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "6", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )

        body = response.content.decode()
        self.assertIn("Lesson complete: Algebra.", body)
        self.assertIn("Next topic:", body)

    @patch("whatsapp_bot.views.generate_question")
    def test_practice_subject_can_be_requested(self, mock_generate_question):
        mock_generate_question.return_value = ("Choose the correct verb.", "is", "English")

        response = self.client.post(
            "/whatsapp/",
            {"Body": "practice english", "From": "whatsapp:+444444444"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Practice question (English, foundation)", response.content.decode())
        mock_generate_question.assert_called_once_with(
            subject="english",
            topic="Articles",
            difficulty="foundation",
        )

    @patch("whatsapp_bot.views.generate_question")
    def test_english_practice_uses_requested_subject(self, mock_generate_question):
        mock_generate_question.return_value = (
            "Choose the correct word: She ___ to school yesterday. A. go B. went C. going",
            "B|went",
            "Verb tense",
        )

        response = self.client.post(
            "/whatsapp/",
            {"Body": "practice english", "From": "whatsapp:+888888888"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Verb tense", body)
        self.assertIn("She ___ to school yesterday", body)

    @patch("whatsapp_bot.views.generate_question")
    def test_practice_difficulty_can_be_requested(self, mock_generate_question):
        mock_generate_question.return_value = ("Solve 12 x 8.", "96", "Multiplication")

        response = self.client.post(
            "/whatsapp/",
            {"Body": "practice maths stretch", "From": "whatsapp:+555555555"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("stretch", response.content.decode().lower())
        mock_generate_question.assert_called_once_with(
            subject="maths",
            topic="Integers",
            difficulty="stretch",
        )

    @patch("whatsapp_bot.views.ask_ai")
    def test_normal_message_uses_ai_when_not_in_practice_mode(self, mock_ask_ai):
        mock_ask_ai.return_value = "Derivative means rate of change."

        response = self.client.post(
            "/whatsapp/",
            {"Body": "What is a derivative?", "From": "whatsapp:+333333333"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Derivative means rate of change.", response.content.decode())
        mock_ask_ai.assert_called_once_with("What is a derivative?", low_data=True)

    def test_low_data_mode_can_be_turned_off(self):
        phone_number = "whatsapp:+818181818"
        response = self.client.post(
            "/whatsapp/",
            {"Body": "lite off", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Data saver is off.", response.content.decode())

        progress = UserProgress.objects.get(phone_number=phone_number)
        self.assertFalse(progress.low_data_mode)

    def test_offline_mode_can_be_turned_on(self):
        phone_number = "whatsapp:+161111111"
        response = self.client.post(
            "/whatsapp/",
            {"Body": "offline on", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Offline mode is on.", response.content.decode())

        progress = UserProgress.objects.get(phone_number=phone_number)
        self.assertTrue(progress.offline_mode)

    def test_offline_status_reports_current_mode(self):
        phone_number = "whatsapp:+171111111"
        self.client.post(
            "/whatsapp/",
            {"Body": "offline on", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "offline status", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Offline mode is on.", response.content.decode())

    def test_learning_packs_can_be_listed(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "packs", "From": "whatsapp:+121111111"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode().lower()
        self.assertIn("available packs", body)
        self.assertIn("algebra", body)

    def test_learning_pack_can_be_requested_by_topic(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "pack passive voice", "From": "whatsapp:+131111111"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode().lower()
        self.assertIn("passive voice pack", body)
        self.assertIn("/packs/english-passive-voice/", body)
        self.assertIn("/offline-packs/english-passive-voice/", body)

    def test_learning_pack_download_endpoint_returns_text_file(self):
        response = self.client.get(
            "/packs/english-passive-voice/",
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("PASSIVE VOICE", response.content.decode())

    def test_audio_packs_can_be_listed(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "audio packs", "From": "whatsapp:+141111111"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode().lower()
        self.assertIn("audio packs", body)
        self.assertIn("algebra", body)

    def test_audio_pack_can_be_requested_by_topic(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "audio pack passive voice", "From": "whatsapp:+151111111"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode().lower()
        self.assertIn("passive voice audio pack", body)
        self.assertIn("/audio-packs/audio-english-passive-voice/player/", body)
        self.assertIn("/audio-packs/audio-english-passive-voice/transcript/", body)
        self.assertIn("/offline-packs/english-passive-voice/", body)

    def test_audio_pack_transcript_download_endpoint_returns_text_file(self):
        response = self.client.get(
            "/audio-packs/audio-english-passive-voice/transcript/",
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("Passive voice focuses on the receiver", response.content.decode())

    def test_audio_pack_player_endpoint_returns_html_page(self):
        response = self.client.get(
            "/audio-packs/audio-english-passive-voice/player/",
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])
        self.assertIn("Play Audio Lesson", response.content.decode())
        self.assertIn("speechSynthesis", response.content.decode())

    def test_offline_bundles_can_be_listed(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "offline packs", "From": "whatsapp:+161616161"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode().lower()
        self.assertIn("offline study bundles", body)
        self.assertIn("offline pack algebra", body)

    def test_offline_library_command_returns_library_link(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "offline library", "From": "whatsapp:+161600000"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode().lower()
        self.assertIn("offline library is ready", body)
        self.assertIn("/offline-library/", body)

    def test_offline_all_command_returns_archive_link(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "offline all", "From": "whatsapp:+161600001"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode().lower()
        self.assertIn("full offline archive is ready", body)
        self.assertIn("/offline-library/download/", body)

    def test_offline_bundle_can_be_requested_by_topic(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "offline pack passive voice", "From": "whatsapp:+171717171"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode().lower()
        self.assertIn("offline bundle ready", body)
        self.assertIn("/offline-packs/english-passive-voice/", body)

    def test_offline_bundle_download_endpoint_returns_zip_bundle(self):
        response = self.client.get(
            "/offline-packs/english-passive-voice/",
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("offline-bundle.zip", response["Content-Disposition"])

        with zipfile.ZipFile(BytesIO(response.content)) as bundle_zip:
            names = set(bundle_zip.namelist())
            self.assertIn("README.txt", names)
            self.assertIn("lesson.txt", names)
            self.assertIn("audio-transcript.txt", names)
            self.assertIn("audio-player.html", names)
            self.assertIn("PASSIVE VOICE", bundle_zip.read("lesson.txt").decode())
            self.assertIn("speechSynthesis", bundle_zip.read("audio-player.html").decode())

    def test_offline_library_page_lists_downloadable_entries(self):
        response = self.client.get(
            "/offline-library/",
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode().lower()
        self.assertIn("eduaccess offline library", body)
        self.assertIn("/offline-library/download/", body)
        self.assertIn("/offline-packs/maths-algebra-basics/", body)
        self.assertIn("/audio-packs/audio-maths-algebra-basics/player/", body)

    def test_offline_library_download_returns_zip_of_bundle_zips(self):
        response = self.client.get(
            "/offline-library/download/",
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("eduaccess-offline-library.zip", response["Content-Disposition"])

        with zipfile.ZipFile(BytesIO(response.content)) as archive_zip:
            names = set(archive_zip.namelist())
            self.assertIn("README.txt", names)
            self.assertIn("maths-algebra-basics.zip", names)
            nested_bundle = archive_zip.read("maths-algebra-basics.zip")
            with zipfile.ZipFile(BytesIO(nested_bundle)) as bundle_zip:
                self.assertIn("lesson.txt", bundle_zip.namelist())

    @patch("whatsapp_bot.views.ask_ai")
    def test_offline_mode_uses_local_pack_reply_for_topic_question(self, mock_ask_ai):
        phone_number = "whatsapp:+181111111"
        self.client.post(
            "/whatsapp/",
            {"Body": "offline on", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "Teach me passive voice", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode().lower()
        self.assertIn("passive voice pack", body)
        self.assertIn("/packs/english-passive-voice/", body)
        mock_ask_ai.assert_not_called()

    @patch("whatsapp_bot.views.ask_ai")
    def test_ai_uses_full_mode_when_low_data_is_off(self, mock_ask_ai):
        mock_ask_ai.return_value = "Longer explanation."
        phone_number = "whatsapp:+919191919"
        self.client.post(
            "/whatsapp/",
            {"Body": "lite off", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "Explain photosynthesis", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Longer explanation.", response.content.decode())
        mock_ask_ai.assert_called_once_with("Explain photosynthesis", low_data=False)

    @patch("whatsapp_bot.views.ask_ai")
    @patch("whatsapp_bot.views.generate_question")
    def test_general_question_exits_practice_mode_and_uses_ai(
        self,
        mock_generate_question,
        mock_ask_ai,
    ):
        mock_generate_question.return_value = ("What is 2 + 2?", "4", "Addition")
        mock_ask_ai.return_value = "Photosynthesis is how plants make food."

        phone_number = "whatsapp:+232323232"
        self.client.post(
            "/whatsapp/",
            {"Body": "practice maths", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "What is photosynthesis?", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Photosynthesis is how plants make food.", response.content.decode())

        progress = UserProgress.objects.get(phone_number=phone_number)
        self.assertFalse(progress.awaiting_practice_answer)


class PracticeBankTests(TestCase):
    def test_secondary_school_maths_question_comes_from_local_bank(self):
        question, answer, topic = generate_question(subject="maths", difficulty="core")
        self.assertTrue(question)
        self.assertTrue(answer)
        self.assertIn(
            topic,
            {"Linear equations", "Simultaneous equations", "Geometry", "Statistics"},
        )

    def test_secondary_school_english_question_comes_from_local_bank(self):
        question, answer, topic = generate_question(subject="english", difficulty="core")
        self.assertTrue(question)
        self.assertTrue(answer)
        self.assertIn(
            topic,
            {"Reported speech", "Parts of speech", "Sentence correction", "Comprehension"},
        )

    def test_english_grammar_topic_can_be_requested(self):
        question, answer, topic = generate_question(subject="english", difficulty="foundation", topic="grammar")
        self.assertTrue(question)
        self.assertTrue(answer)
        self.assertIn(
            topic,
            {"Subject-verb agreement", "Articles"},
        )

    def test_english_reported_speech_topic_can_be_requested(self):
        question, answer, topic = generate_question(subject="english", difficulty="core", topic="reported speech")
        self.assertEqual(topic, "Reported speech")
        self.assertIn("reported speech", question.lower())

    def test_english_passive_voice_topic_can_be_requested_across_difficulties(self):
        question, answer, topic = generate_question(subject="english", difficulty="foundation", topic="passive voice")
        self.assertEqual(topic, "Passive voice")
        self.assertIn("passive voice", question.lower())

    @patch("whatsapp_bot.views.generate_question")
    def test_wrong_answer_creates_topic_progress_and_remediation(self, mock_generate_question):
        mock_generate_question.side_effect = [
            ("What is 5 + 5?", "10", "Addition"),
            ("What is 2 + 3?", "5", "Addition"),
        ]

        self.client.post(
            "/whatsapp/",
            {"Body": "practice maths core", "From": "whatsapp:+666666666"},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "8", "From": "whatsapp:+666666666"},
            HTTP_HOST="127.0.0.1",
        )

        body = response.content.decode()
        self.assertIn("Not quite. The correct answer is: 10", body)
        self.assertIn("Quick retry on Addition", body)
        self.assertIn("Session score: 0/1.", body)

        progress = UserProgress.objects.get(phone_number="whatsapp:+666666666")
        self.assertTrue(progress.awaiting_practice_answer)
        self.assertTrue(progress.awaiting_remediation)
        self.assertEqual(progress.total_attempts, 1)

        topic_progress = TopicProgress.objects.get(user=progress, subject="maths", topic="Addition")
        self.assertEqual(topic_progress.attempts, 1)
        self.assertEqual(topic_progress.correct_answers, 0)
        self.assertEqual(topic_progress.last_outcome, "incorrect")

    @patch("whatsapp_bot.views.generate_question")
    def test_progress_message_reports_weak_areas(self, mock_generate_question):
        mock_generate_question.side_effect = [
            ("What is 9 + 1?", "10", "Addition"),
            ("What is 2 + 2?", "4", "Addition"),
        ]

        phone_number = "whatsapp:+777777777"
        self.client.post(
            "/whatsapp/",
            {"Body": "practice maths", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        self.client.post(
            "/whatsapp/",
            {"Body": "7", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "progress", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )

        body = response.content.decode()
        self.assertIn("Current session: 0/1.", body)
        self.assertIn("Revise next: Addition.", body)

    @patch("whatsapp_bot.views.generate_question")
    def test_english_option_answer_accepts_letter_or_word(self, mock_generate_question):
        mock_generate_question.return_value = (
            "Choose the correct word: She ___ to school yesterday. A. go B. went C. going",
            "B|went",
            "Verb tense",
        )

        phone_number = "whatsapp:+999999999"
        self.client.post(
            "/whatsapp/",
            {"Body": "practice english", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "went", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )

        self.assertIn("Correct! Well done.", response.content.decode())

    @patch("whatsapp_bot.views.generate_question")
    def test_new_practice_command_resets_session_score(self, mock_generate_question):
        mock_generate_question.side_effect = [
            ("What is 2 + 2?", "4", "Addition"),
            ("What is 3 + 3?", "6", "Addition"),
        ]

        phone_number = "whatsapp:+121212121"
        self.client.post(
            "/whatsapp/",
            {"Body": "practice maths", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        self.client.post(
            "/whatsapp/",
            {"Body": "4", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        self.client.post(
            "/whatsapp/",
            {"Body": "practice maths", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )

        progress = UserProgress.objects.get(phone_number=phone_number)
        self.assertEqual(progress.session_correct_answers, 0)
        self.assertEqual(progress.session_total_attempts, 0)

    @patch("whatsapp_bot.views.generate_question")
    def test_stop_command_exits_practice_mode(self, mock_generate_question):
        mock_generate_question.return_value = ("What is 2 + 2?", "4", "Addition")

        phone_number = "whatsapp:+343434343"
        self.client.post(
            "/whatsapp/",
            {"Body": "practice maths", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "stop", "From": phone_number},
            HTTP_HOST="127.0.0.1",
        )

        self.assertIn("Practice stopped.", response.content.decode())

        progress = UserProgress.objects.get(phone_number=phone_number)
        self.assertFalse(progress.awaiting_practice_answer)

    def test_practice_english_grammar_uses_requested_topic(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "practice english grammar", "From": "whatsapp:+454545454"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode().lower()
        self.assertIn("practice question", body)
        self.assertTrue(
            "subject-verb agreement" in body or "articles" in body or "parts of speech" in body or "sentence correction" in body
        )

    def test_practice_english_passive_voice_uses_requested_topic(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "practice english passive voice", "From": "whatsapp:+565656565"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode().lower()
        self.assertIn("practice question (passive voice", body)
        self.assertIn("passive voice", body)

    def test_english_topics_command_lists_available_topics(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "english topics", "From": "whatsapp:+676767676"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode().lower()
        self.assertIn("english topics:", body)
        self.assertIn("passive voice", body)
        self.assertIn("reported speech", body)
