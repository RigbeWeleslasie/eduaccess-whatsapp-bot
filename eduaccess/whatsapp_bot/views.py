# eduaccess/whatsapp/views.py
import math
import re
from fractions import Fraction

from django.http import Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from twilio.twiml.messaging_response import MessagingResponse

from .ai import (
    ask_ai,
    get_audio_pack_by_slug_or_topic,
    get_audio_packs,
    generate_question,
    get_curriculum_topics,
    get_learning_pack_by_slug_or_topic,
    get_learning_packs,
    get_practice_topics,
)
from .models import AudioLearningPack, LearningPack, PracticeQuestion, TopicProgress, UserProgress


GREETING_MESSAGES = {
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
}

PRACTICE_MESSAGES = {
    "practice",
    "quiz",
    "test me",
    "give me a question",
}
PROGRESS_MESSAGES = {
    "progress",
    "report",
    "my progress",
    "weak areas",
    "weaknesses",
}
HELP_MESSAGES = {
    "help",
    "menu",
    "options",
}
OFFLINE_ON_MESSAGES = {
    "offline on",
    "study offline",
}
OFFLINE_OFF_MESSAGES = {
    "offline off",
    "online mode",
}
OFFLINE_STATUS_MESSAGES = {
    "offline status",
    "mode",
}
LOW_DATA_ON_MESSAGES = {
    "lite on",
    "data saver on",
    "low data on",
}
LOW_DATA_OFF_MESSAGES = {
    "lite off",
    "data saver off",
    "low data off",
}
TOPIC_MESSAGES = {
    "english topics",
    "topics english",
    "show english topics",
}
PACK_MESSAGES = {
    "packs",
    "learning packs",
    "study packs",
}
AUDIO_PACK_MESSAGES = {
    "audio packs",
    "audio lessons",
    "audio pack",
}
EXIT_MESSAGES = {
    "cancel",
    "exit",
    "stop",
    "quit",
}
SUPPORTED_PRACTICE_SUBJECTS = {"english", "maths", "math"}
SUPPORTED_DIFFICULTIES = ("foundation", "core", "stretch")
MAX_REPLY_CHARS = 700
QUESTION_STARTERS = (
    "what",
    "why",
    "how",
    "when",
    "where",
    "who",
    "which",
    "explain",
    "define",
    "tell me",
    "can you",
)


def _normalize_answer(text):
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(text.split())


def _candidate_answers(expected_answer):
    normalized_expected = _normalize_answer(expected_answer)
    candidates = {normalized_expected}

    for part in re.split(r"[|/;]", expected_answer):
        normalized_part = _normalize_answer(part)
        if normalized_part:
            candidates.add(normalized_part)

    if normalized_expected.startswith("option "):
        option_letter = normalized_expected.replace("option ", "", 1).strip()
        if option_letter:
            candidates.add(option_letter)

    return {candidate for candidate in candidates if candidate}


def _extract_math_expression(text):
    lowered_text = text.strip().lower()
    if "=" in lowered_text:
        lowered_text = lowered_text.split("=")[-1].strip()

    cleaned = lowered_text.replace(" ", "")
    if not cleaned:
        return None

    if re.fullmatch(r"-?\d+(\.\d+)?%?", cleaned):
        return cleaned

    if re.fullmatch(r"-?\d+/\d+", cleaned):
        return cleaned

    return None


def _math_to_number(text):
    expression = _extract_math_expression(text)
    if expression is None:
        return None

    try:
        if expression.endswith("%"):
            return float(expression[:-1]) / 100
        if "/" in expression:
            numerator, denominator = expression.split("/", 1)
            return float(Fraction(int(numerator), int(denominator)))
        return float(expression)
    except (ValueError, ZeroDivisionError):
        return None


def _math_answers_match(expected_answer, submitted_answer):
    expected_value = _math_to_number(expected_answer)
    submitted_value = _math_to_number(submitted_answer)
    if expected_value is not None and submitted_value is not None:
        return math.isclose(expected_value, submitted_value, rel_tol=1e-9, abs_tol=1e-9)

    expected_normalized = _normalize_answer(expected_answer)
    submitted_normalized = _normalize_answer(submitted_answer)
    if expected_normalized == submitted_normalized:
        return True

    if expected_normalized.startswith("x ") and submitted_normalized == expected_normalized.split()[-1]:
        return True
    if submitted_normalized.startswith("x ") and expected_normalized == submitted_normalized.split()[-1]:
        return True

    return False


