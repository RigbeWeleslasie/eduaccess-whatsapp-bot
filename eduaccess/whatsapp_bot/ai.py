# whatsapp_bot/ai.py
import json
import math
import os
import random
import re
from pathlib import Path
from urllib import error, request

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

TUTOR_SYSTEM_PROMPT = """
You are EduAccess, a patient and accurate tutor for secondary school learners.

Rules:
- Always answer the student's question directly.
- If the question is about maths or science, explain the idea in simple steps.
- If the question is short or slightly unclear, make the best reasonable interpretation and answer it.
- Only ask a clarifying question if the request is too ambiguous to answer.
- Keep replies concise, clear, and easy to read on WhatsApp.
- Use short paragraphs or bullet points when helpful.
- If the student asks for a definition, start with a plain-language definition, then give a short example.

Example:
Question: What does derivative mean in calculus?
Answer: In calculus, a derivative shows how fast one quantity changes compared to another. It is the slope or gradient of a curve at a specific point. For example, if distance changes with time, the derivative tells you the speed.
""".strip()

GRAPH_KEYWORDS = {
    "graph",
    "diagram",
    "plot",
    "sketch",
    "draw",
    "curve",
    "axis",
    "axes",
}

GRAPH_SYSTEM_PROMPT = """
You are EduAccess, a tutor helping students over WhatsApp text.

The platform may not support real image generation for this request, so when a student asks for a graph or diagram:
- Provide a simple ASCII sketch when possible.
- Label the axes clearly.
- Name key points such as intercepts, turning points, or gradients when relevant.
- Keep the sketch readable in plain text on a phone screen.
- After the sketch, add a brief explanation of what the student is seeing.
- If the exact graph is unclear, make the best reasonable interpretation and state it briefly.

Example style:
y
^
|      *
|    *   *
|  *       *
+------------------> x

This sketch shows a curve opening upward.
""".strip()

