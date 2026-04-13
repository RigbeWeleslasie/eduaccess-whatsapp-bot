# whatsapp_bot/ai.py
import json
import os
import random
import re
import base64
import math
import time
from datetime import date
from fractions import Fraction
from pathlib import Path
from urllib import error, request

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Tracks the date on which a 429 was received; resets automatically the next day
_gemini_quota_exceeded_date = None


class GeminiQuotaError(RuntimeError):
    """Raised when the Gemini free-tier daily quota is exhausted (HTTP 429)."""


TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

TOPIC_CATALOG = {
    "english": [
        "passive voice",
        "reported speech",
        "adjectives",
        "tenses",
        "vocabulary",
        "parts of speech",
        "comprehension",
        "essay writing",
        "letter writing",
        "conjunctions",
        "direct and indirect speech",
    ],
    "maths": [
        "fractions",
        "algebra",
        "geometry",
        "calculus",
        "linear equations",
        "simultaneous equations",
        "quadratic equations",
        "percentages",
        "ratios",
        "indices",
        "trigonometry",
    ],
}

LOCAL_LEARNING_PACKS = [
    {
        "slug": "maths-algebra-basics",
        "subject": "maths",
        "topic": "Algebra",
        "title": "Algebra Basics Pack",
        "summary": "Starter algebra pack kept as an offline fallback.",
        "content": (
            "ALGEBRA BASICS STUDY PACK\n\n"
            "This offline fallback pack introduces variables, expressions, equations, and the balance method.\n\n"
            "Worked example: x + 7 = 15, so x = 8.\n"
            "Worked example: 3x = 21, so x = 7.\n\n"
            "Revision tip: keep both sides balanced and always check your answer."
        ),
    },
    {
        "slug": "english-passive-voice",
        "subject": "english",
        "topic": "Passive voice",
        "title": "Passive Voice Pack",
        "summary": "Starter passive voice pack kept as an offline fallback.",
        "content": (
            "PASSIVE VOICE STUDY PACK\n\n"
            "This offline fallback pack explains that passive voice focuses on the receiver of the action.\n\n"
            "Pattern: object + form of be + past participle.\n"
            "Example: The chef cooked the meal. -> The meal was cooked by the chef.\n\n"
            "Revision tip: identify the object first, then choose the correct form of be."
        ),
    },
]

LOCAL_AUDIO_PACKS = [
    {
        "slug": "audio-maths-algebra-basics",
        "subject": "maths",
        "topic": "Algebra",
        "title": "Algebra Audio Lesson",
        "summary": "Short offline algebra audio transcript fallback.",
        "transcript": (
            "Welcome to this algebra lesson. Algebra uses letters to represent unknown numbers. "
            "To solve equations, keep both sides balanced and reverse the operation step by step."
        ),
    },
    {
        "slug": "audio-english-passive-voice",
        "subject": "english",
        "topic": "Passive voice",
        "title": "Passive Voice Audio Lesson",
        "summary": "Short offline passive voice audio transcript fallback.",
        "transcript": (
            "Welcome to this passive voice lesson. Passive voice focuses on the receiver of the action. "
            "A common pattern is object plus a form of be plus the past participle."
        ),
    },
]

LOCAL_PRACTICE_QUESTIONS = {
    "maths": [
        ("Solve for x: x + 9 = 14", "x = 5"),
        ("Solve for y: 3y = 18", "y = 6"),
        ("Solve for a: 2a - 4 = 10", "a = 7"),
        ("Solve for b: b/3 = 5", "b = 15"),
        ("Find the value of n: 5n + 2 = 27", "n = 5"),
        ("Simplify: 4/12", "1/3"),
        ("Simplify: 9/15", "3/5"),
        ("What is 3/4 + 1/4?", "1"),
        ("What is 2/3 + 1/6?", "5/6"),
        ("Find 15% of 80.", "12"),
        ("Find 25% of 200.", "50"),
        ("What is 10% of 350?", "35"),
        ("Simplify the ratio 6:9.", "2:3"),
        ("Simplify the ratio 15:25.", "3:5"),
        ("What is 2⁴?", "16"),
        ("Simplify: 3² × 3³", "3⁵ or 243"),
        ("What is the area of a rectangle with length 8 cm and width 5 cm?", "40 cm²"),
        ("How many sides does a hexagon have?", "6"),
        ("What is the perimeter of a square with side 7 cm?", "28 cm"),
        ("What is the sum of angles in a triangle?", "180°"),
        ("What is cos 0°?", "1"),
        ("What is tan 45°?", "1"),
        ("What is sin 30°?", "0.5"),
        ("Solve: x² - 16 = 0", "x = 4 or x = -4"),
        ("Solve: x² + 5x + 6 = 0", "x = -2 or x = -3"),
        ("Solve the pair: x + y = 10 and x - y = 4", "x = 7, y = 3"),
        ("Differentiate: y = 4x³", "dy/dx = 12x²"),
        ("What is the LCM of 4 and 6?", "12"),
        ("What is the HCF of 12 and 18?", "6"),
        ("A car travels 120 km in 2 hours. What is its speed?", "60 km/h"),
        ("Round 3.867 to 2 decimal places.", "3.87"),
        ("Convert 0.75 to a fraction.", "3/4"),
        ("Express 40% as a decimal.", "0.4"),
        ("What is the mean of 4, 8, 6, 10?", "7"),
        ("What is the median of 3, 7, 9, 11, 15?", "9"),
    ],
    "english": [
        # Plurals
        ("Write the plural form of 'child'.", "children"),
        ("Write the plural form of 'tooth'.", "teeth"),
        ("Write the plural form of 'mouse'.", "mice"),
        ("Write the plural form of 'leaf'.", "leaves"),
        ("Write the plural form of 'man'.", "men"),
        ("Write the plural form of 'woman'.", "women"),
        ("Write the plural form of 'foot'.", "feet"),
        ("Write the plural form of 'goose'.", "geese"),
        # Passive voice
        ("Change to passive voice: The chef cooked the meal.", "The meal was cooked by the chef."),
        ("Change to passive voice: The teacher marked the papers.", "The papers were marked by the teacher."),
        ("Change to passive voice: Musa kicked the ball.", "The ball was kicked by Musa."),
        ("Change to passive voice: The farmer planted the seeds.", "The seeds were planted by the farmer."),
        ("Change to active voice: The song was sung by the choir.", "The choir sang the song."),
        ("Change to active voice: The cake was eaten by the children.", "The children ate the cake."),
        # Reported speech
        ('Change to reported speech: She said, "I am happy."', "She said that she was happy."),
        ('Change to reported speech: He said, "I will come tomorrow."', "He said that he would come the next day."),
        ('Change to reported speech: Amina said, "I love reading."', "Amina said that she loved reading."),
        # Tenses
        ("Change to past tense: She walks to school every day.", "She walked to school every day."),
        ("Change to past tense: He plays football.", "He played football."),
        ("Change to future tense: They go to the market.", "They will go to the market."),
        ("Change to present continuous: She read a book.", "She is reading a book."),
        ("Change to past perfect: He eats his food.", "He had eaten his food."),
        # Parts of speech
        ("Identify the noun in this sentence: The teacher praised Musa.", "teacher"),
        ("Identify the verb in this sentence: The dog barked loudly.", "barked"),
        ("Identify the adjective in this sentence: The tall boy ran home.", "tall"),
        ("Identify the adverb in this sentence: She spoke softly.", "softly"),
        ("Identify the pronoun in this sentence: She opened the door.", "She"),
        ("Identify the preposition: The book is on the table.", "on"),
        ("Identify the conjunction: I went to school but my friend stayed home.", "but"),
        ("Identify the interjection: Wow! That was amazing!", "Wow"),
        # Vocabulary / synonyms / antonyms
        ("Give one synonym for 'happy'.", "joyful / cheerful / glad"),
        ("Give one antonym for 'beautiful'.", "ugly"),
        ("Give one synonym for 'big'.", "large / huge / enormous"),
        ("Give one antonym for 'brave'.", "cowardly"),
        ("Give the meaning of 'benevolent'.", "kind and generous"),
        ("Use 'diligent' in a sentence.", "She is a diligent student who always studies hard."),
        # Punctuation / grammar
        ("Add the correct punctuation: Where are you going", "Where are you going?"),
        ("Which is correct: 'its' or 'it's' in: ___ a beautiful day?", "It's"),
        ("Which is correct: 'their', 'there', or 'they're' in: ___ going to the market.", "They're"),
        ("Choose the correct word: She (don't/doesn't) like coffee.", "doesn't"),
        ("Choose the correct form: He (go/goes) to school every day.", "goes"),
        # Comprehension skills
        ("What is the main idea of a paragraph?", "The central or most important point the paragraph is about."),
        ("What does 'skimming' mean when reading a text?", "Reading quickly to get the general idea."),
        ("What does 'scanning' mean when reading a text?", "Looking through text quickly to find specific information."),
        # Essay / letter writing
        ("Name three main parts of an essay.", "Introduction, body, and conclusion."),
        ("What is the purpose of a topic sentence?", "To introduce the main idea of a paragraph."),
        ("What is one feature of a formal letter?", "It uses formal language and includes addresses and a proper greeting."),
        ("What greeting is used in a formal letter to someone whose name you know?", "Dear [Name],"),
        # Conjunctions / connectives
        ("Choose the correct conjunction: I stayed indoors _____ it was raining. (because/and)", "because"),
        ("Choose the correct conjunction: She was tired _____ she kept working. (so/but)", "but"),
        ("Fill in: I will go _____ you come with me. (if/although)", "if"),
    ],
    "general": [
        ("Solve for x: x + 7 = 15", "x = 8"),
        ("Change to active voice: The song was sung by the choir.", "The choir sang the song."),
        ("What is 30% of 90?", "27"),
        ("Give one synonym for 'intelligent'.", "clever / smart"),
        ("What is the plural of 'ox'?", "oxen"),
        ("Solve for x: 4x = 20", "x = 5"),
        ("Identify the verb: The cat sat on the mat.", "sat"),
    ],
}