def _is_correct_answer(subject, expected_answer, submitted_answer):
    normalized_submitted = _normalize_answer(submitted_answer)
    if not normalized_submitted:
        return False

    if subject == "maths":
        return _math_answers_match(expected_answer, submitted_answer)

    accepted_answers = _candidate_answers(expected_answer)
    if normalized_submitted in accepted_answers:
        return True

    if subject == "english":
        submitted_words = normalized_submitted.split()
        if len(submitted_words) <= 2:
            for accepted in accepted_answers:
                accepted_words = accepted.split()
                if normalized_submitted in accepted_words or accepted in submitted_words:
                    return True

    return False


def _extract_practice_subject(message):
    for subject in SUPPORTED_PRACTICE_SUBJECTS:
        if subject in message:
            return "maths" if subject == "math" else subject
    return None


def _extract_difficulty(message):
    for difficulty in SUPPORTED_DIFFICULTIES:
        if difficulty in message:
            return difficulty
    return None


def _extract_requested_topic(message, subject):
    if not subject:
        return None

    available_topics = get_practice_topics(subject)
    lowered_message = message.lower()

    for topic in sorted(available_topics, key=len, reverse=True):
        if topic.lower() in lowered_message:
            return topic

    if subject == "english":
        for keyword in ("grammar", "tenses", "vocabulary", "synonyms", "antonyms", "reported speech", "passive voice", "conditionals", "comprehension"):
            if keyword in lowered_message:
                return keyword

    return None


def _extract_pack_subject(message):
    lowered_message = message.lower()
    if "math" in lowered_message:
        return "maths"
    if "english" in lowered_message:
        return "english"
    return None


def _extract_pack_query(message):
    lowered_message = message.lower().strip()
    if lowered_message.startswith("pack "):
        return lowered_message[5:].strip()
    if lowered_message.startswith("get pack "):
        return lowered_message[9:].strip()
    return None


def _extract_audio_pack_query(message):
    lowered_message = message.lower().strip()
    if lowered_message.startswith("audio pack "):
        return lowered_message[11:].strip()
    if lowered_message.startswith("get audio pack "):
        return lowered_message[15:].strip()
    if lowered_message.startswith("audio lesson "):
        return lowered_message[13:].strip()
    return None


def _looks_like_general_question(message):
    lowered_message = message.strip().lower()
    if "?" in lowered_message:
        return True
    return any(lowered_message.startswith(starter) for starter in QUESTION_STARTERS)


def _get_or_create_progress(phone_number):
    return UserProgress.objects.get_or_create(phone_number=phone_number)[0]


def _reset_session(progress):
    progress.session_correct_answers = 0
    progress.session_total_attempts = 0
    progress.awaiting_remediation = False
    progress.current_streak = 0
    progress.lesson_progress = 0
    progress.lesson_topic = ""
    progress.lesson_subject = ""
    progress.save(
        update_fields=[
            "session_correct_answers",
            "session_total_attempts",
            "awaiting_remediation",
            "current_streak",
            "lesson_progress",
            "lesson_topic",
            "lesson_subject",
        ]
    )


def _clear_practice_state(progress):
    progress.awaiting_practice_answer = False
    progress.awaiting_remediation = False
    progress.save(update_fields=["awaiting_practice_answer", "awaiting_remediation"])


def _compact_reply(text):
    compact_text = "\n".join(line.strip() for line in text.strip().splitlines() if line.strip())
    if len(compact_text) <= MAX_REPLY_CHARS:
        return compact_text
    return compact_text[: MAX_REPLY_CHARS - 3].rstrip() + "..."


def _set_low_data_mode(progress, enabled):
    progress.low_data_mode = enabled
    progress.save(update_fields=["low_data_mode"])
    if enabled:
        return "Data saver is on. Replies will stay shorter."
    return "Data saver is off. Replies can be more detailed."


def _set_offline_mode(progress, enabled):
    progress.offline_mode = enabled
    progress.save(update_fields=["offline_mode"])
    if enabled:
        return (
            "Offline mode is on. Use practice, packs, or audio packs. "
            "Live AI answers are paused."
        )
    return "Offline mode is off. Live AI answers are available again."


def _offline_status_text(progress):
    state = "on" if progress.offline_mode else "off"
    return f"Offline mode is {state}. Data saver is {'on' if progress.low_data_mode else 'off'}."


