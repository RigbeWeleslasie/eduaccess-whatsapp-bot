# eduaccess/whatsapp/views.py
import json
import re
import threading
import traceback

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.messaging_response import MessagingResponse

from .forms import EduAccessAuthenticationForm, EduAccessUserCreationForm
from .models import UserProgress
from .ai import (
    ask_ai,
    build_local_tutor_answer,
    is_sentence_analysis_question,
    generate_audio_pack,
    get_audio_pack_by_slug_or_topic,
    get_audio_packs,
    generate_learning_pack,
    generate_question,
    get_or_generate_audio_pack,
    get_or_generate_learning_pack,
    get_learning_pack_by_slug_or_topic,
    get_learning_packs,
    get_supported_topics,
    looks_like_linear_equation_question,
    looks_like_quadratic_equation_question,
    resolve_topic_from_text,
    solve_linear_equation,
    solve_quadratic_equation,
    transcribe_whatsapp_audio,
)


def _get_request_base_url(request):
    return f"{request.scheme}://{request.get_host()}"


def _topic_to_slug(topic):
    return re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-") or "study-topic"


def _topic_to_title(topic):
    return " ".join(word.capitalize() for word in re.sub(r"[-_]+", " ", topic).split())


def _normalize_whatsapp_sender(raw_sender):
    sender = (raw_sender or "").strip()
    if sender.startswith("whatsapp:"):
        sender = sender.split(":", 1)[1]
    return sender or "unknown"


def _empty_practice_state():
    return {
        "pending": None,
        "correct_answers": 0,
        "total_attempts": 0,
        "subject_stats": {},
        "recent_questions": {},
        "recent_topics": [],
    }


def _load_session_practice_state(request):
    state = request.session.get("study_assistant_practice")
    if not isinstance(state, dict):
        return _empty_practice_state()
    return {
        "pending": state.get("pending"),
        "correct_answers": int(state.get("correct_answers", 0)),
        "total_attempts": int(state.get("total_attempts", 0)),
        "subject_stats": state.get("subject_stats", {}) if isinstance(state.get("subject_stats", {}), dict) else {},
        "recent_questions": state.get("recent_questions", {}) if isinstance(state.get("recent_questions", {}), dict) else {},
        "recent_topics": state.get("recent_topics", []) if isinstance(state.get("recent_topics", []), list) else [],
    }


def _save_session_practice_state(request, state):
    request.session["study_assistant_practice"] = state


def _clear_session_practice_state(request):
    request.session.pop("study_assistant_practice", None)


def _load_user_practice_state(user):
    progress, _ = UserProgress.objects.get_or_create(user=user)
    state = _empty_practice_state()
    state["correct_answers"] = progress.correct_answers
    state["total_attempts"] = progress.total_attempts

    if progress.last_question:
        try:
            saved_state = json.loads(progress.last_question)
        except json.JSONDecodeError:
            saved_state = None
        if isinstance(saved_state, dict):
            state["pending"] = saved_state.get("pending")
            state["subject_stats"] = (
                saved_state.get("subject_stats", {})
                if isinstance(saved_state.get("subject_stats", {}), dict)
                else {}
            )
            state["recent_questions"] = (
                saved_state.get("recent_questions", {})
                if isinstance(saved_state.get("recent_questions", {}), dict)
                else {}
            )
            state["recent_topics"] = (
                saved_state.get("recent_topics", [])
                if isinstance(saved_state.get("recent_topics", []), list)
                else []
            )

    return progress, state


def _save_user_practice_state(progress, state):
    progress.correct_answers = state["correct_answers"]
    progress.total_attempts = state["total_attempts"]
    payload = {
        "pending": state.get("pending"),
        "subject_stats": state.get("subject_stats", {}),
        "recent_questions": state.get("recent_questions", {}),
        "recent_topics": state.get("recent_topics", []),
    }
    progress.last_question = json.dumps(payload) if any(
        [payload["pending"], payload["subject_stats"], payload["recent_topics"]]
    ) else ""
    progress.save(update_fields=["correct_answers", "total_attempts", "last_question"])


