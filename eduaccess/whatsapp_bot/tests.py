from unittest.mock import patch
import json

from django.contrib.auth.models import User
from django.test import TestCase

from whatsapp_bot.models import UserProgress


class PwaTests(TestCase):
    def test_manifest_is_available(self):
        response = self.client.get("/manifest.json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertContains(response, "EduAccess Offline Library")
        self.assertContains(response, "icon-192.png")
        self.assertContains(response, "icon-512.png")
        self.assertContains(response, "standalone")

    def test_service_worker_is_available(self):
        response = self.client.get("/service-worker.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn("application/javascript", response["Content-Type"])
        self.assertIn("CACHE_NAME", response.content.decode())
        self.assertEqual(response["Service-Worker-Allowed"], "/")

    def test_service_worker_precaches_only_local_pack_resources(self):
        response = self.client.get("/service-worker.js")

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("/packs/maths-algebra-basics/", body)
        self.assertIn("/audio-packs/audio-maths-algebra-basics/player/", body)
        self.assertNotIn("/audio-packs/audio-simultaneous-equations/player/", body)

    def test_offline_library_page_renders_pack_links(self):
        response = self.client.get("/offline-library/")

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("EduAccess Offline Library", body)
        self.assertIn("/packs/simultaneous-equations/", body)
        self.assertIn("/audio-packs/audio-simultaneous-equations/player/", body)

    def test_offline_library_page_renders_pack_links_for_logged_in_user(self):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        response = self.client.get("/offline-library/")

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("EduAccess Offline Library", body)
        self.assertIn('href="/manifest.json"', body)
        self.assertIn("Install EduAccess", body)
        self.assertIn('id="install-status"', body)
        self.assertIn("/study-assistant/", body)
        self.assertIn("/packs/simultaneous-equations/", body)
        self.assertIn("/audio-packs/audio-simultaneous-equations/player/", body)

    def test_study_assistant_page_renders(self):
        response = self.client.get("/study-assistant/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_register_page_creates_user_and_logs_them_in(self):
        response = self.client.post(
            "/register/",
            {
                "username": "student1",
                "email": "student1@example.com",
                "password1": "StrongPass123",
                "password2": "StrongPass123",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/study-assistant/")
        self.assertTrue(User.objects.filter(username="student1").exists())

    def test_login_page_renders(self):
        response = self.client.get("/login/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Welcome back", response.content.decode())

    def test_dashboard_requires_login(self):
        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_dashboard_shows_logged_in_student_progress(self):
        user = User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        UserProgress.objects.get_or_create(user=user)
        progress = user.learning_progress
        progress.correct_answers = 2
        progress.total_attempts = 3
        progress.last_question = (
            '{"pending": {"subject": "maths", "question": "Solve for x: x + 9 = 14", "answer": "x = 5"}, '
            '"subject_stats": {"maths": {"attempts": 2, "correct": 1}, "english": {"attempts": 1, "correct": 1}}, '
            '"recent_questions": {}}'
        )
        progress.save()

        response = self.client.get("/dashboard/")

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("student1", body)
        self.assertIn("learning progress", body)
        self.assertIn("2/3", body)
        self.assertIn("Solve for x: x + 9 = 14", body)
        self.assertIn("Maths", body)
        self.assertIn("English", body)

    @patch("whatsapp_bot.views.generate_question")
    def test_study_assistant_page_handles_practice_english_command(self, mock_generate_question):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_generate_question.return_value = (
            "Write this sentence in the passive voice: The chef cooked the meal.",
            "The meal was cooked by the chef.",
        )

        response = self.client.post(
            "/study-assistant/",
            {"question": "Practice english"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("English Practice Question", body)
        self.assertIn("Reply with your answer and I will mark it", body)
        mock_generate_question.assert_called_once_with(subject="english", exclude_questions=[], topic=None)

    @patch("whatsapp_bot.views.generate_question")
    def test_study_assistant_marks_practice_answer_and_updates_progress(self, mock_generate_question):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_generate_question.return_value = (
            "Write this sentence in the passive voice: The chef cooked the meal.",
            "The meal was cooked by the chef.",
        )

        self.client.post("/study-assistant/", {"question": "Practice english"})
        response = self.client.post(
            "/study-assistant/",
            {"question": "The meal was cooked by the chef."},
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("English Practice Feedback", body)
        self.assertIn("Correct. Well done.", body)
        self.assertIn("Score: 1/1", body)
        self.assertIn("Progress: English grammar practice has started.", body)
        self.assertIn("Covered area focus: sentence structure, grammar, vocabulary, and expression.", body)

    @patch("whatsapp_bot.views.generate_question")
    def test_study_assistant_feedback_uses_subject_score_not_overall_score(self, mock_generate_question):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_generate_question.side_effect = [
            ("Change to passive voice: The chef cooked the meal.", "The meal was cooked by the chef."),
            ("Solve for x: x + 9 = 14", "x = 5"),
            ("Solve for y: 3y = 18", "y = 6"),
        ]

        self.client.post("/study-assistant/", {"question": "Practice english"})
        self.client.post("/study-assistant/", {"question": "The meal was cooked by the chef."})
        self.client.post("/study-assistant/", {"question": "Practice maths"})
        self.client.post("/study-assistant/", {"question": "x = 3"})
        self.client.post("/study-assistant/", {"question": "Practice maths"})
        response = self.client.post("/study-assistant/", {"question": "y = 6"})

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Maths Practice Feedback", body)
        self.assertIn("Score: 1/2", body)
        self.assertNotIn("Score: 2/3", body)

    @patch("whatsapp_bot.views.generate_question")
    def test_study_assistant_avoids_immediate_repeat_for_same_subject(self, mock_generate_question):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_generate_question.side_effect = [
            ("Change to passive voice: The chef cooked the meal.", "The meal was cooked by the chef."),
            ("Change to passive voice: The students solved the problem.", "The problem was solved by the students."),
        ]

        self.client.post("/study-assistant/", {"question": "Practice english"})
        response = self.client.post("/study-assistant/", {"question": "Practice english"})

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("The students solved the problem.", body)
        self.assertEqual(mock_generate_question.call_args_list[0].kwargs, {"subject": "english", "exclude_questions": [], "topic": None})
        self.assertEqual(
            mock_generate_question.call_args_list[1].kwargs,
            {"subject": "english", "exclude_questions": ["Change to passive voice: The chef cooked the meal."], "topic": None},
        )

    @patch("whatsapp_bot.views.generate_question")
    def test_study_assistant_progress_command_shows_running_score(self, mock_generate_question):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_generate_question.return_value = (
            "Solve: 2x = 10",
            "x = 5",
        )

        self.client.post("/study-assistant/", {"question": "Practice maths"})
        self.client.post("/study-assistant/", {"question": "x = 5"})
        response = self.client.post("/study-assistant/", {"question": "progress"})

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Score: 1/1", body)
        self.assertIn("Progress: Learning progress is building.", body)

    @patch("whatsapp_bot.views.generate_question")
    def test_study_assistant_supports_specific_english_topic_choice(self, mock_generate_question):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_generate_question.return_value = (
            "Read the sentence and identify the adjective: The tall tree fell.",
            "tall",
        )

        response = self.client.post("/study-assistant/", {"question": "practice english adjectives"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("English Practice Question", response.content.decode())
        mock_generate_question.assert_called_once_with(subject="english", exclude_questions=[], topic="adjectives")

    @patch("whatsapp_bot.views.ask_ai")
    @patch("whatsapp_bot.views.generate_question")
    def test_new_learning_request_does_not_get_graded_as_pending_practice_answer(
        self,
        mock_generate_question,
        mock_ask_ai,
    ):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_generate_question.return_value = (
            "Differentiate with respect to x: x^2",
            "2x",
        )
        mock_ask_ai.return_value = "Linear equations are equations whose highest power is 1."

        self.client.post("/study-assistant/", {"question": "practice maths calculus"})
        response = self.client.post("/study-assistant/", {"question": "Teach me linear equations"})

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Linear equations are equations whose highest power is 1.", body)
        self.assertNotIn("Maths Practice Feedback", body)

    def test_generate_question_uses_local_reported_speech_bank(self):
        from whatsapp_bot.ai import generate_question

        question, answer = generate_question(subject="english", topic="reported speech")

        self.assertIn("reported speech", question.lower())
        self.assertTrue(answer)

    def test_generate_question_accepts_singular_topic_alias(self):
        from whatsapp_bot.ai import generate_question

        question, answer = generate_question(subject="maths", topic="linear equation")

        self.assertTrue(question)
        self.assertTrue(answer)

    def test_resolve_topic_from_text_maps_noun_to_parts_of_speech(self):
        from whatsapp_bot.ai import resolve_topic_from_text

        subject, topic = resolve_topic_from_text("What is a noun?")

        self.assertEqual(subject, "english")
        self.assertEqual(topic, "parts of speech")

    def test_resolve_topic_from_text_maps_linear_equation_question_correctly(self):
        from whatsapp_bot.ai import resolve_topic_from_text

        subject, topic = resolve_topic_from_text("Please help me solve this linear equation")

        self.assertEqual(subject, "maths")
        self.assertEqual(topic, "linear equations")

    @patch("whatsapp_bot.ai._call_gemini")
    def test_resolve_topic_from_text_uses_gemini_classification_when_valid(self, mock_call_gemini):
        from whatsapp_bot.ai import resolve_topic_from_text

        mock_call_gemini.return_value = (
            '{"subject":"english","topic":"parts of speech","confidence":0.96}'
        )

        subject, topic = resolve_topic_from_text("What is a noun?")

        self.assertEqual(subject, "english")
        self.assertEqual(topic, "parts of speech")

    @patch("whatsapp_bot.ai._call_gemini")
    def test_resolve_topic_from_text_falls_back_when_gemini_is_unavailable(self, mock_call_gemini):
        from whatsapp_bot.ai import resolve_topic_from_text

        mock_call_gemini.side_effect = RuntimeError("Gemini unavailable")

        subject, topic = resolve_topic_from_text("What is a noun?")

        self.assertEqual(subject, "english")
        self.assertEqual(topic, "parts of speech")

    @patch("whatsapp_bot.ai.request.urlopen")
    def test_transcribe_audio_bytes_uses_gemini_response_text(self, mock_urlopen):
        from whatsapp_bot.ai import transcribe_audio_bytes

        mock_response = mock_urlopen.return_value.__enter__.return_value
        mock_response.read.return_value = json.dumps(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "What is a noun?"}
                            ]
                        }
                    }
                ]
            }
        ).encode("utf-8")

        transcript = transcribe_audio_bytes(b"fake-audio", content_type="audio/ogg")

        self.assertEqual(transcript, "What is a noun?")

    @patch("whatsapp_bot.views.generate_question")
    def test_specific_topic_practice_adds_related_download_links(
        self,
        mock_generate_question,
    ):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_generate_question.return_value = (
            "Change to passive voice: The chef cooked the meal.",
            "The meal was cooked by the chef.",
        )

        response = self.client.post(
            "/study-assistant/",
            {"question": "practice english passive voice"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        # passive voice is in LOCAL packs with the english-passive-voice slug
        self.assertIn("/packs/english-passive-voice/", body)
        self.assertIn("/audio-packs/audio-english-passive-voice/player/", body)
        self.assertIn("/audio-packs/audio-english-passive-voice/transcript/", body)

    @patch("whatsapp_bot.views.generate_learning_pack")
    def test_study_assistant_page_handles_pack_command(self, mock_generate_learning_pack):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_generate_learning_pack.return_value = {
            "slug": "algebra",
            "subject": "maths",
            "topic": "Algebra",
            "title": "Algebra Pack",
            "summary": "Rich algebra revision content.",
            "content": "ALGEBRA CONTENT",
        }
        response = self.client.post(
            "/study-assistant/",
            {"question": "pack algebra"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Algebra Pack", body)
        self.assertIn("/packs/algebra/", body)
        self.assertIn('href="http://127.0.0.1/packs/algebra/"', body)
        mock_generate_learning_pack.assert_called_once()
        self.assertEqual(mock_generate_learning_pack.call_args[0][0], "algebra")

    @patch("whatsapp_bot.views.ask_ai")
    def test_study_assistant_page_uses_ai_for_normal_question(self, mock_ask_ai):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_ask_ai.return_value = "Algebra uses letters to represent unknown values."

        response = self.client.post(
            "/study-assistant/",
            {"question": "Explain algebra"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Algebra uses letters to represent unknown values.", response.content.decode())
        mock_ask_ai.assert_called_once()
        self.assertEqual(mock_ask_ai.call_args[0][0], "Explain algebra")

    @patch("whatsapp_bot.views.ask_ai")
    def test_ai_answer_includes_topic_specific_resources_for_derivative_question(self, mock_ask_ai):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_ask_ai.return_value = "A derivative measures rate of change."

        response = self.client.post(
            "/study-assistant/",
            {"question": "What is a derivative?"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("A derivative measures rate of change.", body)
        self.assertIn("/packs/calculus/", body)
        self.assertIn("/audio-packs/audio-calculus/player/", body)

    def test_study_assistant_page_greeting_shows_capabilities(self):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")

        response = self.client.post(
            "/study-assistant/",
            {"question": "Hello"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("I can help you with", body)
        self.assertIn("practice maths", body)
        self.assertIn("practice english", body)

    def test_study_assistant_returns_scope_message_for_biology_question(self):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")

        response = self.client.post(
            "/study-assistant/",
            {"question": "Explain biology cell division"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("This application only answers Maths and English questions for now.", body)
        self.assertIn("It will be upgraded later on. Thank you.", body)

    def test_study_assistant_returns_scope_message_for_photosynthesis_variant(self):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")

        response = self.client.post(
            "/study-assistant/",
            {"question": "what is photosynthess"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("This application only answers Maths and English questions for now.", body)
        self.assertIn("It will be upgraded later on. Thank you.", body)

    def test_study_assistant_solves_raw_linear_equation(self):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")

        response = self.client.post(
            "/study-assistant/",
            {"question": "5x=3x-4"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Linear equation solution", body)
        self.assertIn("Answer: x = -2", body)
        self.assertIn("/packs/linear-equations/", body)

    def test_study_assistant_solves_quadratic_equation(self):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")

        response = self.client.post(
            "/study-assistant/",
            {"question": "2x^2-4=16"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Quadratic equation solution", body)
        self.assertIn("Answer: x = 3.162278 or x = -3.162278", body)
        self.assertIn("/packs/quadratic-equations/", body)

    @patch("whatsapp_bot.views.generate_question")
    def test_new_linear_equation_question_is_not_graded_as_pending_practice_answer(self, mock_generate_question):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_generate_question.return_value = (
            "Solve for x: x + 9 = 14",
            "x = 5",
        )

        self.client.post("/study-assistant/", {"question": "Practice maths"})
        response = self.client.post(
            "/study-assistant/",
            {"question": "5x=3x-4"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Linear equation solution", body)
        self.assertNotIn("Maths Practice Feedback", body)

    @patch("whatsapp_bot.views.ask_ai")
    def test_topic_based_normal_question_adds_resource_links(
        self,
        mock_ask_ai,
    ):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_ask_ai.return_value = "Linear equations help us solve for unknown values."

        response = self.client.post(
            "/study-assistant/",
            {"question": "Teach me linear equations"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Linear equations help us solve for unknown values.", body)
        self.assertIn("/packs/linear-equations/", body)
        self.assertIn("/audio-packs/audio-linear-equations/player/", body)
        self.assertIn("/audio-packs/audio-linear-equations/transcript/", body)

    @patch("whatsapp_bot.views.ask_ai")
    def test_topic_based_normal_question_uses_topic_fallback_when_ai_fails(
        self,
        mock_ask_ai,
    ):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_ask_ai.side_effect = RuntimeError("AI unavailable")

        response = self.client.post(
            "/study-assistant/",
            {"question": "Teach me linear equations"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("linear equation", body.lower())
        self.assertIn("Study Pack:", body)
        self.assertIn("/packs/linear-equations/", body)

    @patch("whatsapp_bot.views.ask_ai")
    def test_normal_maths_question_uses_local_fallback_when_ai_fails(self, mock_ask_ai):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_ask_ai.side_effect = RuntimeError("AI unavailable")

        response = self.client.post(
            "/study-assistant/",
            {"question": "What is a derivative?"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Differentiation finds the rate", body)
        self.assertIn("/audio-packs/audio-calculus/player/", body)
        self.assertNotIn("couldn't process your request right now", body)

    @patch("whatsapp_bot.views.get_or_generate_audio_pack")
    @patch("whatsapp_bot.views.get_or_generate_learning_pack")
    def test_offline_library_shows_recent_topic_from_normal_chat(
        self,
        mock_get_or_generate_learning_pack,
        mock_get_or_generate_audio_pack,
    ):
        user = User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        UserProgress.objects.get_or_create(user=user)
        mock_get_or_generate_learning_pack.return_value = {
            "slug": "linear-equations",
            "subject": "maths",
            "topic": "Linear Equations",
            "title": "Linear Equations Pack",
            "summary": "Detailed pack",
            "content": "CONTENT",
        }
        mock_get_or_generate_audio_pack.return_value = {
            "slug": "audio-linear-equations",
            "subject": "maths",
            "topic": "Linear Equations",
            "title": "Linear Equations Audio Lesson",
            "summary": "Detailed audio",
            "transcript": "TRANSCRIPT",
        }

        session = self.client.session
        session["study_assistant_history"] = [
            {"role": "student", "text": "Teach me linear equations"},
            {"role": "assistant", "text": "Linear equations help us solve for unknown values."},
        ]
        session.save()

        progress = user.learning_progress
        progress.last_question = (
            '{"pending": null, "subject_stats": {}, "recent_questions": {}, '
            '"recent_topics": [{"topic": "linear equations", "subject": "maths", "normalized": "linear equations"}]}'
        )
        progress.save()

        response = self.client.get("/offline-library/")

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Linear Equations", body)
        self.assertIn("Recent Topic", body)
        self.assertIn("/packs/linear-equations/", body)

    @patch("whatsapp_bot.views.get_or_generate_audio_pack")
    @patch("whatsapp_bot.views.get_or_generate_learning_pack")
    def test_offline_library_shows_recent_adjectives_topic(
        self,
        mock_get_or_generate_learning_pack,
        mock_get_or_generate_audio_pack,
    ):
        user = User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        UserProgress.objects.get_or_create(user=user)
        mock_get_or_generate_learning_pack.return_value = {
            "slug": "adjectives",
            "subject": "english",
            "topic": "Adjectives",
            "title": "Adjectives Pack",
            "summary": "Adjectives pack",
            "content": "CONTENT",
        }
        mock_get_or_generate_audio_pack.return_value = {
            "slug": "audio-adjectives",
            "subject": "english",
            "topic": "Adjectives",
            "title": "Adjectives Audio Lesson",
            "summary": "Adjectives audio",
            "transcript": "TRANSCRIPT",
        }

        progress = user.learning_progress
        progress.last_question = (
            '{"pending": null, "subject_stats": {}, "recent_questions": {}, '
            '"recent_topics": [{"topic": "adjectives", "subject": "english", "normalized": "adjectives"}]}'
        )
        progress.save()

        response = self.client.get("/offline-library/")

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Adjectives", body)
        self.assertIn("/packs/adjectives/", body)
        self.assertIn("/audio-packs/audio-adjectives/player/", body)

    @patch("whatsapp_bot.views.get_audio_pack_by_slug_or_topic")
    @patch("whatsapp_bot.views.get_learning_pack_by_slug_or_topic")
    @patch("whatsapp_bot.views.get_or_generate_audio_pack")
    @patch("whatsapp_bot.views.get_or_generate_learning_pack")
    def test_offline_library_does_not_generate_recent_topic_resources_synchronously(
        self,
        mock_get_or_generate_learning_pack,
        mock_get_or_generate_audio_pack,
        mock_get_learning_pack_by_slug_or_topic,
        mock_get_audio_pack_by_slug_or_topic,
    ):
        user = User.objects.create_user(username="student_timeout", password="StrongPass123")
        self.client.login(username="student_timeout", password="StrongPass123")
        UserProgress.objects.get_or_create(user=user)

        progress = user.learning_progress
        progress.last_question = (
            '{"pending": null, "subject_stats": {}, "recent_questions": {}, '
            '"recent_topics": [{"topic": "novel topic", "subject": "maths", "normalized": "novel topic"}]}'
        )
        progress.save()

        mock_get_learning_pack_by_slug_or_topic.return_value = None
        mock_get_audio_pack_by_slug_or_topic.return_value = None

        response = self.client.get("/offline-library/")

        self.assertEqual(response.status_code, 200)
        mock_get_or_generate_learning_pack.assert_not_called()
        mock_get_or_generate_audio_pack.assert_not_called()

    @patch("whatsapp_bot.views.generate_audio_pack")
    def test_study_assistant_api_returns_audio_pack_reply(self, mock_generate_audio_pack):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        mock_generate_audio_pack.return_value = {
            "slug": "audio-passive-voice",
            "subject": "english",
            "topic": "Passive Voice",
            "title": "Passive Voice Audio Lesson",
            "summary": "Detailed audio lesson.",
            "transcript": "TRANSCRIPT",
        }
        response = self.client.post(
            "/study-assistant/api/",
            data='{"question": "audio pack passive voice"}',
            content_type="application/json",
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Passive Voice Audio Lesson", response.json()["reply"])
        self.assertIn("/audio-packs/audio-passive-voice/player/", response.json()["reply"])
        mock_generate_audio_pack.assert_called_once()
        self.assertEqual(mock_generate_audio_pack.call_args[0][0], "Passive Voice")

    def test_offline_fallback_page_renders(self):
        response = self.client.get("/offline-fallback/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You are offline")

    def test_study_assistant_routes_to_offline_library_for_library_command(self):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")

        response = self.client.post("/study-assistant/", {"question": "offline library"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/offline-library/")

    def test_learning_pack_download_returns_text(self):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        response = self.client.get("/packs/english-passive-voice/", HTTP_HOST="127.0.0.1")

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])
        body = response.content.decode()
        self.assertIn("PASSIVE VOICE", body)
        self.assertIn("COMMON MISTAKES", body)

    def test_algebra_pack_download_contains_fuller_lesson_content(self):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        response = self.client.get("/packs/maths-algebra-basics/", HTTP_HOST="127.0.0.1")

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("ALGEBRA", body)
        self.assertIn("COMMON MISTAKES", body)
        self.assertIn("WORKED EXAMPLE", body)

    def test_audio_player_page_contains_speech_synthesis(self):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        response = self.client.get("/audio-packs/audio-english-passive-voice/player/")

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Play Audio Lesson", body)
        self.assertIn("speechSynthesis", body)

    def test_audio_transcript_download_returns_text(self):
        User.objects.create_user(username="student1", password="StrongPass123")
        self.client.login(username="student1", password="StrongPass123")
        response = self.client.get("/audio-packs/audio-english-passive-voice/transcript/", HTTP_HOST="127.0.0.1")

        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("passive voice", response.content.decode().lower())


class WhatsAppWebhookTests(TestCase):
    def test_greeting_returns_capabilities_message(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "Hi", "From": "whatsapp:+111111111"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("I can help you with", body)
        self.assertIn("practice maths", body)
        self.assertIn("practice english", body)

    @patch("whatsapp_bot.views.ask_ai")
    def test_normal_message_uses_ai(self, mock_ask_ai):
        mock_ask_ai.return_value = "Derivative means rate of change."

        response = self.client.post(
            "/whatsapp/",
            {"Body": "What is a derivative?", "From": "whatsapp:+333333333"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Derivative means rate of change.", response.content.decode())
        mock_ask_ai.assert_called_once()
        self.assertEqual(mock_ask_ai.call_args[0][0], "What is a derivative?")

    @patch("whatsapp_bot.views.ask_ai")
    def test_normal_message_uses_local_fallback_when_ai_fails(self, mock_ask_ai):
        mock_ask_ai.side_effect = RuntimeError("AI unavailable")

        response = self.client.post(
            "/whatsapp/",
            {"Body": "What is a derivative?", "From": "whatsapp:+333333333"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Differentiation finds the rate", body)
        self.assertIn("/packs/calculus/", body)

    def test_offline_library_command_returns_link(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "offline library", "From": "whatsapp:+111111111"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("/offline-library/", response.content.decode())

    def test_out_of_scope_question_returns_scope_message(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "What is photosynthesis in biology?", "From": "whatsapp:+111111111"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("This application only answers Maths and English questions for now.", body)
        self.assertIn("It will be upgraded later on. Thank you.", body)

    def test_photosynthesis_variant_returns_scope_message(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "what is photosynthess", "From": "whatsapp:+111111111"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("This application only answers Maths and English questions for now.", body)
        self.assertIn("It will be upgraded later on. Thank you.", body)

    @patch("whatsapp_bot.views.ask_ai")
    @patch("whatsapp_bot.views.transcribe_whatsapp_audio")
    def test_audio_question_is_transcribed_and_answered(self, mock_transcribe_whatsapp_audio, mock_ask_ai):
        mock_transcribe_whatsapp_audio.return_value = "What is a noun?"
        mock_ask_ai.return_value = "A noun is a naming word."

        response = self.client.post(
            "/whatsapp/",
            {
                "Body": "",
                "From": "whatsapp:+111111111",
                "NumMedia": "1",
                "MediaUrl0": "https://example.com/audio.ogg",
                "MediaContentType0": "audio/ogg",
            },
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("A noun is a naming word.", response.content.decode())
        mock_transcribe_whatsapp_audio.assert_called_once_with(
            "https://example.com/audio.ogg",
            content_type="audio/ogg",
        )
        mock_ask_ai.assert_called_once()
        self.assertEqual(mock_ask_ai.call_args[0][0], "What is a noun?")

    @patch("whatsapp_bot.views.transcribe_whatsapp_audio")
    def test_audio_question_with_codec_content_type_is_processed(self, mock_transcribe_whatsapp_audio):
        mock_transcribe_whatsapp_audio.return_value = "2x^2-4=16"

        response = self.client.post(
            "/whatsapp/",
            {
                "Body": "",
                "From": "whatsapp:+111111111",
                "NumMedia": "1",
                "MediaUrl0": "https://example.com/audio.ogg",
                "MediaContentType0": "audio/ogg; codecs=opus",
            },
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("Quadratic equation solution", body)
        self.assertIn("Answer: x = 3.162278 or x = -3.162278", body)
        mock_transcribe_whatsapp_audio.assert_called_once_with(
            "https://example.com/audio.ogg",
            content_type="audio/ogg; codecs=opus",
        )

    @patch("whatsapp_bot.views.transcribe_whatsapp_audio")
    def test_audio_transcription_failure_returns_retry_message(self, mock_transcribe_whatsapp_audio):
        mock_transcribe_whatsapp_audio.side_effect = RuntimeError("transcription failed")

        response = self.client.post(
            "/whatsapp/",
            {
                "Body": "",
                "From": "whatsapp:+111111111",
                "NumMedia": "1",
                "MediaUrl0": "https://example.com/audio.ogg",
                "MediaContentType0": "audio/ogg; codecs=opus",
            },
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("I could not transcribe your audio just now", response.content.decode())

    def test_empty_message_without_text_or_audio_prompts_for_supported_input(self):
        response = self.client.post(
            "/whatsapp/",
            {"Body": "", "From": "whatsapp:+111111111", "NumMedia": "0"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Please send a text or audio question", response.content.decode())


# ---------------------------------------------------------------------------
# Phase 4 — Failure Scenario Tests
# ---------------------------------------------------------------------------

class FailureScenarioTests(TestCase):
    """
    Scenario 1 — Worker timeout: _build_topic_resource_lines must never block
    on unknown topics. It should return "" immediately and fire a background
    thread for generation instead of calling Gemini synchronously.
    """

    def test_topic_resource_lines_returns_empty_for_unknown_topic_without_blocking(self):
        from unittest.mock import patch as mock_patch
        import threading
        from django.test import RequestFactory
        from whatsapp_bot.views import _build_topic_resource_lines

        factory = RequestFactory()
        request = factory.get("/", HTTP_HOST="127.0.0.1")

        threads_started = []
        original_start = threading.Thread.start

        def track_start(self_thread):
            threads_started.append(True)
            original_start(self_thread)

        with mock_patch.object(threading.Thread, "start", track_start):
            result = _build_topic_resource_lines(request, "maths", "unknown-novel-topic")

        self.assertEqual(result, "")
        self.assertTrue(threads_started, "Should have launched a background thread for generation")

    def test_topic_resource_lines_returns_links_for_known_local_pack(self):
        from django.test import RequestFactory
        from whatsapp_bot.views import _build_topic_resource_lines

        factory = RequestFactory()
        request = factory.get("/", HTTP_HOST="127.0.0.1")

        result = _build_topic_resource_lines(request, "maths", "linear equations")

        self.assertIn("/packs/linear-equations/", result)
        self.assertIn("/audio-packs/audio-linear-equations/player/", result)

    """
    Scenario 2 — Corrupted practice state: if the database stores invalid JSON
    in UserProgress.last_question, the bot must recover gracefully rather than
    crashing with a JSONDecodeError.
    """

    def test_study_assistant_recovers_from_corrupted_practice_state(self):
        user = User.objects.create_user(username="student_corrupt", password="StrongPass123")
        self.client.login(username="student_corrupt", password="StrongPass123")
        UserProgress.objects.get_or_create(user=user)
        progress = user.learning_progress
        progress.last_question = "THIS IS NOT VALID JSON {{{"
        progress.save()

        response = self.client.post(
            "/study-assistant/",
            {"question": "Hello"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("I can help you with", body)

    def test_whatsapp_webhook_recovers_from_corrupted_practice_state(self):
        from whatsapp_bot.models import UserProgress as UP

        UP.objects.create(phone_number="+123456789", last_question="INVALID{{{")

        response = self.client.post(
            "/whatsapp/",
            {"Body": "Hello", "From": "whatsapp:+123456789"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("I can help you with", response.content.decode())

    """
    Scenario 3 — Edge-case inputs: the study assistant must handle blank
    questions, whitespace-only input, and very long input gracefully.
    """

    def test_study_assistant_ignores_whitespace_only_question(self):
        User.objects.create_user(username="student_ws", password="StrongPass123")
        self.client.login(username="student_ws", password="StrongPass123")

        response = self.client.post(
            "/study-assistant/",
            {"question": "   "},
        )

        # Whitespace is stripped to empty — no reply is generated, page just reloads
        self.assertEqual(response.status_code, 200)

    def test_study_assistant_api_rejects_missing_question(self):
        User.objects.create_user(username="student_api", password="StrongPass123")
        self.client.login(username="student_api", password="StrongPass123")

        response = self.client.post(
            "/study-assistant/api/",
            data="{}",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("required", response.json()["detail"].lower())

    def test_study_assistant_api_rejects_malformed_json(self):
        User.objects.create_user(username="student_bad", password="StrongPass123")
        self.client.login(username="student_bad", password="StrongPass123")

        response = self.client.post(
            "/study-assistant/api/",
            data="not-json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    @patch("whatsapp_bot.views.generate_question")
    def test_practice_english_command_returns_question(self, mock_generate_question):
        mock_generate_question.return_value = (
            "Change this sentence to passive voice: The students completed the work.",
            "The work was completed by the students.",
        )

        response = self.client.post(
            "/whatsapp/",
            {"Body": "Practice english", "From": "whatsapp:+111111111"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("English Practice Question", response.content.decode())
        self.assertIn("Reply with your answer and I will mark it", response.content.decode())
        mock_generate_question.assert_called_once_with(subject="english", exclude_questions=[], topic=None)

    @patch("whatsapp_bot.views.generate_question")
    def test_whatsapp_practice_answer_returns_feedback_and_score(self, mock_generate_question):
        mock_generate_question.return_value = (
            "Change this sentence to passive voice: The students completed the work.",
            "The work was completed by the students.",
        )

        self.client.post(
            "/whatsapp/",
            {"Body": "Practice english", "From": "whatsapp:+111111111"},
            HTTP_HOST="127.0.0.1",
        )
        response = self.client.post(
            "/whatsapp/",
            {"Body": "The work was completed by the students.", "From": "whatsapp:+111111111"},
            HTTP_HOST="127.0.0.1",
        )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("English Practice Feedback", body)
        self.assertIn("Correct. Well done.", body)
        self.assertIn("Score: 1/1", body)
        self.assertIn("Covered area focus: sentence structure, grammar, vocabulary, and expression.", body)