def _get_request_base_url(request):
    return f"{request.scheme}://{request.get_host()}"


def _list_learning_packs(subject=None):
    packs = get_learning_packs(subject=subject)
    if not packs:
        return "No learning packs are available yet."

    heading = "Available packs"
    if subject:
        heading = f"{subject.title()} packs"

    pack_lines = [f"{pack['topic']}: pack {pack['topic'].lower()}" for pack in packs]
    return heading + ":\n" + "\n".join(pack_lines)


def _list_audio_packs(subject=None):
    packs = get_audio_packs(subject=subject)
    if not packs:
        return "No audio packs are available yet."

    heading = "Audio packs"
    if subject:
        heading = f"{subject.title()} audio packs"

    pack_lines = [f"{pack['topic']}: audio pack {pack['topic'].lower()}" for pack in packs]
    return heading + ":\n" + "\n".join(pack_lines)


def _find_local_study_pack_from_message(message):
    lowered_message = message.lower()
    for pack in get_learning_packs():
        if pack["topic"].lower() in lowered_message:
            return ("text", pack)
    for pack in get_audio_packs():
        if pack["topic"].lower() in lowered_message:
            return ("audio", pack)
    return (None, None)


def _get_learning_pack(pack_query):
    pack = get_learning_pack_by_slug_or_topic(pack_query)
    if pack:
        return pack

    try:
        return LearningPack.objects.get(slug=pack_query)
    except LearningPack.DoesNotExist:
        try:
            return LearningPack.objects.get(topic__iexact=pack_query)
        except LearningPack.DoesNotExist:
            return None


def _get_audio_pack(pack_query):
    pack = get_audio_pack_by_slug_or_topic(pack_query)
    if pack:
        return pack

    try:
        return AudioLearningPack.objects.get(slug=pack_query)
    except AudioLearningPack.DoesNotExist:
        try:
            return AudioLearningPack.objects.get(topic__iexact=pack_query)
        except AudioLearningPack.DoesNotExist:
            return None


def _learning_pack_reply(pack, base_url, low_data=False):
    slug = pack["slug"] if isinstance(pack, dict) else pack.slug
    title = pack["title"] if isinstance(pack, dict) else pack.title
    summary = pack["summary"] if isinstance(pack, dict) else pack.summary
    topic = pack["topic"] if isinstance(pack, dict) else pack.topic
    download_url = f"{base_url}/packs/{slug}/"
    if low_data:
        return (
            f"{title}\n"
            f"{summary}\n"
            f"Download: {download_url}"
        )
    return (
        f"{title} ({topic})\n"
        f"{summary}\n"
        f"Download full text: {download_url}"
    )


def _audio_pack_reply(pack, base_url, low_data=False):
    slug = pack["slug"] if isinstance(pack, dict) else pack.slug
    title = pack["title"] if isinstance(pack, dict) else pack.title
    summary = pack["summary"] if isinstance(pack, dict) else pack.summary
    duration_label = pack["duration_label"] if isinstance(pack, dict) else pack.duration_label
    audio_url = pack["audio_url"] if isinstance(pack, dict) else pack.audio_url
    transcript_url = f"{base_url}/audio-packs/{slug}/transcript/"

    lines = [title]
    if duration_label:
        lines[0] = f"{title} ({duration_label})"
    lines.append(summary)
    if audio_url:
        lines.append(f"Audio: {audio_url}")
    lines.append(f"Transcript: {transcript_url}")
    if low_data and len(lines) > 3:
        lines = lines[:3]
    return "\n".join(lines)


def _offline_study_reply(message, progress, base_url):
    pack_kind, pack = _find_local_study_pack_from_message(message)
    if pack_kind == "text":
        return _learning_pack_reply(pack, base_url=base_url, low_data=progress.low_data_mode)
    if pack_kind == "audio":
        return _audio_pack_reply(pack, base_url=base_url, low_data=progress.low_data_mode)

    return (
        "Offline mode is on.\n"
        "Use 'practice maths', 'practice english', 'packs', 'audio packs', or ask for a known topic like Algebra or Passive voice."
    )


def _get_or_create_topic_progress(progress, subject, topic):
    return TopicProgress.objects.get_or_create(
        user=progress,
        subject=subject,
        topic=topic,
    )[0]


def _get_topic_accuracy(topic_progress):
    if topic_progress.attempts == 0:
        return 0.0
    return topic_progress.correct_answers / topic_progress.attempts