def _load_whatsapp_practice_state(phone_number):
    progress, _ = UserProgress.objects.get_or_create(phone_number=phone_number)
    state = _empty_practice_state()
    state["correct_answers"] = progress.correct_answers
    state["total_attempts"] = progress.total_attempts

    if progress.last_question:
        try:
            saved_state = json.loads(progress.last_question)
        except json.JSONDecodeError:
            saved_state = None
        if isinstance(saved_state, dict):
            if "pending" in saved_state or "subject_stats" in saved_state:
                state["pending"] = saved_state.get("pending")
                state["subject_stats"] = (
                    saved_state.get("subject_stats", {})
                    if isinstance(saved_state.get("subject_stats", {}), dict)
                    else {}
                )
                state["recent_questions"] = (
                    saved_state.get("recent_questions", {})
                    if isinstance(saved_state.get("recent_questions", {}), dict)
                    else {}
                )
                state["recent_topics"] = (
                    saved_state.get("recent_topics", [])
                    if isinstance(saved_state.get("recent_topics", []), list)
                    else []
                )
            else:
                state["pending"] = saved_state

    return progress, state


def _save_whatsapp_practice_state(progress, state):
    progress.correct_answers = state["correct_answers"]
    progress.total_attempts = state["total_attempts"]
    payload = {
        "pending": state.get("pending"),
        "subject_stats": state.get("subject_stats", {}),
        "recent_questions": state.get("recent_questions", {}),
        "recent_topics": state.get("recent_topics", []),
    }
    progress.last_question = json.dumps(payload) if any(
        [payload["pending"], payload["subject_stats"], payload["recent_topics"]]
    ) else ""
    progress.save(update_fields=["correct_answers", "total_attempts", "last_question"])


def _remember_topic(state, topic, subject=None):
    if not topic:
        return

    cleaned_topic = topic.strip()
    if not cleaned_topic:
        return

    recent_topics = state.setdefault("recent_topics", [])
    normalized_topic = cleaned_topic.lower()
    updated_topics = [
        item for item in recent_topics
        if isinstance(item, dict) and item.get("normalized") != normalized_topic
    ]
    updated_topics.insert(
        0,
        {
            "topic": cleaned_topic,
            "subject": subject or "general",
            "normalized": normalized_topic,
        },
    )
    state["recent_topics"] = updated_topics[:6]


def _normalize_answer_text(text):
    text = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return " ".join(text.split())