TOPIC_PRACTICE_QUESTIONS = {
    "english": {
        "passive voice": [
            ("Change to passive voice: The chef cooked the meal.", "The meal was cooked by the chef."),
        ],
        "reported speech": [
            ('Change to reported speech: Amina said, "I am revising now."', "Amina said that she was revising then."),
        ],
        "adjectives": [
            ("Identify the adjective in this sentence: The tall boy ran home.", "tall"),
        ],
        "tenses": [
            ("Change this sentence to the past tense: She walks to school every day.", "She walked to school every day."),
        ],
        "vocabulary": [
            ("Give one synonym for 'happy'.", "joyful"),
        ],
        "parts of speech": [
            ("Identify the noun in this sentence: The teacher praised Musa.", "teacher"),
        ],
        "comprehension": [
            ("What should you do first when answering a comprehension passage question?", "Read the passage carefully."),
        ],
        "essay writing": [
            ("Name one important part of an essay.", "introduction"),
        ],
        "letter writing": [
            ("Write one feature of a formal letter.", "address"),
        ],
        "conjunctions": [
            ("Choose the correct conjunction: I stayed indoors _____ it was raining. (because/and)", "because"),
        ],
        "direct and indirect speech": [
            ('Change to indirect speech: John said, "I am tired."', "John said that he was tired."),
        ],
    },
    "maths": {
        "fractions": [
            ("Simplify: 6/8", "3/4"),
        ],
        "algebra": [
            ("Solve for x: x + 9 = 14", "x = 5"),
        ],
        "geometry": [
            ("How many degrees are in a right angle?", "90"),
        ],
        "calculus": [
            ("Differentiate with respect to x: x^2", "2x"),
        ],
        "linear equations": [
            ("Solve for x: 2x + 3 = 11", "x = 4"),
        ],
        "simultaneous equations": [
            ("Solve: x + y = 7 and x - y = 1", "x = 4, y = 3"),
        ],
        "quadratic equations": [
            ("Solve: x^2 - 9 = 0", "x = 3 or x = -3"),
        ],
        "percentages": [
            ("Find 20% of 50.", "10"),
        ],
        "ratios": [
            ("Simplify the ratio 8:12.", "2:3"),
        ],
        "indices": [
            ("Simplify: 2^3", "8"),
        ],
        "trigonometry": [
            ("What is the sine of 90 degrees?", "1"),
        ],
    },
}

GENERATED_LEARNING_PACKS = {}
GENERATED_AUDIO_PACKS = {}
TOPIC_ALIASES = {
    "linear equation": "linear equations",
    "simultaneous equation": "simultaneous equations",
    "quadratic equation": "quadratic equations",
    "percentage": "percentages",
    "ratio": "ratios",
    "index": "indices",
    "part of speech": "parts of speech",
    "conjunction": "conjunctions",
    "tense": "tenses",
    "adjective": "adjectives",
    "noun": "parts of speech",
    "verb": "parts of speech",
    "indirect speech": "reported speech",
    "direct speech": "direct and indirect speech",
}