def _pick_next_curriculum_topic(subject, current_topic=None):
    curriculum_topics = get_curriculum_topics(subject)
    if not curriculum_topics:
        return current_topic
    if current_topic not in curriculum_topics:
        return curriculum_topics[0]
    current_index = curriculum_topics.index(current_topic)
    if current_index + 1 < len(curriculum_topics):
        return curriculum_topics[current_index + 1]
    return curriculum_topics[current_index]


def _pick_focus_topic(progress, subject):
    weakest_topics = list(
        progress.topic_progress.filter(subject=subject, attempts__gt=0).order_by("attempts", "topic")
    )
    if not weakest_topics:
        return None
    weakest_topics.sort(key=lambda item: (_get_topic_accuracy(item), -item.attempts, item.topic.lower()))
    if _get_topic_accuracy(weakest_topics[0]) >= 0.7:
        return None
    return weakest_topics[0].topic


def _recommend_difficulty(progress, subject):
    subject_topics = list(progress.topic_progress.filter(subject=subject, attempts__gt=0))
    if progress.awaiting_remediation:
        return "foundation"
    if subject_topics:
        accuracy = sum(item.correct_answers for item in subject_topics) / sum(
            item.attempts for item in subject_topics
        )
        if accuracy < 0.5:
            return "foundation"
        if accuracy >= 0.8 and progress.current_streak >= 3:
            return "stretch"
    if progress.current_streak >= 2:
        return "core"
    return "foundation"


def _get_practice_question(subject=None, difficulty="foundation", topic=None):
    saved_questions = PracticeQuestion.objects.all()
    if subject:
        saved_questions = saved_questions.filter(subject=subject)
    if difficulty:
        saved_questions = saved_questions.filter(difficulty=difficulty)
    if topic:
        saved_questions = saved_questions.filter(topic__iexact=topic)

    saved_question = saved_questions.order_by("id").first()
    if saved_question:
        return (
            saved_question.question_text,
            saved_question.answer_text,
            saved_question.topic,
            saved_question.subject,
            saved_question.difficulty,
        )

    question_text, answer_text, generated_topic = generate_question(
        subject=subject,
        topic=topic,
        difficulty=difficulty,
    )
    return question_text, answer_text, generated_topic, subject or "maths", difficulty


def _store_current_question(progress, question_text, answer_text, topic, subject, difficulty):
    progress.last_question = question_text
    progress.last_answer = answer_text
    progress.last_topic = topic
    progress.last_subject = subject
    progress.practice_difficulty = difficulty
    progress.awaiting_practice_answer = True
    progress.save()


def _prepare_lesson(progress, subject, topic):
    lesson_changed = progress.lesson_topic != topic or progress.lesson_subject != subject
    progress.lesson_subject = subject
    progress.lesson_topic = topic
    if progress.lesson_progress == 0 or lesson_changed:
        progress.lesson_progress = 0
    progress.save(update_fields=["lesson_subject", "lesson_topic", "lesson_progress"])


def _should_reset_for_new_practice(progress, subject, difficulty, topic):
    if not progress.lesson_topic:
        return True
    if subject or difficulty or topic:
        return True
    return False


def _start_practice(progress, subject=None, difficulty=None, topic=None):
    chosen_subject = subject or progress.last_subject or "maths"
    chosen_difficulty = difficulty or _recommend_difficulty(progress, chosen_subject)
    chosen_topic = topic or progress.lesson_topic or _pick_focus_topic(progress, chosen_subject)
    if not chosen_topic:
        chosen_topic = _pick_next_curriculum_topic(chosen_subject)
    question_text, answer_text, generated_topic, generated_subject, generated_difficulty = _get_practice_question(
        subject=chosen_subject,
        difficulty=chosen_difficulty,
        topic=chosen_topic,
    )
    _prepare_lesson(progress, generated_subject, generated_topic)
    _store_current_question(
        progress,
        question_text,
        answer_text,
        generated_topic,
        generated_subject,
        generated_difficulty,
    )
    progress.awaiting_remediation = False
    progress.save(update_fields=["awaiting_remediation"])
    topic_note = ""
    if chosen_topic and chosen_topic.lower() == generated_topic.lower():
        topic_note = f" Focus: {chosen_topic}."
    return (
        f"Practice question ({generated_topic}, {generated_difficulty}): {question_text}\n"
        f"Reply with your answer. Lesson {progress.lesson_progress + 1}/{progress.lesson_goal}.{topic_note}"
    )