def _clean_display_text(text):
    cleaned = text.replace("**", "")
    cleaned = cleaned.replace("$", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _answers_match(student_answer, expected_answer):
    student_normalized = _normalize_answer_text(student_answer)
    expected_normalized = _normalize_answer_text(expected_answer)

    if not student_normalized or not expected_normalized:
        return False

    if student_normalized == expected_normalized:
        return True

    if student_normalized in expected_normalized or expected_normalized in student_normalized:
        return True

    expected_words = set(expected_normalized.split())
    student_words = set(student_normalized.split())
    if expected_words and len(expected_words & student_words) >= max(2, len(expected_words) - 1):
        return True

    return False


def _looks_like_new_learning_request(message):
    normalized = message.strip().lower()
    if not normalized:
        return False

    request_starters = (
        "teach me",
        "explain",
        "help me",
        "what is",
        "how do",
        "show me",
        "tell me about",
        "give me notes",
        "give me a note",
        "lesson on",
        "topic:",
        "pack ",
        "audio pack ",
        "practice ",
    )
    return normalized.startswith(request_starters)


def _unsupported_subject_reply():
    return (
        "This application only answers Maths and English questions for now. "
        "It will be upgraded later on. Thank you."
    )


def _is_out_of_scope_question(message):
    normalized = re.sub(r"\s+", " ", (message or "").strip().lower())
    if not normalized:
        return False

    unsupported_subject_keywords = (
        "biology",
        "chemistry",
        "physics",
        "history",
        "geography",
        "civics",
        "economics",
        "commerce",
        "agriculture",
        "kiswahili",
        "swahili",
        "computer studies",
        "computer science",
        "religious education",
        "cre",
        "ire",
        "photosynth",
        "cell division",
        "ecosystem",
        "atom",
        "molecule",
        "electricity",
        "newton",
        "acid",
        "base",
        "map reading",
    )

    return any(keyword in normalized for keyword in unsupported_subject_keywords)


def _format_score(state, subject=None):
    if subject:
        current = state.get("subject_stats", {}).get(subject, {"attempts": 0, "correct": 0})
        return f"Score: {int(current.get('correct', 0))}/{int(current.get('attempts', 0))}"

    total = state["total_attempts"]
    correct = state["correct_answers"]
    return f"Score: {correct}/{total}"


def _update_subject_stats(state, subject, is_correct):
    if not subject:
        return
    subject_stats = state.setdefault("subject_stats", {})
    current = subject_stats.get(subject, {"attempts": 0, "correct": 0})
    current["attempts"] = int(current.get("attempts", 0)) + 1
    current["correct"] = int(current.get("correct", 0)) + (1 if is_correct else 0)
    subject_stats[subject] = current


def _format_learning_progress(state, subject=None):
    subject = subject or "general"
    subject_stats = state.get("subject_stats", {})
    current = subject_stats.get(subject, {"attempts": 0, "correct": 0})
    attempts = int(current.get("attempts", 0))
    correct = int(current.get("correct", 0))

    if subject == "maths":
        focus = "variables, equations, balancing steps, and problem solving"
        if attempts <= 1:
            stage = "Maths foundations started."
        elif attempts <= 3:
            stage = "Maths foundations are building well."
        else:
            stage = "Maths understanding is growing across the covered area."
    elif subject == "english":
        focus = "sentence structure, grammar, vocabulary, and expression"
        if attempts <= 1:
            stage = "English grammar practice has started."
        elif attempts <= 3:
            stage = "English grammar understanding is building well."
        else:
            stage = "English learning progress is growing across the covered area."
    else:
        focus = "the covered learning area"
        stage = "Learning progress is building."

    return (
        f"Progress: {stage} Covered area focus: {focus}. "
        f"You have practised {attempts} {subject} question{'s' if attempts != 1 else ''} and answered {correct} correctly in this area."
    )


def _build_dashboard_summary(state):
    subject_stats = state.get("subject_stats", {})
    subjects = []
    for subject in ("maths", "english"):
        current = subject_stats.get(subject, {"attempts": 0, "correct": 0})
        attempts = int(current.get("attempts", 0))
        correct = int(current.get("correct", 0))
        subjects.append(
            {
                "name": subject.title(),
                "attempts": attempts,
                "correct": correct,
                "progress_text": _format_learning_progress(state, subject),
            }
        )

    pending = state.get("pending")
    return {
        "overall_score": _format_score(state),
        "subjects": subjects,
        "pending_question": pending.get("question") if isinstance(pending, dict) else None,
        "pending_subject": pending.get("subject", "general").title() if isinstance(pending, dict) and pending.get("subject") else None,
        "total_attempts": state.get("total_attempts", 0),
    }


def _build_topic_resource_lines(request, subject, topic):
    if not topic:
        return ""

    learning_pack = get_learning_pack_by_slug_or_topic(topic, subject=subject)
    audio_pack = get_audio_pack_by_slug_or_topic(topic, subject=subject)

    if not learning_pack or not audio_pack:
        # Generate missing packs in the background so future requests are served from cache
        def _generate_in_background():
            try:
                if not learning_pack:
                    get_or_generate_learning_pack(topic, subject=subject)
                if not audio_pack:
                    get_or_generate_audio_pack(topic, subject=subject)
            except Exception:
                pass

        threading.Thread(target=_generate_in_background, daemon=True).start()
        return ""

    base_url = _get_request_base_url(request)
    return (
        "\n\nTopic Resources\n"
        f"Study Pack: {base_url}/packs/{learning_pack['slug']}/\n"
        f"Audio Lesson: {base_url}/audio-packs/{audio_pack['slug']}/player/\n"
        f"Transcript: {base_url}/audio-packs/{audio_pack['slug']}/transcript/"
    )


def _build_topic_study_fallback(request, subject, topic):
    topic_title = topic.title()
    subject_label = subject.title() if subject else "Study"

    try:
        resource_lines = _build_topic_resource_lines(request, subject, topic)
    except Exception:
        resource_lines = f"\n\nYou can still explore related materials here: {_get_request_base_url(request)}/offline-library/"

    if subject == "maths":
        explanation = (
            f"{topic_title} is part of {subject_label}. Focus on the rule, work through one example slowly, "
            "and then solve a few short questions step by step. Keep your working clear, check each step, and "
            "look for the operation or relationship that controls the problem."
        )
    elif subject == "english":
        explanation = (
            f"{topic_title} is part of {subject_label}. Focus on the meaning, the language pattern, and how the rule "
            "works in a full sentence. Study a few examples, notice common mistakes, and then practise writing your own answers."
        )
    else:
        explanation = (
            f"{topic_title} is an important study topic. Start with the main idea, read one worked example carefully, "
            "and then try a few practice questions before checking the answers."
        )

    return f"{topic_title}\n{explanation}{resource_lines}"


def _detect_study_topic(message):
    return resolve_topic_from_text(message)


def _resolve_resource_topic(message):
    if looks_like_linear_equation_question(message):
        return "maths", "linear equations"

    if looks_like_quadratic_equation_question(message):
        return "maths", "quadratic equations"

    inferred_subject, inferred_topic = _detect_study_topic(message)
    if inferred_topic:
        return inferred_subject, inferred_topic

    local_answer = build_local_tutor_answer(message)
    if local_answer:
        local_subject = local_answer.get("subject")
        local_topic = local_answer.get("topic")
        if local_subject in {"maths", "english"} and local_topic:
            return local_subject, local_topic

    return None, None


def _build_practice_question_reply(request, state, subject):
    topic = None
    if isinstance(subject, tuple):
        subject, topic = subject

    if subject and subject not in {"english", "maths"}:
        return "I can create practice questions for English or Maths. Try 'practice english' or 'practice maths'."

    recent_questions = state.setdefault("recent_questions", {})
    subject_key = f"{subject}:{topic}" if topic else (subject or "general")
    question, answer = generate_question(
        subject=subject,
        exclude_questions=recent_questions.get(subject_key, []),
        topic=topic,
    )
    recent_questions[subject_key] = [question, *recent_questions.get(subject_key, [])][:3]
    state["pending"] = {
        "subject": subject,
        "topic": topic,
        "question": question,
        "answer": _clean_display_text(answer),
    }
    _remember_topic(state, topic, subject)

    subject_label = f"{subject.title()} " if subject else ""
    topic_resource_lines = _build_topic_resource_lines(request, subject, topic)
    return (
        f"{subject_label}Practice Question\n"
        f"{question}\n\n"
        "Reply with your answer and I will mark it, give feedback, and update your score."
        f"{topic_resource_lines}"
    )


def _build_practice_feedback_reply(state, student_answer):
    pending = state.get("pending")
    if not pending:
        return None

    expected_answer = pending.get("answer", "")
    is_correct = _answers_match(student_answer, expected_answer)
    state["total_attempts"] += 1
    if is_correct:
        state["correct_answers"] += 1

    subject = pending.get("subject")
    _update_subject_stats(state, subject, is_correct)
    subject_label = subject.title() if subject else "General"
    state["pending"] = None

    if is_correct:
        feedback = "Correct. Well done."
    else:
        feedback = (
            "Not quite.\n"
            f"Correct answer: {_clean_display_text(expected_answer)}"
        )

    return (
        f"{subject_label} Practice Feedback\n"
        f"{feedback}\n\n"
        f"{_format_score(state, subject)}\n"
        f"{_format_learning_progress(state, subject)}\n"
        "Send 'practice english' or 'practice maths' for another question."
    )


def _build_welcome_reply(request):
    return (
        "Welcome to *EduAccess* \U0001f393\n\n"
        "I am your personal study tutor for Maths and English.\n\n"
        "Here is what you can do:\n\n"
        "*Practice*\n"
        "- practice maths\n"
        "- practice english\n\n"
        "*Ask the tutor*\n"
        "- Explain algebra\n"
        "- What is passive voice?\n"
        "- Solve 2x + 5 = 11\n\n"
        "*Study packs (download & read offline)*\n"
        "- pack algebra\n"
        "- pack passive voice\n\n"
        "*Audio lessons (listen offline)*\n"
        "- audio pack algebra\n\n"
        "*Your progress*\n"
        "- score\n\n"
        f"Open the web app: {_get_request_base_url(request)}/\n\n"
        "Just send a message to get started \u2728"
    )


def _build_greeting_reply(request):
    return (
        "Hi! \U0001f44b I am your EduAccess tutor.\n\n"
        "I can help you with *Maths* and *English*.\n\n"
        "Try one of these:\n"
        "- practice maths\n"
        "- practice english\n"
        "- Explain fractions\n"
        "- pack algebra\n"
        "- score\n\n"
        "What would you like to do?"
    )


def _extract_audio_question_from_request(request):
    try:
        num_media = int(request.POST.get("NumMedia", "0") or "0")
    except ValueError:
        num_media = 0

    found_audio = False

    for index in range(num_media):
        content_type = (request.POST.get(f"MediaContentType{index}", "") or "").strip().lower()
        media_url = (request.POST.get(f"MediaUrl{index}", "") or "").strip()
        if content_type.startswith("audio/") and media_url:
            found_audio = True
            try:
                transcript = transcribe_whatsapp_audio(media_url, content_type=content_type)
            except Exception:
                continue
            return transcript.strip(), False

    return "", found_audio


def _build_tutor_reply(request, incoming_msg, practice_state):
    normalized = incoming_msg.strip().lower()
    practice_subject = None
    is_score_request = normalized in {"score", "progress", "my score", "show progress"}
    is_practice_request = False

    # Twilio sandbox join keyword — user just joined for the first time
    if normalized.startswith("join ") or normalized == "join":
        return _build_welcome_reply(request)

    if normalized in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "start", "menu", "help"}:
        return _build_greeting_reply(request)

    if normalized in {"offline library", "study offline", "offline app"}:
        return f"Open your offline library here: {_get_request_base_url(request)}/offline-library/"

    if _is_out_of_scope_question(incoming_msg):
        return _unsupported_subject_reply()

    if normalized.startswith("practice "):
        practice_body = normalized[9:].strip()
        if practice_body.startswith("english "):
            practice_subject = ("english", practice_body[8:].strip())
        elif practice_body == "english":
            practice_subject = "english"
        elif practice_body.startswith("maths "):
            practice_subject = ("maths", practice_body[6:].strip())
        elif practice_body == "maths":
            practice_subject = "maths"
        else:
            practice_subject = practice_body
        is_practice_request = True
    elif normalized in {"practice", "quiz me", "give me a question"}:
        practice_subject = None
        is_practice_request = True

    if is_score_request:
        return f"{_format_score(practice_state)}\n{_format_learning_progress(practice_state)}"

    if is_practice_request:
        try:
            return _build_practice_question_reply(request, practice_state, practice_subject)
        except Exception:
            topic_label = None
            if isinstance(practice_subject, tuple):
                base_subject, topic = practice_subject
                topic_label = f"{base_subject} topic '{topic}'" if topic else base_subject
            else:
                topic_label = practice_subject
            if practice_subject:
                return (
                    f"Sorry, I couldn't create a {topic_label} practice question right now. "
                    "Please try again in a moment."
                )
            return "Sorry, I couldn't create a practice question right now. Please try again in a moment."

    if practice_state.get("pending") and (
        _looks_like_new_learning_request(incoming_msg)
        or looks_like_linear_equation_question(incoming_msg)
        or looks_like_quadratic_equation_question(incoming_msg)
    ):
        practice_state["pending"] = None

    practice_feedback = _build_practice_feedback_reply(practice_state, incoming_msg)
    if practice_feedback:
        return practice_feedback

    solved_equation = solve_linear_equation(incoming_msg)
    if solved_equation:
        _remember_topic(practice_state, "linear equations", "maths")
        return f"{solved_equation}{_build_topic_resource_lines(request, 'maths', 'linear equations')}"

    solved_quadratic = solve_quadratic_equation(incoming_msg)
    if solved_quadratic:
        _remember_topic(practice_state, "quadratic equations", "maths")
        return f"{solved_quadratic}{_build_topic_resource_lines(request, 'maths', 'quadratic equations')}"

    if normalized.startswith("pack "):
        query = normalized[5:].strip()
        pack = None
        try:
            pack = get_or_generate_learning_pack(query)
        except Exception:
            pack = get_learning_pack_by_slug_or_topic(query)
        if pack:
            _remember_topic(practice_state, pack["topic"], pack.get("subject"))
            return (
                f"{pack['title']}\n"
                f"{pack['summary']}\n"
                f"Download: {_get_request_base_url(request)}/packs/{pack['slug']}/"
            )
        return "I could not find that pack. Try 'offline library' to browse available topics."

    if normalized.startswith("audio pack "):
        query = normalized[11:].strip()
        pack = None
        try:
            pack = get_or_generate_audio_pack(query)
        except Exception:
            pack = get_audio_pack_by_slug_or_topic(query)
        if pack:
            _remember_topic(practice_state, pack["topic"], pack.get("subject"))
            return (
                f"{pack['title']}\n"
                f"{pack['summary']}\n"
                f"Open audio lesson: {_get_request_base_url(request)}/audio-packs/{pack['slug']}/player/"
            )
        return "I could not find that audio pack. Try 'offline library' to browse available topics."

    inferred_subject, inferred_topic = _resolve_resource_topic(incoming_msg)
    if inferred_topic:
        _remember_topic(practice_state, inferred_topic, inferred_subject)

    local_answer = build_local_tutor_answer(incoming_msg)

    try:
        ai_reply = ask_ai(incoming_msg, subject=inferred_subject, topic=inferred_topic)
        if inferred_topic:
            return f"{ai_reply}{_build_topic_resource_lines(request, inferred_subject, inferred_topic)}"
        return ai_reply
    except Exception as ai_exc:
        print(f"[ask_ai] failed for message={incoming_msg!r} subject={inferred_subject} topic={inferred_topic} error={ai_exc}")
        traceback.print_exc()
        # For sentence-analysis questions, the generic topic explanation is misleading —
        # the student asked about a specific sentence, not for a topic lesson.
        if is_sentence_analysis_question(incoming_msg):
            topic_label = inferred_topic or "that"
            return (
                f"I'm having trouble processing your question right now. "
                f"To answer it properly, look at each word in the sentence and ask: "
                f"does this word describe a noun? If yes, it is an adjective. "
                f"If no adjective-like word is present, the sentence may not contain one.\n\n"
                f"Try again in a moment and I will give you a specific answer."
                if inferred_topic == "adjectives" else
                f"I'm having trouble processing your question about {topic_label} right now. "
                f"Please try again in a moment and I will give you a specific answer for that sentence."
            )
        if local_answer:
            local_subject = local_answer.get("subject")
            local_topic = local_answer.get("topic")
            if local_topic:
                _remember_topic(practice_state, local_topic, local_subject)
                return f"{local_answer['answer']}{_build_topic_resource_lines(request, local_subject, local_topic)}"
            return local_answer["answer"]
        if inferred_topic:
            return _build_topic_study_fallback(request, inferred_subject, inferred_topic)
        return (
            "Sorry, I couldn't process your request right now. "
            f"You can still use the offline library: {_get_request_base_url(request)}/offline-library/"
        )