LOCAL_TUTOR_KNOWLEDGE = [
    {
        "subject": "maths",
        "keywords": ["derivative", "differentiate", "differentiation", "rate of change"],
        "topic": "calculus",
        "explanation": (
            "Differentiation finds the rate at which a function changes.\n\n"
            "The basic rule: if y = xⁿ, then dy/dx = nxⁿ⁻¹\n\n"
            "Example: y = x³  →  dy/dx = 3x²\n\n"
            "Steps:\n"
            "1. Bring the power down as a multiplier\n"
            "2. Reduce the power by 1\n"
            "3. Simplify\n\n"
            "For a constant (e.g. y = 5), the derivative is 0 because a constant does not change."
        ),
    },
    {
        "subject": "maths",
        "keywords": ["linear equation", "linear equations", "solve for x", "unknown value"],
        "topic": "linear equations",
        "explanation": (
            "A linear equation has one unknown (usually x) and no powers higher than 1.\n\n"
            "Rule: whatever you do to one side, do the same to the other side.\n\n"
            "Example: 2x + 5 = 11\n"
            "  Subtract 5 from both sides: 2x = 6\n"
            "  Divide both sides by 2: x = 3\n\n"
            "Always check by substituting back: 2(3) + 5 = 11 ✓"
        ),
    },
    {
        "subject": "maths",
        "keywords": ["algebra", "expression", "equation"],
        "topic": "algebra",
        "explanation": (
            "Algebra uses letters (like x or y) to represent unknown numbers.\n\n"
            "Key rules:\n"
            "- Like terms can be added: 3x + 2x = 5x\n"
            "- Unlike terms cannot: 3x + 2y stays as 3x + 2y\n"
            "- To solve for x, isolate it on one side\n\n"
            "Example: 3x - 4 = 11\n"
            "  Add 4 to both sides: 3x = 15\n"
            "  Divide by 3: x = 5"
        ),
    },
    {
        "subject": "maths",
        "keywords": ["fraction", "fractions", "numerator", "denominator"],
        "topic": "fractions",
        "explanation": (
            "A fraction shows a part of a whole. The top number is the numerator, the bottom is the denominator.\n\n"
            "Adding fractions: make the denominators the same first.\n"
            "  1/4 + 1/2 = 1/4 + 2/4 = 3/4\n\n"
            "Multiplying fractions: multiply top × top and bottom × bottom.\n"
            "  2/3 × 3/4 = 6/12 = 1/2\n\n"
            "Dividing fractions: flip the second fraction and multiply.\n"
            "  2/3 ÷ 4/5 = 2/3 × 5/4 = 10/12 = 5/6"
        ),
    },
    {
        "subject": "maths",
        "keywords": ["percentage", "percentages", "percent"],
        "topic": "percentages",
        "explanation": (
            "A percentage is a number out of 100.\n\n"
            "To find a percentage of an amount:\n"
            "  15% of 200 = (15 ÷ 100) × 200 = 30\n\n"
            "To convert a fraction to a percentage:\n"
            "  3/4 = (3 ÷ 4) × 100 = 75%\n\n"
            "Percentage increase/decrease:\n"
            "  Increase 80 by 20%: 80 × 1.20 = 96\n"
            "  Decrease 80 by 20%: 80 × 0.80 = 64"
        ),
    },
    {
        "subject": "maths",
        "keywords": ["ratio", "ratios"],
        "topic": "ratios",
        "explanation": (
            "A ratio compares two or more quantities.\n\n"
            "Example: ratio 3:2 means for every 3 of one thing, there are 2 of another.\n\n"
            "Sharing in a ratio:\n"
            "  Share 40 in the ratio 3:2\n"
            "  Total parts = 3 + 2 = 5\n"
            "  One part = 40 ÷ 5 = 8\n"
            "  Shares: 3 × 8 = 24 and 2 × 8 = 16\n\n"
            "Always simplify ratios where possible: 6:4 = 3:2"
        ),
    },
    {
        "subject": "maths",
        "keywords": ["trigonometry", "sine", "cosine", "tangent"],
        "topic": "trigonometry",
        "explanation": (
            "Trigonometry studies the relationship between angles and sides in right-angled triangles.\n\n"
            "The three main ratios (remember SOH-CAH-TOA):\n"
            "  sin(θ) = Opposite ÷ Hypotenuse\n"
            "  cos(θ) = Adjacent ÷ Hypotenuse\n"
            "  tan(θ) = Opposite ÷ Adjacent\n\n"
            "Example: In a right triangle with angle 30°, hypotenuse = 10:\n"
            "  Opposite = sin(30°) × 10 = 0.5 × 10 = 5"
        ),
    },
    {
        "subject": "english",
        "keywords": ["passive voice", "active voice"],
        "topic": "passive voice",
        "explanation": (
            "Passive voice shifts the focus from who does the action to what receives the action.\n\n"
            "Active:  The teacher marked the papers.\n"
            "Passive: The papers were marked by the teacher.\n\n"
            "How to form the passive:\n"
            "  Subject + to be (correct tense) + past participle\n\n"
            "More examples:\n"
            "  Active:  They built the bridge in 1990.\n"
            "  Passive: The bridge was built in 1990.\n\n"
            "  Active:  Someone has stolen my bag.\n"
            "  Passive: My bag has been stolen.\n\n"
            "Use passive voice when the doer is unknown, unimportant, or obvious from context."
        ),
    },
    {
        "subject": "english",
        "keywords": ["reported speech", "indirect speech", "direct speech"],
        "topic": "reported speech",
        "explanation": (
            "Reported speech conveys what someone said without quoting them directly.\n\n"
            "Direct:   She said, \"I am tired.\"\n"
            "Reported: She said that she was tired.\n\n"
            "Key changes when reporting:\n"
            "  am/is → was,  are → were\n"
            "  will → would,  can → could\n"
            "  now → then,  today → that day,  here → there\n\n"
            "For questions:\n"
            "  Direct:   He asked, \"Where do you live?\"\n"
            "  Reported: He asked where I lived.\n\n"
            "Note: no question mark in reported questions, and word order becomes normal (subject before verb)."
        ),
    },
    {
        "subject": "english",
        "keywords": ["adjective", "adjectives"],
        "topic": "adjectives",
        "explanation": (
            "Adjectives describe or modify nouns.\n\n"
            "Examples: a tall building, a cold day, the red car\n\n"
            "Order of adjectives (before a noun):\n"
            "  Opinion → Size → Age → Shape → Colour → Origin → Material\n"
            "  e.g. a lovely small old round brown French wooden box\n\n"
            "Comparative (comparing two): taller, more expensive\n"
            "Superlative (comparing three or more): tallest, most expensive\n\n"
            "Adjectives can also follow a linking verb:\n"
            "  The soup is hot. She feels tired."
        ),
    },
    {
        "subject": "english",
        "keywords": ["tense", "tenses", "past tense", "present tense", "future tense"],
        "topic": "tenses",
        "explanation": (
            "Tenses show when an action happens.\n\n"
            "Simple Present: I walk to school. (routine or fact)\n"
            "Present Continuous: I am walking. (happening now)\n"
            "Simple Past: I walked yesterday. (completed action)\n"
            "Past Continuous: I was walking when it rained. (ongoing past action)\n"
            "Present Perfect: I have walked 5 km. (past action with present relevance)\n"
            "Simple Future: I will walk tomorrow. (future plan)\n\n"
            "Tip: the auxiliary verb (am/is/are/was/were/have/will) tells you the tense."
        ),
    },
    {
        "subject": "english",
        "keywords": ["noun", "nouns", "verb", "verbs", "conjunction", "conjunctions"],
        "topic": "parts of speech",
        "explanation": (
            "Parts of speech are the categories every word belongs to.\n\n"
            "Noun: names a person, place, or thing. (teacher, Lagos, happiness)\n"
            "Verb: shows an action or state. (run, think, is)\n"
            "Adjective: describes a noun. (tall, happy, red)\n"
            "Adverb: modifies a verb, adjective, or other adverb. (quickly, very, well)\n"
            "Pronoun: replaces a noun. (he, she, they, it)\n"
            "Preposition: shows relationship. (in, on, at, before)\n"
            "Conjunction: joins words or clauses. (and, but, because, although)\n"
            "Interjection: an exclamation. (Oh! Wow! Yes!)"
        ),
    },
]


def _extract_text(response_data):
    candidates = response_data.get("candidates", [])
    for candidate in candidates:
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        text_chunks = [part.get("text", "") for part in parts if part.get("text")]
        if text_chunks:
            return "".join(text_chunks).strip()
    return ""


def _call_gemini(user_prompt, system_prompt=None):
    global _gemini_quota_exceeded_date
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set.")
    if _gemini_quota_exceeded_date == date.today():
        raise GeminiQuotaError("Gemini daily quota already exhausted — skipping call.")

    contents = []
    if system_prompt:
        contents.append(
            {
                "role": "user",
                "parts": [{"text": f"System instruction: {system_prompt}"}],
            }
        )
    contents.append({"role": "user", "parts": [{"text": user_prompt}]})

    payload = {"contents": contents}
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

    _transient_codes = {500, 502, 503, 504}
    _max_retries = 3
    _backoff = 2  # seconds, doubles each attempt

    for attempt in range(_max_retries):
        try:
            with request.urlopen(req, timeout=30) as response:
                response_data = json.loads(response.read().decode("utf-8"))
            break  # success
        except error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 429:
                _gemini_quota_exceeded_date = date.today()
                raise GeminiQuotaError(f"Gemini API error {exc.code}: {error_body}") from exc
            if exc.code in _transient_codes and attempt < _max_retries - 1:
                time.sleep(_backoff * (2 ** attempt))
                # Rebuild request body since urlopen consumes it
                req = request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                continue
            raise RuntimeError(f"Gemini API error {exc.code}: {error_body}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Gemini network error: {exc.reason}") from exc

    text = _extract_text(response_data)
    if not text:
        raise RuntimeError(f"Gemini returned no text: {response_data}")
    return text