def _build_remediation_reply(progress):
    remediation_question, remediation_answer, remediation_topic, remediation_subject, remediation_difficulty = (
        _get_practice_question(
            subject=progress.last_subject or "maths",
            difficulty="foundation",
            topic=progress.last_topic or None,
        )
    )
    _store_current_question(
        progress,
        remediation_question,
        remediation_answer,
        remediation_topic,
        remediation_subject,
        remediation_difficulty,
    )
    progress.awaiting_remediation = True
    progress.save(update_fields=["awaiting_remediation"])
    return (
        f"Quick retry on {remediation_topic}: {remediation_question}\n"
        "Reply with your answer."
    )


def _build_progress_summary(progress):
    if progress.total_attempts == 0:
        return (
            "Progress: no practice attempts yet.\n"
            "Send 'practice maths' or 'practice english' to begin."
        )

    overall_accuracy = round((progress.correct_answers / progress.total_attempts) * 100)
    topic_rows = list(progress.topic_progress.filter(attempts__gt=0))
    topic_rows.sort(key=lambda item: (_get_topic_accuracy(item), -item.attempts, item.topic.lower()))
    weak_topics = topic_rows[:3]

    lines = [
        f"Overall progress: {progress.correct_answers}/{progress.total_attempts} correct ({overall_accuracy}%).",
        f"Current session: {progress.session_correct_answers}/{progress.session_total_attempts}.",
        f"Current level: {progress.practice_difficulty}.",
    ]
    if progress.lesson_topic:
        lines.append(
            f"Current lesson: {progress.lesson_subject} - {progress.lesson_topic} ({progress.lesson_progress}/{progress.lesson_goal})."
        )

    if weak_topics:
        weak_parts = []
        for item in weak_topics:
            topic_accuracy = round(_get_topic_accuracy(item) * 100)
            weak_parts.append(f"{item.topic} {topic_accuracy}%")
        lines.append("Weak areas: " + ", ".join(weak_parts) + ".")
        lines.append(f"Revise next: {weak_topics[0].topic}.")
    else:
        lines.append("Weak areas: not enough topic data yet.")

    next_subject = progress.last_subject or "maths"
    recommended_topic = _pick_focus_topic(progress, next_subject)
    recommended_difficulty = _recommend_difficulty(progress, next_subject)
    if recommended_topic:
        lines.append(
            f"Recommended practice: practice {next_subject} {recommended_difficulty} on {recommended_topic}."
        )
    else:
        lines.append(f"Recommended practice: practice {next_subject} {recommended_difficulty}.")

    if progress.low_data_mode:
        compact_lines = lines[:3]
        if weak_topics:
            compact_lines.append(f"Revise next: {weak_topics[0].topic}.")
        else:
            compact_lines.append("Revise next: keep practicing.")
        return "\n".join(compact_lines)

    return "\n".join(lines)


def _grade_practice_answer(progress, student_answer):
    is_correct = _is_correct_answer(
        progress.last_subject or "maths",
        progress.last_answer,
        student_answer,
    )
    topic_progress = _get_or_create_topic_progress(
        progress,
        progress.last_subject or "maths",
        progress.last_topic or "General",
    )

    progress.total_attempts += 1
    progress.session_total_attempts += 1
    topic_progress.attempts += 1

    if is_correct:
        progress.correct_answers += 1
        progress.session_correct_answers += 1
        progress.current_streak += 1
        if progress.lesson_topic == (progress.last_topic or ""):
            progress.lesson_progress += 1
        progress.awaiting_practice_answer = False
        progress.awaiting_remediation = False
        topic_progress.correct_answers += 1
        topic_progress.last_outcome = "correct"
        feedback = "Correct! Well done."
    else:
        progress.current_streak = 0
        topic_progress.last_outcome = "incorrect"
        feedback = f"Not quite. The correct answer is: {progress.last_answer}"

    topic_progress.save()
    progress.save()

    if is_correct:
        if progress.lesson_progress >= progress.lesson_goal and progress.lesson_topic:
            completed_topic = progress.lesson_topic
            next_topic = _pick_next_curriculum_topic(progress.last_subject or "maths", completed_topic)
            progress.lesson_progress = 0
            progress.lesson_topic = next_topic
            progress.lesson_subject = progress.last_subject or "maths"
            progress.save(update_fields=["lesson_progress", "lesson_topic", "lesson_subject"])
            return (
                f"{feedback}\n"
                f"Session score: {progress.session_correct_answers}/{progress.session_total_attempts}.\n"
                f"Lesson complete: {completed_topic}.\n"
                f"Next topic: {next_topic}. Send 'practice' to continue."
            )
        return (
            f"{feedback}\n"
            f"Session score: {progress.session_correct_answers}/{progress.session_total_attempts}.\n"
            f"Overall progress: {progress.correct_answers}/{progress.total_attempts}.\n"
            f"Lesson progress: {progress.lesson_progress}/{progress.lesson_goal} on {progress.lesson_topic or progress.last_topic}.\n"
            "Send 'progress' to see weak areas, or 'practice' to continue this lesson."
        )

    remediation_reply = _build_remediation_reply(progress)
    return (
        f"{feedback}\n"
        f"Session score: {progress.session_correct_answers}/{progress.session_total_attempts}.\n"
        f"Overall progress: {progress.correct_answers}/{progress.total_attempts}.\n"
        f"{remediation_reply}"
    )