def _offline_library_entries(request, subject=None):
    entries = []
    for current_subject in ([subject] if subject else ["maths", "english"]):
        for topic in get_supported_topics(subject=current_subject):
            slug = _topic_to_slug(topic)
            topic_title = _topic_to_title(topic)
            if current_subject == "maths":
                summary = f"Dynamic Maths study pack for {topic_title}, generated through Gemini when opened."
            else:
                summary = f"Dynamic English study pack for {topic_title}, generated through Gemini when opened."

            entries.append(
                {
                    "topic": topic_title,
                    "subject": current_subject,
                    "summary": summary,
                    "text_url": f"{_get_request_base_url(request)}/packs/{slug}/",
                    "audio_url": f"{_get_request_base_url(request)}/audio-packs/audio-{slug}/player/",
                    "transcript_url": f"{_get_request_base_url(request)}/audio-packs/audio-{slug}/transcript/",
                }
            )

    return entries


def _recent_topic_library_entries(request, practice_state, subject=None):
    entries = []
    seen_slugs = set()

    for item in practice_state.get("recent_topics", []):
        if not isinstance(item, dict):
            continue

        topic = item.get("topic", "").strip()
        topic_subject = (item.get("subject") or "general").strip().lower()
        if not topic:
            continue
        if subject and topic_subject != subject:
            continue

        try:
            learning_pack = get_or_generate_learning_pack(topic, subject=topic_subject if topic_subject != "general" else None)
            audio_pack = get_or_generate_audio_pack(topic, subject=topic_subject if topic_subject != "general" else None)
        except Exception:
            continue

        if learning_pack["slug"] in seen_slugs:
            continue
        seen_slugs.add(learning_pack["slug"])
        entries.append(
            {
                "topic": learning_pack["topic"],
                "subject": learning_pack["subject"],
                "summary": learning_pack["summary"],
                "text_url": f"{_get_request_base_url(request)}/packs/{learning_pack['slug']}/",
                "audio_url": f"{_get_request_base_url(request)}/audio-packs/{audio_pack['slug']}/player/",
                "transcript_url": f"{_get_request_base_url(request)}/audio-packs/{audio_pack['slug']}/transcript/",
                "is_recent_topic": True,
            }
        )

    return entries