ALLOWED_EXPR_PATTERN = re.compile(r"^[0-9x+\-*/().^ \t]+$")
MVP_SUBJECTS = ("english", "maths")
PRACTICE_LEVELS = ("foundation", "core", "stretch")
MAX_CACHE_ENTRIES = 128
_RESPONSE_CACHE = {}
ENGLISH_PRACTICE_PROMPT = (
    "Generate only easy-to-grade English practice. "
    "Use one of these formats only: "
    "1. Fill in the blank with a single correct word. "
    "2. Choose the correct option from A, B, C. "
    "3. Give the correct tense, synonym, antonym, or part of speech with one short answer. "
    "The answer must be short and unambiguous. "
    "Do not ask open-ended composition, essay, or explanation questions. "
    "If you use options, include the full option text in the question and return the correct answer as both the option letter and word separated by |. "
    "Example answer format: B|went."
)
MATHS_PRACTICE_PROMPT = (
    "Generate short, clear maths practice that can be answered in one line. "
    "Use direct numeric or short-expression answers."
)
LOCAL_PRACTICE_BANK = {
    "english": {
        "foundation": [
            (
                "Verb tense",
                "Choose the correct word: By the time the bell rang, the students had already ___ their notes. A. pack B. packed C. packing",
                "B|packed",
            ),
            (
                "Subject-verb agreement",
                "Fill in the blank: Neither of the boys ___ ready for the debate. A. are B. were C. was",
                "C|was",
            ),
            (
                "Articles",
                "Fill in the blank: The principal gave us ___ important announcement during assembly.",
                "an",
            ),
            (
                "Vocabulary",
                "Choose the synonym of 'diligent'. A. lazy B. careful C. hardworking",
                "C|hardworking",
            ),
            (
                "Antonyms",
                "Choose the opposite of 'scarce'. A. limited B. plentiful C. empty",
                "B|plentiful",
            ),
        ],
        "core": [
            (
                "Reported speech",
                "Choose the correct reported speech: The teacher said, 'Open your books.' A. The teacher said that open your books. B. The teacher told us to open our books. C. The teacher says open your books.",
                "B|the teacher told us to open our books",
            ),
            (
                "Parts of speech",
                "What part of speech is the word 'carefully' in this sentence: The student carefully drew the graph?",
                "adverb",
            ),
            (
                "Sentence correction",
                "Choose the correct sentence. A. She don't like Chemistry. B. She doesn't like Chemistry. C. She didn't likes Chemistry.",
                "B|she doesn't like chemistry",
            ),
            (
                "Comprehension",
                "In the sentence 'The committee postponed the trip because the roads were flooded,' why was the trip postponed? A. The bus broke down B. The roads were flooded C. The committee was absent",
                "B|the roads were flooded",
            ),
        ],
        "stretch": [
            (
                "Conditional sentences",
                "Choose the correct sentence. A. If I had revised earlier, I would pass the exam. B. If I had revised earlier, I would have passed the exam. C. If I revised earlier, I would have passed the exam.",
                "B|if i had revised earlier i would have passed the exam",
            ),
            (
                "Sentence transformation",
                "Rewrite in reported speech: Musa said, 'I will submit the assignment tomorrow.'",
                "musa said that he would submit the assignment the following day",
            ),
            (
                "Passive voice",
                "Change to passive voice: 'The students solved the problem.'",
                "the problem was solved by the students",
            ),
        ],
    },
    "maths": {
        "foundation": [
            ("Integers", "Evaluate: -4 + 11", "7"),
            ("Fractions", "What is 3/5 of 20?", "12"),
            ("Algebra", "Solve for x: x + 7 = 15", "8"),
            ("Percentages", "What is 15% of 200?", "30"),
        ],
        "core": [
            ("Linear equations", "Solve for x: 3x - 5 = 16", "7"),
            ("Simultaneous equations", "Find x if x + y = 10 and y = 4", "6"),
            ("Geometry", "What is the area of a triangle with base 10 cm and height 6 cm?", "30"),
            ("Statistics", "Find the mean of 4, 6, 8, 12", "7.5"),
        ],
        "stretch": [
            ("Quadratic equations", "Solve for x: x^2 - 9 = 0. Give the positive value.", "3"),
            ("Trigonometry", "In a right-angled triangle, if opposite = 3 and adjacent = 4, what is tan(theta)?", "3/4"),
            ("Indices", "Simplify: 2^3 x 2^4", "128"),
            ("Circle geometry", "What is the circumference of a circle of radius 7 cm? Use pi = 22/7.", "44"),
        ],
    },
}
ENGLISH_TOPIC_ALIASES = {
    "grammar": {
        "Subject-verb agreement",
        "Sentence correction",
        "Parts of speech",
        "Articles",
    },
    "tenses": {"Verb tense"},
    "vocabulary": {"Vocabulary", "Antonyms"},
    "synonyms": {"Vocabulary"},
    "antonyms": {"Antonyms"},
    "reported speech": {"Reported speech"},
    "passive voice": {"Passive voice"},
    "conditionals": {"Conditional sentences"},
    "transformation": {"Sentence transformation"},
    "parts of speech": {"Parts of speech"},
    "articles": {"Articles"},
    "comprehension": {"Comprehension"},
}
CURRICULUM_TOPICS = {
    "english": [
        "Articles",
        "Subject-verb agreement",
        "Verb tense",
        "Vocabulary",
        "Antonyms",
        "Reported speech",
        "Parts of speech",
        "Sentence correction",
        "Comprehension",
        "Conditional sentences",
        "Sentence transformation",
        "Passive voice",
    ],
    "maths": [
        "Integers",
        "Fractions",
        "Algebra",
        "Percentages",
        "Linear equations",
        "Simultaneous equations",
        "Geometry",
        "Statistics",
        "Indices",
        "Quadratic equations",
        "Trigonometry",
        "Circle geometry",
    ],
}
LOCAL_LEARNING_PACKS = [
    {
        "slug": "maths-algebra-basics",
        "subject": "maths",
        "topic": "Algebra",
        "title": "Algebra Basics Pack",
        "summary": "Variables, simple equations, and quick examples.",
        "content": (
            "ALGEBRA BASICS\n"
            "1. A variable is a letter that stands for an unknown value.\n"
            "2. An expression joins numbers and variables, for example 3x + 2.\n"
            "3. An equation says two expressions are equal, for example x + 7 = 15.\n"
            "4. To solve an equation, do the same operation to both sides.\n"
            "Example:\n"
            "x + 7 = 15\n"
            "Subtract 7 from both sides.\n"
            "x = 8\n"
            "Quick check:\n"
            "If 2x = 18, then x = 9.\n"
            "Revision tip: isolate the variable step by step."
        ),
    },
    {
        "slug": "maths-fractions-core",
        "subject": "maths",
        "topic": "Fractions",
        "title": "Fractions Core Pack",
        "summary": "Equivalent fractions, operations, and mixed practice.",
        "content": (
            "FRACTIONS CORE PACK\n"
            "1. Equivalent fractions name the same value, for example 1/2 = 2/4.\n"
            "2. To add fractions with the same denominator, add the numerators.\n"
            "3. To add fractions with different denominators, first find a common denominator.\n"
            "Example:\n"
            "1/2 + 1/4 = 2/4 + 1/4 = 3/4\n"
            "4. To find a fraction of a quantity, multiply.\n"
            "Example:\n"
            "3/5 of 20 = 12\n"
            "Revision tip: simplify your final answer if possible."
        ),
    },
    {
        "slug": "english-reported-speech",
        "subject": "english",
        "topic": "Reported speech",
        "title": "Reported Speech Pack",
        "summary": "How direct speech changes into reported speech.",
        "content": (
            "REPORTED SPEECH\n"
            "1. Reported speech tells what someone said without quoting the exact words.\n"
            "2. Pronouns and time words may change.\n"
            "Direct: The teacher said, 'Open your books.'\n"
            "Reported: The teacher told us to open our books.\n"
            "3. Present forms often shift back in tense.\n"
            "Direct: Amina said, 'I am tired.'\n"
            "Reported: Amina said that she was tired.\n"
            "4. Tomorrow can become the following day.\n"
            "Revision tip: check the reporting verb, pronoun, tense, and time word."
        ),
    },
    {
        "slug": "english-passive-voice",
        "subject": "english",
        "topic": "Passive voice",
        "title": "Passive Voice Pack",
        "summary": "Turning active sentences into passive voice.",
        "content": (
            "PASSIVE VOICE\n"
            "1. In active voice, the subject performs the action.\n"
            "2. In passive voice, the receiver of the action becomes the focus.\n"
            "Active: The students solved the problem.\n"
            "Passive: The problem was solved by the students.\n"
            "3. Use the correct form of 'be' plus the past participle.\n"
            "Present example: The class writes notes. -> Notes are written by the class.\n"
            "Past example: The class wrote notes. -> Notes were written by the class.\n"
            "Revision tip: keep the tense the same when changing active to passive."
        ),
    },
]
LOCAL_AUDIO_PACKS = [
    {
        "slug": "audio-maths-algebra-basics",
        "subject": "maths",
        "topic": "Algebra",
        "title": "Algebra Audio Pack",
        "summary": "A short spoken-style revision on algebra basics.",
        "duration_label": "2 min",
        "audio_url": "",
        "transcript": (
            "Algebra basics. A variable is a letter that stands for an unknown value. "
            "For example, in x plus 7 equals 15, x is the unknown. "
            "To solve the equation, subtract 7 from both sides. "
            "That gives x equals 8. "
            "Always do the same operation on both sides of the equation."
        ),
    },
    {
        "slug": "audio-maths-fractions-core",
        "subject": "maths",
        "topic": "Fractions",
        "title": "Fractions Audio Pack",
        "summary": "A short audio-style guide to equivalent fractions and addition.",
        "duration_label": "2 min",
        "audio_url": "",
        "transcript": (
            "Fractions revision. Equivalent fractions name the same amount. "
            "One half is the same as two quarters. "
            "When adding fractions with different denominators, first change them to a common denominator. "
            "For example, one half plus one quarter becomes two quarters plus one quarter, which equals three quarters."
        ),
    },
    {
        "slug": "audio-english-reported-speech",
        "subject": "english",
        "topic": "Reported speech",
        "title": "Reported Speech Audio Pack",
        "summary": "A short spoken explanation of how to change direct speech.",
        "duration_label": "2 min",
        "audio_url": "",
        "transcript": (
            "Reported speech tells us what someone said without repeating the exact words. "
            "For example, direct speech says, the teacher said, open your books. "
            "Reported speech becomes, the teacher told us to open our books. "
            "Watch for changes in pronouns, tense, and time words."
        ),
    },
    {
        "slug": "audio-english-passive-voice",
        "subject": "english",
        "topic": "Passive voice",
        "title": "Passive Voice Audio Pack",
        "summary": "A short audio-style lesson on changing active voice to passive voice.",
        "duration_label": "2 min",
        "audio_url": "",
        "transcript": (
            "Passive voice focuses on the receiver of the action. "
            "Active voice says, the students solved the problem. "
            "Passive voice says, the problem was solved by the students. "
            "Use the correct form of be together with the past participle."
        ),
    },
]