def _extract_json_object(payload_text):
    try:
        return json.loads(payload_text)
    except json.JSONDecodeError:
        json_match = re.search(r"\{.*\}", payload_text, re.DOTALL)
        if not json_match:
            return None
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return None


def _parse_question_answer_text(text):
    normalized = text.strip()
    if "Answer:" in normalized:
        question, answer = normalized.split("Answer:", 1)
        return question.strip(), answer.strip()

    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    if len(lines) >= 2:
        return lines[0], lines[-1]

    return normalized, "unknown"


def _cache_generated_learning_pack(pack):
    GENERATED_LEARNING_PACKS[pack["slug"]] = pack
    GENERATED_LEARNING_PACKS[_normalize_topic_key(pack["topic"])] = pack
    return pack


def _cache_generated_audio_pack(pack):
    GENERATED_AUDIO_PACKS[pack["slug"]] = pack
    GENERATED_AUDIO_PACKS[_normalize_topic_key(pack["topic"])] = pack
    return pack


_SENTENCE_ANALYSIS_MARKERS = (
    "in here", "in this sentence", "in the sentence", "in this example",
    "in the above", "in the following", "find the", "identify the",
    "identify all", "spot the", "underline the", "what is the",
    "which word", "which words", "is there a", "are there any",
)


def is_sentence_analysis_question(question):
    """True when the student is asking about a specific sentence, not a general topic."""
    normalized = question.strip().lower()
    if any(m in normalized for m in _SENTENCE_ANALYSIS_MARKERS):
        return True
    # Pattern: "some sentence, what/which/find..." — comma before a question word
    if re.search(r".{10,},\s*(what|which|find|identify|is there|are there|how many)", normalized):
        return True
    return False


def ask_ai(question, subject=None, topic=None):
    resolved_subject = subject or _infer_subject(question)
    resolved_topic = topic or resolve_topic_from_text(question, subject=subject)[1]

    if is_sentence_analysis_question(question):
        # Student is asking about a specific sentence — answer it directly
        prompt = (
            "A student is asking you to analyse a specific sentence or example.\n"
            "Answer their question DIRECTLY and SPECIFICALLY.\n"
            "- Look at the exact sentence or example they provided.\n"
            "- Identify exactly what they are asking for (e.g. the adjective, verb, subject).\n"
            "- If the sentence does not contain what they are looking for, say so clearly.\n"
            "- Give a short, clear answer (2-5 sentences). Do NOT give a general topic lesson.\n"
            "- Do not mention being an AI or talk about the prompt.\n"
            "- Return plain text only.\n\n"
            f"Student question: {question.strip()}"
        )
    else:
        topic_line = f"Target topic: {resolved_topic}\n" if resolved_topic else ""
        subject_line = f"Subject: {resolved_subject}\n" if resolved_subject and resolved_subject != "general" else ""
        prompt = (
            "Answer this student question as a secondary school tutor.\n"
            f"{subject_line}"
            f"{topic_line}"
            f"Question: {question.strip()}\n"
            "Requirements:\n"
            "- Stay on-topic and course-related.\n"
            "- If it is Maths, explain the method step by step.\n"
            "- If it is English, explain the rule clearly and use examples.\n"
            "- Be accurate, supportive, and easy to understand.\n"
            "- Do not mention being an AI or talk about the prompt.\n"
            "- Return plain text only."
        )

    try:
        return _call_gemini(
            prompt,
            system_prompt=(
                "You are EduAccess, a helpful secondary school tutor for English and Maths. "
                "Give direct educational answers that are suitable for students."
            ),
        )
    except GeminiQuotaError:
        return (
            "I'm sorry, the AI tutor has reached its daily limit and will be available again tomorrow. "
            "In the meantime, try the Offline Library for revision packs and audio lessons on your topic."
        )
    except RuntimeError:
        return (
            "The AI tutor is temporarily unavailable due to high demand. "
            "Please try again in a few moments."
        )


def _extension_from_content_type(content_type):
    content_type = (content_type or "").split(";", 1)[0].strip().lower()
    mapping = {
        "audio/ogg": ".ogg",
        "audio/opus": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".mp4",
        "audio/aac": ".aac",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/webm": ".webm",
    }
    return mapping.get(content_type, ".audio")


def download_whatsapp_media(media_url):
    if not media_url:
        raise ValueError("Missing media URL.")

    auth = None
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    response = requests.get(media_url, auth=auth, timeout=30)
    response.raise_for_status()
    return response.content


def transcribe_audio_bytes(audio_bytes, content_type=None):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set.")
    if not audio_bytes:
        raise ValueError("Audio file is empty.")

    mime_type = (content_type or "").split(";", 1)[0].strip().lower() or "audio/ogg"
    if mime_type not in {
        "audio/ogg",
        "audio/opus",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/aac",
        "audio/wav",
        "audio/x-wav",
        "audio/webm",
    }:
        mime_type = "audio/ogg"
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Transcribe this audio message into plain text. "
                            "Return only the transcript with no extra commentary."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(audio_bytes).decode("utf-8"),
                        }
                    },
                ]
            }
        ]
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
        with request.urlopen(req, timeout=60) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini audio transcription error {exc.code}: {error_body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Gemini audio transcription network error: {exc.reason}") from exc

    transcript = _extract_text(response_data).strip()
    if not transcript:
        raise RuntimeError(f"Gemini returned no transcription text: {response_data}")
    return transcript


def transcribe_whatsapp_audio(media_url, content_type=None):
    audio_bytes = download_whatsapp_media(media_url)
    return transcribe_audio_bytes(audio_bytes, content_type=content_type)


def _fraction_to_display(value):
    if value.denominator == 1:
        return str(value.numerator)
    return str(float(value))


def _parse_fraction(value):
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"Invalid number: {value}")


def _parse_linear_expression(expression, variable):
    normalized = expression.replace(" ", "").replace("*", "").replace("−", "-")
    if not normalized:
        raise ValueError("Empty expression")

    terms = re.findall(r"[+-]?[^+-]+", normalized)
    if not terms:
        raise ValueError("No terms found")

    coefficient = Fraction(0)
    constant = Fraction(0)

    for term in terms:
        if variable in term:
            if term.count(variable) != 1:
                raise ValueError("Unsupported variable term")
            if term.endswith(f"{variable}") and "/" not in term:
                factor = term[:-1]
                if factor in {"", "+"}:
                    coefficient += Fraction(1)
                elif factor == "-":
                    coefficient -= Fraction(1)
                else:
                    coefficient += _parse_fraction(factor)
                continue

            division_match = re.fullmatch(
                rf"([+-]?)(?:(\d+(?:\.\d+)?)?)?{re.escape(variable)}/(\d+(?:\.\d+)?)",
                term,
            )
            if division_match:
                sign, numerator, denominator = division_match.groups()
                signed_numerator = numerator or "1"
                if sign == "-":
                    signed_numerator = f"-{signed_numerator}"
                coefficient += _parse_fraction(signed_numerator) / _parse_fraction(denominator)
                continue

            raise ValueError("Unsupported linear term")

        constant += _parse_fraction(term)

    return coefficient, constant