def pwa_manifest(request):
    data = {
        "name": "EduAccess Offline Library",
        "short_name": "EduAccess",
        "description": "Installable offline study library for low-data learning.",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f4efe4",
        "theme_color": "#0f766e",
        "icons": [
            {
                "src": static("whatsapp_bot/icons/icon-192.png"),
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": static("whatsapp_bot/icons/icon-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable",
            },
        ],
    }
    return JsonResponse(data)


def service_worker(request):
    offline_urls = [
        "/",
        "/login/",
        "/register/",
        "/offline-library/",
        "/offline-library/?subject=maths",
        "/offline-library/?subject=english",
        "/offline-fallback/",
        static("whatsapp_bot/icons/icon-192.png"),
        static("whatsapp_bot/icons/icon-512.png"),
    ]

    for current_subject in ["maths", "english"]:
        for topic in get_supported_topics(subject=current_subject):
            slug = _topic_to_slug(topic)
            offline_urls.append(f"/packs/{slug}/")
            offline_urls.append(f"/audio-packs/audio-{slug}/player/")
            offline_urls.append(f"/audio-packs/audio-{slug}/transcript/")

    offline_urls = list(dict.fromkeys(offline_urls))

    response = render(
        request,
        "whatsapp_bot/service-worker.js",
        {
            "cache_name": "eduaccess-pwa-v2",
            "offline_urls": offline_urls,
        },
        content_type="application/javascript; charset=utf-8",
    )
    response["Service-Worker-Allowed"] = "/"
    return response