def _local_practice_question(subject, difficulty, topic=None):
    subject_bank = LOCAL_PRACTICE_BANK.get(subject, {})
    if topic:
        requested_topic = topic.lower()
        allowed_topics = {topic}
        if subject == "english":
            alias_topics = ENGLISH_TOPIC_ALIASES.get(requested_topic)
            if alias_topics:
                allowed_topics = alias_topics

        for bank_difficulty in (difficulty, "foundation", "core", "stretch"):
            difficulty_bank = subject_bank.get(bank_difficulty, [])
            topic_matches = [
                item for item in difficulty_bank
                if item[0] in allowed_topics or requested_topic in item[0].lower()
            ]
            if topic_matches:
                return random.choice(topic_matches)

    difficulty_bank = subject_bank.get(difficulty, [])
    if not difficulty_bank:
        return None

    return random.choice(difficulty_bank)


def get_practice_topics(subject):
    subject_bank = LOCAL_PRACTICE_BANK.get(subject, {})
    topics = set()
    for questions in subject_bank.values():
        for topic, _, _ in questions:
            topics.add(topic)
    if subject == "english":
        topics.update(ENGLISH_TOPIC_ALIASES.keys())
    return sorted(topics)


def get_curriculum_topics(subject):
    return CURRICULUM_TOPICS.get(subject, [])