def _parse_quadratic_expression(expression, variable):
    normalized = (
        expression.replace(" ", "")
        .replace("*", "")
        .replace("−", "-")
        .replace("²", "^2")
    )
    if not normalized:
        raise ValueError("Empty expression")

    terms = re.findall(r"[+-]?[^+-]+", normalized)
    if not terms:
        raise ValueError("No terms found")

    quadratic = Fraction(0)
    linear = Fraction(0)
    constant = Fraction(0)

    for term in terms:
        quadratic_match = re.fullmatch(
            rf"([+-]?)(\d+(?:\.\d+)?)?{re.escape(variable)}\^2",
            term,
        )
        if quadratic_match:
            sign, factor = quadratic_match.groups()
            coefficient = factor or "1"
            if sign == "-":
                coefficient = f"-{coefficient}"
            quadratic += _parse_fraction(coefficient)
            continue

        if variable in term:
            if term.count(variable) != 1 or "^" in term:
                raise ValueError("Unsupported variable term")
            if term.endswith(variable):
                factor = term[:-1]
                if factor in {"", "+"}:
                    linear += Fraction(1)
                elif factor == "-":
                    linear -= Fraction(1)
                else:
                    linear += _parse_fraction(factor)
                continue

            raise ValueError("Unsupported linear term")

        constant += _parse_fraction(term)

    return quadratic, linear, constant


_EQUATION_PREFIX = re.compile(
    r"^\s*(?:solve|find|calculate|work\s+out|evaluate|simplify|compute)\s*[:\-]?\s*",
    re.IGNORECASE,
)


def _strip_equation_prefix(text):
    """Remove common instruction words before the actual equation."""
    return _EQUATION_PREFIX.sub("", text).strip()


def looks_like_linear_equation_question(question):
    normalized = _strip_equation_prefix(question).lower()
    if "^2" in normalized or "²" in normalized:
        return False
    if normalized.count("=") != 1:
        return False

    variable_matches = re.findall(r"[a-z]", normalized)
    unique_variables = set(variable_matches)
    if len(unique_variables) != 1:
        return False

    if re.fullmatch(r"\s*[a-z]\s*=\s*[-+]?\d+(?:\.\d+)?\s*", normalized):
        return False
    if re.fullmatch(r"\s*[-+]?\d+(?:\.\d+)?\s*=\s*[a-z]\s*", normalized):
        return False

    return bool(re.search(r"\d", normalized))


def looks_like_quadratic_equation_question(question):
    normalized = _strip_equation_prefix(question).lower().replace("²", "^2")
    if normalized.count("=") != 1:
        return False

    variable_matches = re.findall(r"[a-z]", normalized)
    unique_variables = set(variable_matches)
    if len(unique_variables) != 1:
        return False

    return "^2" in normalized and bool(re.search(r"\d", normalized))


def solve_linear_equation(question):
    if not looks_like_linear_equation_question(question):
        return None

    normalized = _strip_equation_prefix(question).strip().lower().replace("^1", "")
    variable = re.findall(r"[a-z]", normalized)[0]
    left_side, right_side = [part.strip() for part in normalized.split("=", 1)]

    try:
        left_coefficient, left_constant = _parse_linear_expression(left_side, variable)
        right_coefficient, right_constant = _parse_linear_expression(right_side, variable)
    except ValueError:
        return None

    variable_coefficient = left_coefficient - right_coefficient
    constant_value = right_constant - left_constant

    if variable_coefficient == 0:
        if constant_value == 0:
            return (
                "This linear equation has infinitely many solutions because both sides simplify to the same expression."
            )
        return "This linear equation has no solution because the variable terms cancel but the constants do not match."

    answer = constant_value / variable_coefficient
    return (
        "Linear equation solution\n"
        f"Equation: {question.strip()}\n"
        f"Collect like terms: {_fraction_to_display(variable_coefficient)}{variable} = {_fraction_to_display(constant_value)}\n"
        f"Answer: {variable} = {_fraction_to_display(answer)}"
    )


def _format_quadratic_solution_value(value):
    if isinstance(value, int):
        return str(value)
    rounded = round(value, 6)
    if rounded.is_integer():
        return str(int(rounded))
    return str(rounded)


def solve_quadratic_equation(question):
    if not looks_like_quadratic_equation_question(question):
        return None

    normalized = _strip_equation_prefix(question).strip().lower().replace("²", "^2")
    variable = re.findall(r"[a-z]", normalized)[0]
    left_side, right_side = [part.strip() for part in normalized.split("=", 1)]

    try:
        left_quadratic, left_linear, left_constant = _parse_quadratic_expression(left_side, variable)
        right_quadratic, right_linear, right_constant = _parse_quadratic_expression(right_side, variable)
    except ValueError:
        return None

    a = left_quadratic - right_quadratic
    b = left_linear - right_linear
    c = left_constant - right_constant

    if a == 0:
        return None

    discriminant = b * b - (4 * a * c)
    if discriminant < 0:
        return (
            "Quadratic equation solution\n"
            f"Equation: {question.strip()}\n"
            f"Standard form: {_fraction_to_display(a)}{variable}^2 + {_fraction_to_display(b)}{variable} + {_fraction_to_display(c)} = 0\n"
            "This equation has no real-number solution because the discriminant is negative."
        )

    discriminant_value = float(discriminant)
    sqrt_discriminant = math.isqrt(int(discriminant_value)) if discriminant.denominator == 1 else None
    if sqrt_discriminant is not None and sqrt_discriminant * sqrt_discriminant == int(discriminant_value):
        root_one = Fraction(-b + sqrt_discriminant, 2 * a)
        root_two = Fraction(-b - sqrt_discriminant, 2 * a)
        root_one_text = _fraction_to_display(root_one)
        root_two_text = _fraction_to_display(root_two)
    else:
        sqrt_discriminant_float = math.sqrt(discriminant_value)
        denominator = float(2 * a)
        root_one_text = _format_quadratic_solution_value((-float(b) + sqrt_discriminant_float) / denominator)
        root_two_text = _format_quadratic_solution_value((-float(b) - sqrt_discriminant_float) / denominator)

    if root_one_text == root_two_text:
        answer_line = f"Answer: {variable} = {root_one_text}"
    else:
        answer_line = f"Answer: {variable} = {root_one_text} or {variable} = {root_two_text}"

    return (
        "Quadratic equation solution\n"
        f"Equation: {question.strip()}\n"
        f"Standard form: {_fraction_to_display(a)}{variable}^2 + {_fraction_to_display(b)}{variable} + {_fraction_to_display(c)} = 0\n"
        f"{answer_line}"
    )