def offline_fallback_page(request):
    return render(request, "whatsapp_bot/offline_fallback.html")


def offline_library_page(request):
    subject = request.GET.get("subject", "").strip().lower() or None
    if subject not in {None, "english", "maths"}:
        subject = None

    recent_entries = []
    if request.user.is_authenticated:
        _, practice_state = _load_user_practice_state(request.user)
        recent_entries = _recent_topic_library_entries(request, practice_state, subject=subject)
    static_entries = _offline_library_entries(request, subject=subject)
    recent_topics = {entry["topic"].strip().lower() for entry in recent_entries}
    entries = [
        *recent_entries,
        *[entry for entry in static_entries if entry["topic"].strip().lower() not in recent_topics],
    ]

    return render(
        request,
        "whatsapp_bot/offline_library.html",
        {
            "subject": subject,
            "entries": entries,
        },
    )


def register_page(request):
    if request.user.is_authenticated:
        return redirect("study_assistant")

    form = EduAccessUserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("study_assistant")

    return render(request, "whatsapp_bot/register.html", {"form": form})


def landing_page(request):
    if request.user.is_authenticated:
        return redirect("study_assistant")
    return render(request, "whatsapp_bot/landing.html")


class EduAccessLoginView(LoginView):
    template_name = "whatsapp_bot/login.html"
    authentication_form = EduAccessAuthenticationForm
    redirect_authenticated_user = True