def get_learning_packs(subject=None):
    packs = LOCAL_LEARNING_PACKS
    if subject:
        packs = [pack for pack in packs if pack["subject"] == subject]
    return packs


def get_learning_pack_by_slug_or_topic(query):
    lowered_query = query.strip().lower()
    for pack in LOCAL_LEARNING_PACKS:
        if pack["slug"] == lowered_query or pack["topic"].lower() == lowered_query:
            return pack
    return None


def get_audio_packs(subject=None):
    packs = LOCAL_AUDIO_PACKS
    if subject:
        packs = [pack for pack in packs if pack["subject"] == subject]
    return packs


def get_audio_pack_by_slug_or_topic(query):
    lowered_query = query.strip().lower()
    for pack in LOCAL_AUDIO_PACKS:
        if pack["slug"] == lowered_query or pack["topic"].lower() == lowered_query:
            return pack
    return None


def _extract_text(response_data):
    candidates = response_data.get("candidates", [])
    for candidate in candidates:
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        text_chunks = [part.get("text", "") for part in parts if part.get("text")]
        if text_chunks:
            return "".join(text_chunks).strip()
    return ""


def _call_gemini(user_prompt, system_prompt=None, max_output_tokens=220):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set.")

    cache_key = (system_prompt or "", user_prompt, max_output_tokens)
    cached_response = _RESPONSE_CACHE.get(cache_key)
    if cached_response:
        return cached_response

    contents = [{"role": "user", "parts": [{"text": user_prompt}]}]

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "topP": 0.9,
            "maxOutputTokens": max_output_tokens,
        },
    }
    if system_prompt:
        payload["systemInstruction"] = {
            "parts": [{"text": system_prompt}],
        }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Gemini API error {exc.code}: {error_body}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Gemini network error: {exc.reason}") from exc

    text = _extract_text(response_data)
    if not text:
        raise RuntimeError(f"Gemini returned no text: {response_data}")
    if len(_RESPONSE_CACHE) >= MAX_CACHE_ENTRIES:
        _RESPONSE_CACHE.pop(next(iter(_RESPONSE_CACHE)))
    _RESPONSE_CACHE[cache_key] = text
    return text


def _looks_like_graph_request(question):
    lowered_question = question.lower()
    if any(keyword in lowered_question for keyword in GRAPH_KEYWORDS):
        return True
    return bool(re.search(r"\by\s*=", lowered_question))


def _extract_equation(question):
    match = re.search(r"y\s*=\s*([^\n\r,;]+)", question, flags=re.IGNORECASE)
    if not match:
        return None
    expression = match.group(1).strip()
    expression = re.sub(r"(\d)(x)", r"\1*\2", expression, flags=re.IGNORECASE)
    expression = expression.replace("^", "**")
    if not ALLOWED_EXPR_PATTERN.match(expression):
        return None
    return expression


def _evaluate_expression(expression, x_value):
    safe_globals = {"__builtins__": {}}
    safe_locals = {
        "x": x_value,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "sqrt": math.sqrt,
        "abs": abs,
    }
    return eval(expression, safe_globals, safe_locals)