def build_local_tutor_answer(question):
    normalized = re.sub(r"\s+", " ", question.strip().lower())
    if not normalized:
        return None

    solved_equation = solve_linear_equation(question)
    if solved_equation:
        return {
            "subject": "maths",
            "topic": "linear equations",
            "answer": solved_equation,
        }

    solved_quadratic = solve_quadratic_equation(question)
    if solved_quadratic:
        return {
            "subject": "maths",
            "topic": "quadratic equations",
            "answer": solved_quadratic,
        }

    for entry in LOCAL_TUTOR_KNOWLEDGE:
        if any(_keyword_in_text(keyword, normalized) for keyword in entry["keywords"]):
            topic_title = _titleize_topic(entry["topic"])
            explanation = entry.get("explanation")
            if not explanation:
                if entry["subject"] == "maths":
                    explanation = (
                        f"{topic_title} is a Maths topic. Start by identifying the rule or formula being used, "
                        "work through one example step by step, and then check the final answer carefully."
                    )
                else:
                    explanation = (
                        f"{topic_title} is an English topic. Start with the main rule, study a correct example, "
                        "and then practise writing or changing sentences using the same pattern."
                    )
            return {
                "subject": entry["subject"],
                "topic": entry["topic"],
                "answer": explanation,
            }

    resolved_subject, resolved_topic = resolve_topic_from_text(question)
    if resolved_topic:
        topic_title = _titleize_topic(resolved_topic)
        if resolved_subject == "maths":
            answer = (
                f"{topic_title} is a Maths topic that becomes easier when you learn the main rule, "
                "study one worked example, and then practise similar questions step by step. "
                "Start by identifying what the question is asking, choose the correct rule, and check each stage of your working carefully."
            )
        else:
            answer = (
                f"{topic_title} is an English topic that is best learnt through clear rules, examples, "
                "and sentence practice. Start by understanding the pattern, compare correct and incorrect examples, "
                "and then write a few sentences of your own."
            )
        return {"subject": resolved_subject, "topic": resolved_topic, "answer": answer}

    inferred_subject = _infer_subject(normalized)
    if inferred_subject == "maths":
        return {
            "subject": "maths",
            "topic": None,
            "answer": (
                "This looks like a Maths question. Start by identifying the rule or formula involved, "
                "work through one example carefully, and keep your steps clear and balanced. "
                "If you want, you can also ask the same question with a specific topic such as algebra, fractions, calculus, or linear equations."
            ),
        }
    if inferred_subject == "english":
        return {
            "subject": "english",
            "topic": None,
            "answer": (
                "This looks like an English question. A good approach is to focus on the rule, look at one correct example, "
                "and then practise using it in a full sentence. If you want a more targeted explanation, ask with a topic such as adjectives, tenses, passive voice, or reported speech."
            ),
        }

    return None


def _slugify_topic(topic):
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
    return slug or "study-topic"


def _titleize_topic(query):
    return " ".join(word.capitalize() for word in re.sub(r"[-_]+", " ", query).split())


def _normalize_topic_key(topic):
    normalized = topic.strip().lower()
    return TOPIC_ALIASES.get(normalized, normalized)


def _keyword_in_text(keyword, text):
    escaped = re.escape(keyword)
    pattern = rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _resolve_topic_from_text_local(question, subject=None):
    normalized = re.sub(r"\s+", " ", question.strip().lower())
    if not normalized:
        return None, None

    candidate_subjects = (subject,) if subject else ("maths", "english")

    for entry in LOCAL_TUTOR_KNOWLEDGE:
        entry_subject = entry.get("subject")
        if entry_subject not in candidate_subjects:
            continue
        if any(_keyword_in_text(keyword, normalized) for keyword in entry.get("keywords", [])):
            return entry_subject, _normalize_topic_key(entry["topic"])

    for current_subject in candidate_subjects:
        for topic in get_supported_topics(subject=current_subject):
            normalized_topic = _normalize_topic_key(topic)
            if _keyword_in_text(normalized_topic, normalized):
                return current_subject, normalized_topic

    return None, None


def _extract_topic_resolution_from_text(payload_text):
    parsed = _extract_json_object(payload_text)

    if not isinstance(parsed, dict):
        return None, None, None

    subject = (parsed.get("subject") or "").strip().lower() or None
    topic = parsed.get("topic")
    confidence = parsed.get("confidence")

    if isinstance(topic, str):
        topic = _normalize_topic_key(topic)
    else:
        topic = None

    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = None

    if subject not in {"maths", "english"}:
        subject = None

    return subject, topic, confidence


def _resolve_topic_from_text_with_gemini(question, subject=None):
    candidate_subjects = [subject] if subject else ["maths", "english"]
    supported_topics = []
    for current_subject in candidate_subjects:
        for topic in get_supported_topics(subject=current_subject):
            normalized_topic = _normalize_topic_key(topic)
            if normalized_topic not in supported_topics:
                supported_topics.append(normalized_topic)

    prompt = (
        "Classify the student's question into one supported school topic.\n"
        f"Question: {question.strip()}\n"
        f"Allowed subjects: {', '.join(candidate_subjects)}\n"
        f"Allowed topics: {', '.join(supported_topics)}\n"
        'Return JSON only in this exact shape: {"subject":"...","topic":"...","confidence":0.0}\n'
        "Use only an allowed topic. If unsure, set topic to an empty string and confidence to 0."
    )
    system_prompt = (
        "You classify student questions to the closest supported topic for resource linking. "
        "Return only valid JSON with no markdown."
    )

    try:
        response_text = _call_gemini(prompt, system_prompt=system_prompt)
    except Exception:
        return None, None

    resolved_subject, resolved_topic, confidence = _extract_topic_resolution_from_text(response_text)
    if not resolved_subject or not resolved_topic or confidence is None or confidence < 0.6:
        return None, None

    if resolved_subject not in candidate_subjects:
        return None, None
    if resolved_topic not in supported_topics:
        return None, None

    return resolved_subject, resolved_topic


def resolve_topic_from_text(question, subject=None):
    resolved_subject, resolved_topic = _resolve_topic_from_text_with_gemini(question, subject=subject)
    if resolved_topic:
        return resolved_subject, resolved_topic
    return _resolve_topic_from_text_local(question, subject=subject)


def _infer_subject(query):
    lowered_query = query.strip().lower()

    for pack in LOCAL_LEARNING_PACKS:
        if pack["slug"] == lowered_query or pack["topic"].lower() == lowered_query:
            return pack["subject"]
    for pack in LOCAL_AUDIO_PACKS:
        if pack["slug"] == lowered_query or pack["topic"].lower() == lowered_query:
            return pack["subject"]

    maths_keywords = {
        "algebra", "equation", "fractions", "fraction", "geometry", "angles",
        "trigonometry", "probability", "statistics", "arithmetic", "calculus",
        "graph", "graphs", "ratio", "ratios", "percent", "percentage",
        "simultaneous", "quadratic", "number",
    }
    english_keywords = {
        "grammar", "passive", "voice", "essay", "essays", "tense", "tenses",
        "comprehension", "summary", "summaries", "parts of speech",
        "adjective", "adverb", "noun", "verb", "pronoun",
    }

    if any(keyword in lowered_query for keyword in maths_keywords):
        return "maths"
    if any(keyword in lowered_query for keyword in english_keywords):
        return "english"
    return "general"


def _split_generated_sections(text, summary_label, content_label):
    summary = ""
    content = text.strip()

    if summary_label in text and content_label in text:
        before_content, after_content = text.split(content_label, 1)
        summary = before_content.split(summary_label, 1)[1].strip()
        content = after_content.strip()

    return summary, content