class EduAccessLogoutView(LogoutView):
    next_page = reverse_lazy("offline_library")


@login_required(login_url=reverse_lazy("login"))
def dashboard_page(request):
    progress, practice_state = _load_user_practice_state(request.user)
    summary = _build_dashboard_summary(practice_state)
    return render(
        request,
        "whatsapp_bot/dashboard.html",
        {
            "progress": progress,
            "summary": summary,
        },
    )


@login_required(login_url=reverse_lazy("login"))
def study_assistant_page(request):
    session_key = "study_assistant_history"
    history = request.session.get(session_key, [])
    progress, practice_state = _load_user_practice_state(request.user)

    # Allow welcome page links like ?prompt=practice+maths to auto-fire a question
    prompt_from_url = request.GET.get("prompt", "").strip()
    if prompt_from_url and request.method == "GET":
        reply = _build_tutor_reply(request, prompt_from_url, practice_state)
        history = [
            *history,
            {"role": "student", "text": prompt_from_url},
            {"role": "assistant", "text": reply},
        ][-12:]
        _save_user_practice_state(progress, practice_state)
        request.session[session_key] = history

    if request.method == "POST":
        if "clear" in request.POST:
            history = []
            practice_state = _empty_practice_state()
            _save_user_practice_state(progress, practice_state)
        else:
            question = request.POST.get("question", "").strip()
            if question:
                normalized_question = question.lower()
                if normalized_question in {"offline library", "study offline", "offline app"}:
                    return redirect("offline_library")
                reply = _build_tutor_reply(request, question, practice_state)
                history = [
                    *history,
                    {"role": "student", "text": question},
                    {"role": "assistant", "text": reply},
                ][-12:]
                _save_user_practice_state(progress, practice_state)
        request.session[session_key] = history

    return render(
        request,
        "whatsapp_bot/study_assistant.html",
        {
            "history": history,
        },
    )