def _help_text(low_data=False):
    if low_data:
        return (
            "Commands:\n"
            "practice maths\n"
            "practice english\n"
            "packs\n"
            "audio packs\n"
            "english topics\n"
            "progress\n"
            "offline on | offline off\n"
            "lite off"
        )

    return (
        "Commands:\n"
        "practice maths\n"
        "practice english\n"
        "practice english grammar\n"
        "practice english reported speech\n"
        "packs | packs maths | packs english\n"
        "pack algebra | pack passive voice\n"
        "audio packs | audio packs maths | audio packs english\n"
        "audio pack algebra | audio pack passive voice\n"
        "english topics\n"
        "practice maths foundation|core|stretch\n"
        "progress\n"
        "offline on | offline off | offline status\n"
        "lite on | lite off\n"
        "stop\n"
        "Or ask any study question."
    )


def _english_topics_text():
    topics = [
        topic for topic in get_practice_topics("english")
        if topic
        in {
            "grammar",
            "tenses",
            "vocabulary",
            "synonyms",
            "antonyms",
            "reported speech",
            "passive voice",
            "conditionals",
            "comprehension",
            "articles",
            "parts of speech",
        }
    ]
    topics.sort()
    return (
        "English topics: " + ", ".join(topics) + ".\n"
        "Example: practice english passive voice"
    )


def learning_pack_download(request, slug):
    pack = _get_learning_pack(slug)
    if not pack:
        raise Http404("Learning pack not found.")

    if isinstance(pack, dict):
        title = pack["title"]
        content = pack["content"]
    else:
        title = pack.title
        content = pack.content

    response = HttpResponse(content, content_type="text/plain; charset=utf-8")
    filename = slug.replace("/", "-")
    response["Content-Disposition"] = f'attachment; filename="{filename}.txt"'
    response["X-Pack-Title"] = title
    return response


def audio_pack_transcript_download(request, slug):
    pack = _get_audio_pack(slug)
    if not pack:
        raise Http404("Audio pack not found.")

    if isinstance(pack, dict):
        transcript = pack["transcript"]
    else:
        transcript = pack.transcript

    response = HttpResponse(transcript, content_type="text/plain; charset=utf-8")
    filename = slug.replace("/", "-")
    response["Content-Disposition"] = f'attachment; filename="{filename}-transcript.txt"'
    return response