def _build_local_learning_pack(topic, subject=None, slug=None):
    normalized_topic = _normalize_topic_key(topic)
    subject = subject or _infer_subject(normalized_topic)
    slug = slug or _slugify_topic(normalized_topic)
    topic_title = _titleize_topic(normalized_topic)
    topic_questions = TOPIC_PRACTICE_QUESTIONS.get(subject or "general", {}).get(normalized_topic, [])

    if subject == "english":
        summary = f"Study pack for {topic_title} with rules, examples, mistakes, and practice."
        explanation = (
            f"{topic_title} helps students understand how English works in real sentences. "
            "A good approach is to learn the rule, study examples, notice common mistakes, and then practise using the topic in full sentences."
        )
        key_points = [
            f"Understand the core rule behind {topic_title}.",
            "Notice how the pattern appears inside a full sentence.",
            "Compare correct and incorrect examples.",
            "Practise short questions before writing your own examples.",
        ]
    else:
        summary = f"Study pack for {topic_title} with key ideas, worked examples, and practice."
        explanation = (
            f"{topic_title} is a Maths topic that becomes easier when the student follows a clear method. "
            "The best revision approach is to understand the rule, work through examples step by step, and then practise similar questions carefully."
        )
        key_points = [
            f"Understand the main rule used in {topic_title}.",
            "Follow a step-by-step method instead of guessing.",
            "Check each stage of the working carefully.",
            "Practise a few short questions and review mistakes.",
        ]

    worked_examples = []
    guided_practice = []
    guided_answers = []
    for index, (question, answer) in enumerate(topic_questions[:3], start=1):
        worked_examples.append(
            f"{index}. Question: {question}\n"
            f"   Answer: {answer}\n"
            "   Tip: Read the question carefully, identify the rule being tested, and explain each step."
        )
        guided_practice.append(f"{index}. {question}")
        guided_answers.append(f"{index}. {answer}")

    if not worked_examples:
        worked_examples.append(
            f"1. Study one clear example related to {topic_title}, then explain why each step is correct."
        )
        guided_practice.append(f"1. Write one short practice question about {topic_title}.")
        guided_answers.append("1. Check your answer against the rule you studied.")

    content = (
        f"{topic_title.upper()} STUDY PACK\n\n"
        "1. LEARNING GOALS\n"
        f"- Build understanding of {topic_title}.\n"
        f"- Apply the main rule used in {topic_title}.\n"
        "- Gain confidence through examples and short practice.\n\n"
        "2. WHY THIS TOPIC MATTERS\n"
        f"{explanation}\n\n"
        "3. KEY POINTS\n"
        + "".join(f"- {point}\n" for point in key_points)
        + "\n4. WORKED EXAMPLES\n"
        + "\n\n".join(worked_examples)
        + "\n\n5. COMMON MISTAKES\n"
        "- Rushing without identifying the rule first.\n"
        "- Giving an answer without checking the method.\n"
        "- Ignoring small details in the question.\n"
        "- Forgetting to practise more than one example.\n\n"
        "6. GUIDED PRACTICE\n"
        + "\n".join(guided_practice)
        + "\n\n7. ANSWERS TO GUIDED PRACTICE\n"
        + "\n".join(guided_answers)
        + "\n\n8. REVISION NOTES\n"
        f"- Review {topic_title} in short sessions.\n"
        "- Explain the rule aloud in your own words.\n"
        "- Rework questions you found difficult.\n\n"
        "9. SUMMARY\n"
        f"{topic_title} becomes easier when the student understands the main idea, studies examples carefully, and practises step by step."
    )

    pack = {
        "slug": slug,
        "subject": subject,
        "topic": topic_title,
        "title": f"{topic_title} Pack",
        "summary": summary,
        "content": content,
    }
    GENERATED_LEARNING_PACKS[slug] = pack
    GENERATED_LEARNING_PACKS[normalized_topic] = pack
    return pack


def _build_local_audio_pack(topic, subject=None, slug=None):
    normalized_topic = _normalize_topic_key(topic)
    subject = subject or _infer_subject(normalized_topic)
    slug = slug or f"audio-{_slugify_topic(normalized_topic)}"
    topic_title = _titleize_topic(normalized_topic)
    topic_questions = TOPIC_PRACTICE_QUESTIONS.get(subject or "general", {}).get(normalized_topic, [])

    examples = []
    for question, answer in topic_questions[:2]:
        examples.append(f"For example, a learner may see this question: {question} The correct answer is {answer}.")

    if not examples:
        examples.append(
            f"For example, when studying {topic_title}, the learner should first identify the main rule and then apply it carefully."
        )

    transcript = (
        f"Welcome to this lesson on {topic_title}. "
        f"In this lesson, we will focus on the main idea behind {topic_title}, look at simple examples, and review how to avoid common mistakes. "
        f"{' '.join(examples)} "
        "As you revise, work slowly, explain each step in your own words, and check your final answer or sentence carefully. "
        f"With regular practice, {topic_title} becomes much easier to understand and use well."
    )

    pack = {
        "slug": slug,
        "subject": subject,
        "topic": topic_title,
        "title": f"{topic_title} Audio Lesson",
        "summary": f"Audio lesson for {topic_title} with examples and revision guidance.",
        "transcript": transcript,
    }
    GENERATED_AUDIO_PACKS[slug] = pack
    GENERATED_AUDIO_PACKS[normalized_topic] = pack
    return pack


def generate_learning_pack(topic, subject=None, slug=None):
    normalized_topic = _normalize_topic_key(topic)
    subject = subject or _infer_subject(normalized_topic)
    slug = slug or _slugify_topic(normalized_topic)
    topic_title = _titleize_topic(normalized_topic)

    prompt = (
        f"Create a detailed secondary school {subject} study pack about '{topic_title}'. "
        "Make it course-related, student-friendly, and ready to download as a revision handout. "
        "Return plain text only.\n"
        "Start with 'SUMMARY:' on one line, then write a short summary paragraph.\n"
        "After that write 'CONTENT:' on its own line and include:\n"
        "1. Learning goals\n"
        "2. Why the topic matters\n"
        "3. Key ideas or rules\n"
        "4. At least 3 worked examples\n"
        "5. Common mistakes\n"
        "6. Guided practice\n"
        "7. Answers to guided practice\n"
        "8. Exam-style practice\n"
        "9. Exam-style answers\n"
        "10. Short summary\n"
        "Use simple classroom English."
    )
    system_prompt = (
        "You are creating a study pack for secondary school students. "
        "Write clear, accurate, educational content with enough detail for revision. "
        "Do not use markdown code fences."
    )
    try:
        text = _call_gemini(prompt, system_prompt=system_prompt)
    except Exception:
        return _build_local_learning_pack(normalized_topic, subject=subject, slug=slug)
    summary, content = _split_generated_sections(text, "SUMMARY:", "CONTENT:")

    return _cache_generated_learning_pack({
        "slug": slug,
        "subject": subject,
        "topic": topic_title,
        "title": f"{topic_title} Pack",
        "summary": summary or f"Detailed revision pack for {topic_title}.",
        "content": content,
    })


def generate_audio_pack(topic, subject=None, slug=None):
    normalized_topic = _normalize_topic_key(topic)
    subject = subject or _infer_subject(normalized_topic)
    slug = slug or f"audio-{_slugify_topic(normalized_topic)}"
    topic_title = _titleize_topic(normalized_topic)

    prompt = (
        f"Create a detailed spoken-style lesson transcript for a secondary school {subject} topic about '{topic_title}'. "
        "Make it sound like a teacher speaking to a student. Return plain text only.\n"
        "Start with 'SUMMARY:' on one line, then a one-paragraph summary.\n"
        "After that write 'TRANSCRIPT:' on its own line and provide a lesson that includes:\n"
        "- a simple introduction\n"
        "- clear explanation of the topic\n"
        "- worked examples\n"
        "- common mistakes\n"
        "- revision advice\n"
        "- a short recap at the end"
    )
    system_prompt = (
        "You are creating an educational audio lesson transcript. "
        "Write clear, natural spoken English for students. "
        "Do not use markdown code fences."
    )
    try:
        text = _call_gemini(prompt, system_prompt=system_prompt)
    except Exception:
        return _build_local_audio_pack(normalized_topic, subject=subject, slug=slug)
    summary, transcript = _split_generated_sections(text, "SUMMARY:", "TRANSCRIPT:")

    return _cache_generated_audio_pack({
        "slug": slug,
        "subject": subject,
        "topic": topic_title,
        "title": f"{topic_title} Audio Lesson",
        "summary": summary or f"Audio lesson for {topic_title}.",
        "transcript": transcript,
    })