def _generate_ascii_graph(expression):
    width = 21
    height = 21
    x_values = list(range(-10, 11))
    plotted_points = set()

    for x_value in x_values:
        try:
            y_value = _evaluate_expression(expression, x_value)
        except Exception:
            return None
        if isinstance(y_value, complex):
            return None
        if not math.isfinite(y_value):
            continue
        rounded_y = int(round(y_value))
        if -10 <= rounded_y <= 10:
            plotted_points.add((x_value, rounded_y))

    if not plotted_points:
        return None

    rows = []
    for y_value in range(10, -11, -1):
        row_chars = []
        for x_value in range(-10, 11):
            point = (x_value, y_value)
            if point in plotted_points:
                row_chars.append("*")
            elif x_value == 0 and y_value == 0:
                row_chars.append("+")
            elif x_value == 0:
                row_chars.append("|")
            elif y_value == 0:
                row_chars.append("-")
            else:
                row_chars.append(" ")
        rows.append(f"{y_value:>3} {''.join(row_chars)}")

    axis_footer = "    " + "".join("^" if x == 0 else " " for x in range(-10, 11))
    x_label = "      -10         x         10"
    return "\n".join(rows + [axis_footer, x_label])


def _answer_graph_request(question, low_data=False):
    expression = _extract_equation(question)
    if expression:
        ascii_graph = _generate_ascii_graph(expression)
        if ascii_graph:
            return (
                f"Here is the graph of y = {expression.replace('**', '^')}:\n"
                f"```text\n{ascii_graph}\n```\n"
                "The vertical line is the y-axis and the horizontal line is the x-axis. "
                "The `*` marks points on the graph."
            )

    prompt = (
        "A student is asking for a graph or diagram.\n"
        "Reply with:\n"
        "1. A simple ASCII sketch if possible.\n"
        "2. A short explanation.\n"
        "3. Important labeled points or features.\n\n"
        f"Student question: {question}"
    )
    return _call_gemini(
        prompt,
        system_prompt=GRAPH_SYSTEM_PROMPT,
        max_output_tokens=140 if low_data else 220,
    )


def ask_ai(question, low_data=False):
    cleaned_question = question.strip()
    if _looks_like_graph_request(cleaned_question):
        return _answer_graph_request(cleaned_question, low_data=low_data)

    if low_data:
        prompt = (
            "Answer this student's WhatsApp question very briefly.\n"
            "Use 2 to 4 short sentences.\n"
            "Keep only the most important explanation.\n"
            f"{cleaned_question}"
        )
    else:
        prompt = (
            "Answer this student's WhatsApp question in a clear, helpful way:\n"
            f"{cleaned_question}"
        )
    return _call_gemini(
        prompt,
        system_prompt=TUTOR_SYSTEM_PROMPT,
        max_output_tokens=120 if low_data else 220,
    )


def generate_question(subject=None, topic=None, difficulty="foundation"):
    chosen_subject = (subject or random.choice(MVP_SUBJECTS)).strip().lower()
    if chosen_subject not in MVP_SUBJECTS:
        chosen_subject = "maths"
    chosen_difficulty = (difficulty or "foundation").strip().lower()
    if chosen_difficulty not in PRACTICE_LEVELS:
        chosen_difficulty = "foundation"

    local_question = _local_practice_question(chosen_subject, chosen_difficulty, topic=topic)
    if local_question:
        local_topic, local_question_text, local_answer = local_question
        return local_question_text, local_answer, local_topic

    topic_instruction = ""
    if topic:
        topic_instruction = f"Focus on this topic: {topic}.\n"

    subject_instruction = MATHS_PRACTICE_PROMPT
    if chosen_subject == "english":
        subject_instruction = ENGLISH_PRACTICE_PROMPT

    text = _call_gemini(
        (
            f"Create one secondary school {chosen_subject} practice question.\n"
            f"Difficulty: {chosen_difficulty}.\n"
            f"{topic_instruction}"
            "Return it in exactly this format:\n"
            "Topic: <topic>\n"
            "Question: <question>\n"
            "Answer: <answer>"
        ),
        system_prompt=(
            "Generate a short, clear practice question for the EduAccess MVP. "
            "Use only English or Maths topics. "
            "Do not generate Chemistry, Physics, Biology, or other subjects. "
            "Foundation questions should be very simple, core questions should match standard practice, "
            "and stretch questions should be slightly harder but still concise. "
            f"{subject_instruction}"
        ),
    )

    topic_match = re.search(r"Topic:\s*(.+)", text)
    question_match = re.search(r"Question:\s*(.+)", text)
    answer_match = re.search(r"Answer:\s*(.+)", text)

    topic = topic_match.group(1).strip() if topic_match else chosen_subject.title()
    question = question_match.group(1).strip() if question_match else text.strip()
    answer = answer_match.group(1).strip() if answer_match else "unknown"
    return question, answer, topic