@csrf_exempt
def whatsapp_webhook(request):
    """
    Webhook to receive WhatsApp messages via Twilio,
    send them to OpenAI GPT, and return the response.
    """
    if request.method == "POST":
        incoming_msg = request.POST.get('Body', '').strip()
        from_number = request.POST.get('From', '')
        print(f"Message from {from_number}: {incoming_msg}")
        progress = _get_or_create_progress(from_number or "unknown")

        resp = MessagingResponse()
        msg = resp.message()

        if incoming_msg:
            try:
                normalized_msg = incoming_msg.lower()
                if normalized_msg in GREETING_MESSAGES:
                    reply = (
                        "Hello! Ask a question, send 'practice maths', or send 'progress'."
                    )
                elif normalized_msg in HELP_MESSAGES:
                    reply = _help_text(low_data=progress.low_data_mode)
                elif normalized_msg in OFFLINE_ON_MESSAGES:
                    reply = _set_offline_mode(progress, True)
                elif normalized_msg in OFFLINE_OFF_MESSAGES:
                    reply = _set_offline_mode(progress, False)
                elif normalized_msg in OFFLINE_STATUS_MESSAGES:
                    reply = _offline_status_text(progress)
                elif normalized_msg in LOW_DATA_ON_MESSAGES:
                    reply = _set_low_data_mode(progress, True)
                elif normalized_msg in LOW_DATA_OFF_MESSAGES:
                    reply = _set_low_data_mode(progress, False)
                elif normalized_msg in AUDIO_PACK_MESSAGES or normalized_msg.startswith("audio packs "):
                    requested_audio_subject = _extract_pack_subject(normalized_msg)
                    reply = _list_audio_packs(subject=requested_audio_subject)
                elif normalized_msg in PACK_MESSAGES or normalized_msg.startswith("packs "):
                    requested_pack_subject = _extract_pack_subject(normalized_msg)
                    reply = _list_learning_packs(subject=requested_pack_subject)
                elif normalized_msg.startswith("audio pack ") or normalized_msg.startswith("get audio pack ") or normalized_msg.startswith("audio lesson "):
                    audio_pack_query = _extract_audio_pack_query(normalized_msg)
                    audio_pack = _get_audio_pack(audio_pack_query) if audio_pack_query else None
                    if audio_pack:
                        reply = _audio_pack_reply(
                            audio_pack,
                            base_url=_get_request_base_url(request),
                            low_data=progress.low_data_mode,
                        )
                    else:
                        reply = "I could not find that audio pack. Send 'audio packs' to see available audio packs."
                elif normalized_msg.startswith("pack ") or normalized_msg.startswith("get pack "):
                    pack_query = _extract_pack_query(normalized_msg)
                    pack = _get_learning_pack(pack_query) if pack_query else None
                    if pack:
                        reply = _learning_pack_reply(
                            pack,
                            base_url=_get_request_base_url(request),
                            low_data=progress.low_data_mode,
                        )
                    else:
                        reply = "I could not find that pack. Send 'packs' to see available packs."
                elif normalized_msg in TOPIC_MESSAGES:
                    reply = _english_topics_text()
                elif normalized_msg in EXIT_MESSAGES:
                    _clear_practice_state(progress)
                    reply = "Practice stopped. Ask any study question or send 'practice' to start again."
                elif normalized_msg in PROGRESS_MESSAGES:
                    reply = _build_progress_summary(progress)
                elif normalized_msg in PRACTICE_MESSAGES or normalized_msg.startswith("practice "):
                    requested_subject = _extract_practice_subject(normalized_msg)
                    requested_difficulty = _extract_difficulty(normalized_msg)
                    requested_topic = _extract_requested_topic(normalized_msg, requested_subject)
                    if _should_reset_for_new_practice(
                        progress,
                        requested_subject,
                        requested_difficulty,
                        requested_topic,
                    ):
                        _reset_session(progress)
                    reply = _start_practice(
                        progress,
                        subject=requested_subject,
                        difficulty=requested_difficulty,
                        topic=requested_topic,
                    )
                elif progress.awaiting_practice_answer and _looks_like_general_question(incoming_msg):
                    _clear_practice_state(progress)
                    if progress.offline_mode:
                        reply = _offline_study_reply(
                            incoming_msg,
                            progress,
                            base_url=_get_request_base_url(request),
                        )
                    else:
                        reply = ask_ai(incoming_msg, low_data=progress.low_data_mode)
                elif progress.awaiting_practice_answer:
                    reply = _grade_practice_answer(progress, incoming_msg)
                elif progress.offline_mode:
                    reply = _offline_study_reply(
                        incoming_msg,
                        progress,
                        base_url=_get_request_base_url(request),
                    )
                else:
                    reply = ask_ai(incoming_msg, low_data=progress.low_data_mode)
            except Exception as e:
                print("Gemini Error:", e)
                reply = _offline_study_reply(
                    incoming_msg,
                    progress,
                    base_url=_get_request_base_url(request),
                )
        else:
            reply = "Hi! Please send a message so I can help you."

        msg.body(_compact_reply(reply))
        return HttpResponse(str(resp), content_type="application/xml")

    # For GET requests or others
    return HttpResponse("Hello, this endpoint is for WhatsApp messages only.")