def get_or_generate_learning_pack(query, subject=None):
    lowered_query = _normalize_topic_key(query)
    generated_pack = GENERATED_LEARNING_PACKS.get(lowered_query)
    if generated_pack and (not subject or generated_pack.get("subject") == subject):
        return generated_pack

    existing_pack = get_learning_pack_by_slug_or_topic(query, subject=subject)
    source_topic = existing_pack["topic"] if existing_pack else query
    source_slug = existing_pack["slug"] if existing_pack else None

    try:
        return generate_learning_pack(source_topic, subject=subject, slug=source_slug)
    except Exception:
        if existing_pack:
            return existing_pack
        raise


def get_or_generate_audio_pack(query, subject=None):
    lowered_query = _normalize_topic_key(query)
    generated_pack = GENERATED_AUDIO_PACKS.get(lowered_query)
    if generated_pack and (not subject or generated_pack.get("subject") == subject):
        return generated_pack

    existing_pack = get_audio_pack_by_slug_or_topic(query, subject=subject)
    source_topic = existing_pack["topic"] if existing_pack else query
    source_slug = existing_pack["slug"] if existing_pack else None

    try:
        return generate_audio_pack(source_topic, subject=subject, slug=source_slug)
    except Exception:
        if existing_pack:
            return existing_pack
        raise


def generate_question(subject=None, exclude_questions=None, topic=None):
    excluded = set(exclude_questions or [])

    if topic:
        normalized_topic = _normalize_topic_key(topic)
        prompt = (
            f"Create one secondary school {subject or 'general'} practice question about '{_titleize_topic(normalized_topic)}'.\n"
            f"Avoid repeating these questions exactly: {sorted(excluded) if excluded else 'none'}\n"
            "Return plain text only in this format:\n"
            "Question: <question>\n"
            "Answer: <answer>"
        )
        system_prompt = (
            f"Generate one clear, short {subject or 'general'} practice question and its correct answer. "
            "Keep it course-related and suitable for WhatsApp revision."
        )
        try:
            text = _call_gemini(prompt, system_prompt=system_prompt)
            question, answer = _parse_question_answer_text(text.replace("Question:", "", 1).strip())
            if question and answer and question not in excluded:
                return question, answer
        except Exception:
            pass

        topic_bank = TOPIC_PRACTICE_QUESTIONS.get(subject or "general", {}).get(normalized_topic, [])
        if topic_bank:
            available = [item for item in topic_bank if item[0] not in excluded]
            if not available:
                available = topic_bank
            return random.choice(available)

    # Build the widest possible local fallback bank: base bank + all topic banks for this subject
    base_bank = LOCAL_PRACTICE_QUESTIONS.get(subject or "general", LOCAL_PRACTICE_QUESTIONS["general"])
    topic_banks = TOPIC_PRACTICE_QUESTIONS.get(subject or "general", {})
    all_topic_items = [item for bank in topic_banks.values() for item in bank]
    combined_bank = list({q: (q, a) for q, a in (base_bank + all_topic_items)}.values())
    available = [item for item in combined_bank if item[0] not in excluded]

    _random_seed = random.randint(1, 9999)
    prompt = "Create one secondary school practice question and provide the answer separately."
    system_prompt = "Generate one simple course-related practice question with a correct answer."
    if subject:
        prompt = f"Create one secondary school {subject} practice question and provide the answer separately."
        system_prompt = (
            f"Generate one simple secondary school {subject} practice question with answer. "
            "Keep it short, clear, and course-related."
        )

    prompt = (
        f"{prompt}\n"
        f"Pick a random topic and difficulty — seed {_random_seed}.\n"
        f"Avoid repeating these questions exactly: {sorted(excluded) if excluded else 'none'}\n"
        "Return plain text only in this format:\n"
        "Question: <question>\n"
        "Answer: <answer>"
    )

    try:
        text = _call_gemini(
            prompt,
            system_prompt=system_prompt,
        )
        question, answer = _parse_question_answer_text(text.replace("Question:", "", 1).strip())
        if question and answer and question not in excluded:
            return question, answer
    except Exception:
        pass

    if not available:
        available = combined_bank

    if available:
        return random.choice(available)

    raise RuntimeError("Unable to generate a practice question.")


def get_learning_packs(subject=None):
    if not subject:
        return LOCAL_LEARNING_PACKS
    return [pack for pack in LOCAL_LEARNING_PACKS if pack["subject"] == subject]


def get_audio_packs(subject=None):
    if not subject:
        return LOCAL_AUDIO_PACKS
    return [pack for pack in LOCAL_AUDIO_PACKS if pack["subject"] == subject]


def get_learning_pack_by_slug_or_topic(query, subject=None):
    lowered_query = _normalize_topic_key(query)
    generated_pack = GENERATED_LEARNING_PACKS.get(lowered_query)
    if generated_pack and (not subject or generated_pack.get("subject") == subject):
        return generated_pack
    for pack in LOCAL_LEARNING_PACKS:
        if subject and pack.get("subject") != subject:
            continue
        if pack["slug"] == lowered_query or _normalize_topic_key(pack["topic"]) == lowered_query:
            return pack
    return None


def get_audio_pack_by_slug_or_topic(query, subject=None):
    lowered_query = _normalize_topic_key(query)
    generated_pack = GENERATED_AUDIO_PACKS.get(lowered_query)
    if generated_pack and (not subject or generated_pack.get("subject") == subject):
        return generated_pack
    for pack in LOCAL_AUDIO_PACKS:
        if subject and pack.get("subject") != subject:
            continue
        if pack["slug"] == lowered_query or _normalize_topic_key(pack["topic"]) == lowered_query:
            return pack
    return None


def get_supported_topics(subject=None):
    topics = set()

    subject_topics = TOPIC_CATALOG.get(subject) if subject else None
    if subject_topics is not None:
        topics.update(subject_topics)
    else:
        for subject_topics in TOPIC_CATALOG.values():
            topics.update(subject_topics)

    practice_subject_topics = TOPIC_PRACTICE_QUESTIONS.get(subject, {}) if subject else None
    if practice_subject_topics is not None:
        topics.update(practice_subject_topics.keys())
    else:
        for topic_map in TOPIC_PRACTICE_QUESTIONS.values():
            topics.update(topic_map.keys())

    learning_packs = get_learning_packs(subject=subject)
    audio_packs = get_audio_packs(subject=subject)
    generated_learning = GENERATED_LEARNING_PACKS.values()
    generated_audio = GENERATED_AUDIO_PACKS.values()

    for pack in [*learning_packs, *audio_packs, *generated_learning, *generated_audio]:
        if subject and pack.get("subject") != subject:
            continue
        topic = pack.get("topic")
        if topic:
            topics.add(topic.lower())

    return sorted(topics, key=len, reverse=True)