@csrf_exempt
@login_required(login_url=reverse_lazy("login"))
def study_assistant_api(request):
    if request.method != "POST":
        return JsonResponse({"detail": "POST only."}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON."}, status=400)

    question = str(payload.get("question", "")).strip()
    if not question:
        return JsonResponse({"detail": "Question is required."}, status=400)

    progress, practice_state = _load_user_practice_state(request.user)
    reply = _build_tutor_reply(request, question, practice_state)
    _save_user_practice_state(progress, practice_state)
    return JsonResponse({"reply": reply})


def learning_pack_download(request, slug):
    try:
        pack = get_or_generate_learning_pack(slug)
    except Exception:
        pack = get_learning_pack_by_slug_or_topic(slug)
        if not pack:
            raise Http404("Learning pack not found.")

    response = HttpResponse(pack["content"], content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{pack["slug"]}.txt"'
    return response


def audio_pack_transcript_download(request, slug):
    lookup_key = slug[6:] if slug.startswith("audio-") else slug
    try:
        pack = get_or_generate_audio_pack(lookup_key)
    except Exception:
        pack = get_audio_pack_by_slug_or_topic(slug)
        if not pack:
            raise Http404("Audio pack not found.")

    response = HttpResponse(pack["transcript"], content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{pack["slug"]}-transcript.txt"'
    return response


def audio_pack_player(request, slug):
    lookup_key = slug[6:] if slug.startswith("audio-") else slug
    try:
        pack = get_or_generate_audio_pack(lookup_key)
    except Exception:
        pack = get_audio_pack_by_slug_or_topic(slug)
        if not pack:
            raise Http404("Audio pack not found.")

    return render(
        request,
        "whatsapp_bot/audio_player.html",
        {
            "pack": pack,
        },
    )


@csrf_exempt
def whatsapp_webhook(request):
    if request.method == "POST":
        incoming_msg = request.POST.get("Body", "").strip()
        raw_sender = request.POST.get("From", "")
        phone_number = _normalize_whatsapp_sender(raw_sender)
        print(
            f"[whatsapp_webhook] method=POST from={raw_sender} normalized={phone_number} "
            f"has_body={bool(incoming_msg)} host={request.get_host()}"
        )
        resp = MessagingResponse()
        msg = resp.message()
        try:
            progress, practice_state = _load_whatsapp_practice_state(phone_number)
            if not incoming_msg:
                incoming_msg, had_audio = _extract_audio_question_from_request(request)
            else:
                had_audio = False
            if incoming_msg:
                reply = _build_tutor_reply(request, incoming_msg, practice_state)
                _save_whatsapp_practice_state(progress, practice_state)
            else:
                if had_audio:
                    reply = (
                        "Hi! I could not transcribe your audio just now. "
                        "Please try again with a clear audio recording or send the question as text."
                    )
                else:
                    reply = "Hi! Please send a text or audio question so I can help you."
        except Exception:
            print("[whatsapp_webhook] error while processing request")
            traceback.print_exc()
            reply = (
                "Sorry, I could not process your WhatsApp text or audio message right now. "
                "Please try again in a moment."
            )

        msg.body(reply)
        return HttpResponse(str(resp), content_type="application/xml")

    print(f"[whatsapp_webhook] method={request.method} host={request.get_host()}")
    return HttpResponse("Hello, this endpoint is for WhatsApp messages only.")
