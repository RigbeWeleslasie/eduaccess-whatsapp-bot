# whatsapp_bot/ai.py
import json
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

LOCAL_LEARNING_PACKS = [
    {
        "slug": "maths-algebra-basics",
        "subject": "maths",
        "topic": "Algebra",
        "title": "Algebra Basics Pack",
        "summary": "A full beginner algebra lesson with explanations, examples, drills, review, and exam-style practice.",
        "content": (
            "ALGEBRA BASICS STUDY PACK\n\n"
            "1. LEARNING GOALS\n"
            "- Understand what variables, expressions, and equations mean.\n"
            "- Solve simple one-step and two-step equations.\n"
            "- Check whether an answer is correct.\n"
            "- Translate simple word statements into algebra.\n\n"
            "2. WHY ALGEBRA MATTERS\n"
            "Algebra is a way of thinking about unknown values. Instead of writing a long sentence every time, we use letters to represent numbers we do not yet know. "
            "This helps in arithmetic, science, business, measurements, and problem solving. If you can solve an equation, you can find a missing age, a missing length, a cost, a speed, or a number pattern.\n\n"
            "3. KEY IDEAS\n"
            "A variable is a letter such as x or y that stands for an unknown number.\n"
            "An expression is a maths phrase such as 3x + 2.\n"
            "An equation says two expressions are equal, for example x + 7 = 15.\n"
            "To solve an equation, keep the equation balanced by doing the same operation to both sides.\n\n"
            "4. VOCABULARY\n"
            "- Variable: a symbol for an unknown value.\n"
            "- Coefficient: the number multiplying a variable, for example 4 in 4x.\n"
            "- Constant: a fixed number, for example 9 in x + 9.\n"
            "- Solve: find the value of the variable.\n\n"
            "5. EXPRESSIONS AND EQUATIONS\n"
            "Expression examples:\n"
            "- 2x + 3\n"
            "- y - 5\n"
            "- 7a\n\n"
            "Equation examples:\n"
            "- x + 7 = 15\n"
            "- 3y = 18\n"
            "- 2m - 1 = 9\n\n"
            "An expression has no equals sign. An equation has an equals sign.\n\n"
            "6. BALANCE METHOD\n"
            "Think of an equation as a balance scale. If you add, subtract, multiply, or divide one side, you must do the same to the other side. "
            "That is how you keep the equation true.\n\n"
            "7. WORKED EXAMPLE 1\n"
            "Solve: x + 7 = 15\n"
            "Step 1: Subtract 7 from both sides.\n"
            "x + 7 - 7 = 15 - 7\n"
            "x = 8\n"
            "Check: 8 + 7 = 15, so the answer is correct.\n\n"
            "8. WORKED EXAMPLE 2\n"
            "Solve: 3x = 21\n"
            "Step 1: Divide both sides by 3.\n"
            "3x / 3 = 21 / 3\n"
            "x = 7\n"
            "Check: 3 x 7 = 21.\n\n"
            "9. WORKED EXAMPLE 3\n"
            "Solve: 2x + 5 = 17\n"
            "Step 1: Subtract 5 from both sides.\n"
            "2x = 12\n"
            "Step 2: Divide both sides by 2.\n"
            "x = 6\n"
            "Check: 2(6) + 5 = 17.\n\n"
            "10. WORKED EXAMPLE 4\n"
            "Solve: x/4 = 3\n"
            "Step 1: Multiply both sides by 4.\n"
            "x = 12\n"
            "Check: 12/4 = 3.\n\n"
            "11. WORD STATEMENTS INTO ALGEBRA\n"
            "Translate these statements:\n"
            "- A number plus 5 is written as x + 5.\n"
            "- Three times a number is written as 3x.\n"
            "- A number reduced by 8 is written as x - 8.\n"
            "- Half of a number is written as x/2.\n\n"
            "12. COMMON MISTAKES\n"
            "- Changing only one side of the equation.\n"
            "- Forgetting to reverse addition with subtraction or multiplication with division.\n"
            "- Not checking the final answer in the original equation.\n"
            "- Mixing expressions and equations.\n"
            "- Forgetting that 3x means 3 multiplied by x.\n\n"
            "13. GUIDED PRACTICE\n"
            "a) x - 4 = 10\n"
            "b) 5x = 35\n"
            "c) y + 12 = 20\n"
            "d) 4m - 3 = 13\n"
            "e) n/5 = 6\n"
            "f) 3p + 2 = 14\n\n"
            "14. ANSWERS TO GUIDED PRACTICE\n"
            "a) x = 14\n"
            "b) x = 7\n"
            "c) y = 8\n"
            "d) m = 4\n"
            "e) n = 30\n"
            "f) p = 4\n\n"
            "15. EXAM-STYLE PRACTICE\n"
            "1) Solve 7x = 49.\n"
            "2) Solve y - 9 = 16.\n"
            "3) Solve 2a + 3 = 11.\n"
            "4) A number increased by 6 is 14. Find the number.\n"
            "5) Amina buys 3 pencils at x shillings each and pays 24 shillings. Form an equation and solve it.\n\n"
            "16. EXAM-STYLE ANSWERS\n"
            "1) x = 7\n"
            "2) y = 25\n"
            "3) a = 4\n"
            "4) x + 6 = 14, so x = 8\n"
            "5) 3x = 24, so x = 8 shillings\n\n"
            "17. REVISION NOTES\n"
            "- Look at the operation near the variable.\n"
            "- Undo that operation using the opposite operation.\n"
            "- Keep both sides balanced.\n"
            "- Check by substitution.\n\n"
            "18. SELF-ASSESSMENT\n"
            "Ask yourself:\n"
            "- Can I tell the difference between an expression and an equation?\n"
            "- Can I solve x + 5 = 12 without help?\n"
            "- Can I solve 3x = 18 without help?\n"
            "- Can I solve 2x + 1 = 9 step by step?\n"
            "If you answered no to any of these, repeat the worked examples and guided practice.\n\n"
            "19. SUMMARY\n"
            "Algebra helps us find unknown values. The main rule is to keep both sides balanced, use opposite operations carefully, and check the answer at the end."
        ),
    },
    {
        "slug": "english-passive-voice",
        "subject": "english",
        "topic": "Passive voice",
        "title": "Passive Voice Pack",
        "summary": "A full grammar lesson on passive voice with clear rules, tense patterns, examples, corrections, and practice.",
        "content": (
            "PASSIVE VOICE STUDY PACK\n\n"
            "1. LEARNING GOALS\n"
            "- Understand the difference between active and passive voice.\n"
            "- Change active sentences into passive sentences correctly.\n"
            "- Choose the correct form of the verb 'be' and the past participle.\n\n"
            "2. WHY THIS TOPIC MATTERS\n"
            "Passive voice is useful in school writing, reports, news writing, science procedures, and formal English. "
            "It helps the writer focus on the action or the result instead of the person doing the action.\n\n"
            "3. KEY IDEA\n"
            "In active voice, the subject does the action.\n"
            "In passive voice, the receiver of the action becomes the focus.\n\n"
            "4. STRUCTURE\n"
            "Active: subject + verb + object\n"
            "Passive: object + form of 'be' + past participle + by + subject\n\n"
            "5. MAIN EXAMPLE\n"
            "Active: The students solved the problem.\n"
            "Passive: The problem was solved by the students.\n\n"
            "6. MORE EXAMPLES\n"
            "Active: The chef cooked the meal.\n"
            "Passive: The meal was cooked by the chef.\n\n"
            "Active: The teacher marks the books.\n"
            "Passive: The books are marked by the teacher.\n\n"
            "7. STEP-BY-STEP METHOD\n"
            "Step 1: Find the object in the active sentence.\n"
            "Step 2: Move that object to the beginning.\n"
            "Step 3: Choose the correct form of the verb 'be'.\n"
            "Step 4: Use the past participle of the main verb.\n"
            "Step 5: Add 'by' plus the doer when necessary.\n\n"
            "8. TENSE GUIDE\n"
            "Present simple active: The teacher marks the books.\n"
            "Present simple passive: The books are marked by the teacher.\n\n"
            "Past simple active: The teacher marked the books.\n"
            "Past simple passive: The books were marked by the teacher.\n\n"
            "Future active: The teacher will mark the books.\n"
            "Future passive: The books will be marked by the teacher.\n\n"
            "9. WHEN TO USE PASSIVE VOICE\n"
            "- When the action is more important than the doer.\n"
            "- When the doer is unknown.\n"
            "- In formal or report writing.\n\n"
            "10. WHEN NOT TO USE IT TOO MUCH\n"
            "Do not overuse passive voice in ordinary speaking and writing, because too much passive voice can make writing weak or unclear. "
            "Use it when it serves a purpose.\n\n"
            "11. COMMON MISTAKES\n"
            "- Forgetting the correct form of 'be'.\n"
            "- Using the wrong past participle.\n"
            "- Leaving out the object from the active sentence.\n"
            "- Changing a sentence that has no object.\n"
            "- Writing 'by' when it is not needed.\n\n"
            "12. CORRECTION PRACTICE\n"
            "Wrong: The food cooked by the chef.\n"
            "Correct: The food was cooked by the chef.\n\n"
            "Wrong: The room is clean by the class.\n"
            "Correct: The room is cleaned by the class.\n\n"
            "13. GUIDED PRACTICE\n"
            "Change these to passive voice:\n"
            "a) The class cleaned the room.\n"
            "b) The farmer planted the maize.\n"
            "c) The police arrested the thief.\n"
            "d) The mechanic repaired the car.\n"
            "e) The nurse helped the patient.\n\n"
            "14. ANSWERS TO GUIDED PRACTICE\n"
            "a) The room was cleaned by the class.\n"
            "b) The maize was planted by the farmer.\n"
            "c) The thief was arrested by the police.\n"
            "d) The car was repaired by the mechanic.\n"
            "e) The patient was helped by the nurse.\n\n"
            "15. EXAM-STYLE PRACTICE\n"
            "1) Change to passive voice: The pupils opened the windows.\n"
            "2) Change to passive voice: The workers built the bridge.\n"
            "3) Change to passive voice: The head teacher will announce the results.\n"
            "4) Rewrite in active voice: The homework was completed by Musa.\n"
            "5) Rewrite in active voice: The song was sung by the choir.\n\n"
            "16. EXAM-STYLE ANSWERS\n"
            "1) The windows were opened by the pupils.\n"
            "2) The bridge was built by the workers.\n"
            "3) The results will be announced by the head teacher.\n"
            "4) Musa completed the homework.\n"
            "5) The choir sang the song.\n\n"
            "17. REVISION NOTES\n"
            "- Find the object first.\n"
            "- Move it to the front.\n"
            "- Use the correct form of 'be'.\n"
            "- Add the past participle.\n"
            "- Add the doer only when necessary.\n\n"
            "18. SELF-ASSESSMENT\n"
            "Ask yourself:\n"
            "- Can I explain active voice and passive voice?\n"
            "- Can I change a past tense sentence into passive voice?\n"
            "- Can I change a future tense sentence into passive voice?\n"
            "- Can I recognise when passive voice is useful?\n"
            "If you answered no to some of these, go back to the examples and guided practice.\n\n"
            "19. SUMMARY\n"
            "Passive voice is formed with a form of 'be' plus a past participle. It is useful when the receiver of the action is the main focus, especially in formal and informational writing."
        ),
    },
]

LOCAL_AUDIO_PACKS = [
    {
        "slug": "audio-maths-algebra-basics",
        "subject": "maths",
        "topic": "Algebra",
        "title": "Algebra Audio Lesson",
        "summary": "A longer spoken-style lesson on variables, equations, balancing, worked examples, and revision tips.",
        "transcript": (
            "Welcome to this algebra lesson. Algebra helps us find unknown numbers by using letters such as x and y. "
            "A variable is a letter that stands for a number we do not yet know. "
            "An expression is a maths phrase such as 2x plus 3, while an equation includes an equals sign. "
            "An equation shows that two sides are equal, for example x plus 7 equals 15. "
            "To solve an equation, we must keep both sides balanced, just like a balance scale. "
            "If the equation is x plus 7 equals 15, we subtract 7 from both sides, and we get x equals 8. "
            "If the equation is 3x equals 21, we divide both sides by 3, and we get x equals 7. "
            "For a two-step equation such as 2x plus 5 equals 17, first subtract 5 from both sides to get 2x equals 12, then divide by 2 to get x equals 6. "
            "Another example is x divided by 4 equals 3. In that case, multiply both sides by 4 to get x equals 12. "
            "Always check your answer by putting it back into the original equation. "
            "Common mistakes include changing only one side of the equation or forgetting to use the opposite operation. "
            "Algebra becomes easier when you work step by step, keep both sides equal, and practise a few examples every day."
        ),
    },
    {
        "slug": "audio-english-passive-voice",
        "subject": "english",
        "topic": "Passive voice",
        "title": "Passive Voice Audio Lesson",
        "summary": "A longer spoken explanation of passive voice, tense patterns, usage, and common mistakes.",
        "transcript": (
            "Welcome to this passive voice lesson. "
            "In active voice, the subject performs the action, as in the students solved the problem. "
            "In passive voice, the receiver of the action becomes the focus, so we say the problem was solved by the students. "
            "To form the passive voice, use the correct form of the verb be and then add the past participle. "
            "For example, the chef cooked the meal becomes the meal was cooked by the chef. "
            "In the present tense, we may say the books are marked by the teacher. In the past tense, we say the books were marked by the teacher. "
            "In the future tense, we can say the results will be announced by the head teacher. "
            "We often use passive voice when the action is more important than the doer, or when the doer is unknown. "
            "When changing a sentence, first identify the object in the active sentence, move it to the front, then choose the correct form of be, and finally use the past participle. "
            "Common mistakes include forgetting the verb be, using the wrong verb form, or trying to change a sentence that has no object. "
            "Passive voice is useful in formal writing, reports, and scientific explanations, but it should be used clearly and purposefully."
        ),
    },
]

LOCAL_PRACTICE_QUESTIONS = {
    "maths": [
        ("Solve for x: x + 9 = 14", "x = 5"),
        ("Solve for y: 3y = 18", "y = 6"),
        ("Solve for m: 2m + 5 = 13", "m = 4"),
        ("Solve for x: x/4 = 3", "x = 12"),
        ("A number increased by 7 is 19. Find the number.", "x = 12"),
        ("Solve for p: 5p - 10 = 15", "p = 5"),
    ],
    "english": [
        ("Rewrite this sentence using the correct punctuation: i like reading novels and poems", "I like reading novels and poems."),
        ("Choose the correct word: The students _____ going to the library. (is/are)", "are"),
        ("Write the plural form of 'child'.", "children"),
        ("Change to passive voice: The chef cooked the meal.", "The meal was cooked by the chef."),
        ("Give one synonym for 'happy'.", "joyful"),
        ("Write one sentence using the past tense of the verb 'go'.", "Yesterday I went to school."),
    ],
    "general": [
        ("Solve for x: x + 7 = 15", "x = 8"),
        ("Change to passive voice: The farmer planted the maize.", "The maize was planted by the farmer."),
        ("Solve for x: 4x = 20", "x = 5"),
        ("Change to active voice: The song was sung by the choir.", "The choir sang the song."),
    ],
}

TOPIC_PRACTICE_QUESTIONS = {
    "english": {
        "passive voice": [
            ("Change to passive voice: The chef cooked the meal.", "The meal was cooked by the chef."),
            ("Change to passive voice: The students solved the problem.", "The problem was solved by the students."),
        ],
        "reported speech": [
            ('Change to reported speech: Amina said, "I am revising now."', "Amina said that she was revising then."),
            ('Change to reported speech: The teacher said, "Work quietly."', "The teacher told the students to work quietly."),
        ],
        "adjectives": [
            ("Identify the adjective in this sentence: The tall boy ran home.", "tall"),
            ("Use an adjective to complete this sentence: The _____ road was difficult to cross.", "busy"),
        ],
        "tenses": [
            ("Change this sentence to the past tense: She walks to school every day.", "She walked to school every day."),
            ("Write the present continuous form of 'read' in a sentence.", "I am reading a book."),
        ],
        "vocabulary": [
            ("Give one synonym for 'happy'.", "joyful"),
            ("Give one antonym for 'difficult'.", "easy"),
        ],
        "parts of speech": [
            ("Identify the noun in this sentence: The teacher praised Musa.", "teacher"),
            ("Identify the verb in this sentence: The children laughed loudly.", "laughed"),
        ],
        "comprehension": [
            ("What should you do first when answering a comprehension passage question?", "Read the passage carefully."),
            ("Why is it important to use evidence from the passage in your answer?", "It supports the answer."),
        ],
        "essay writing": [
            ("Name one important part of an essay.", "introduction"),
            ("What should each body paragraph in an essay contain?", "one main idea"),
        ],
        "letter writing": [
            ("Write one feature of a formal letter.", "address"),
            ("What polite closing can be used in a formal letter?", "Yours faithfully"),
        ],
        "conjunctions": [
            ("Choose the correct conjunction: I stayed indoors _____ it was raining. (because/and)", "because"),
            ("Join these ideas with a conjunction: She studied hard. She passed the test.", "She studied hard, so she passed the test."),
        ],
        "direct and indirect speech": [
            ('Change to indirect speech: John said, "I am tired."', "John said that he was tired."),
            ('Change to direct speech: Mary said that she would come the next day.', 'Mary said, "I will come tomorrow."'),
        ],
    },
    "maths": {
        "fractions": [
            ("Simplify: 6/8", "3/4"),
            ("Add: 1/4 + 1/4", "1/2"),
        ],
        "algebra": [
            ("Solve for x: x + 9 = 14", "x = 5"),
            ("Solve for y: 3y = 18", "y = 6"),
        ],
        "geometry": [
            ("How many degrees are in a right angle?", "90"),
            ("Name a shape with three sides.", "triangle"),
        ],
        "calculus": [
            ("Differentiate with respect to x: x^2", "2x"),
            ("Find the derivative of 3x^2.", "6x"),
            ("Differentiate with respect to x: 5x", "5"),
        ],
        "linear equations": [
            ("Solve for x: 2x + 3 = 11", "x = 4"),
            ("Solve for y: 5y - 10 = 20", "y = 6"),
            ("Solve for x: 4x = 28", "x = 7"),
        ],
        "simultaneous equations": [
            ("Solve: x + y = 7 and x - y = 1", "x = 4, y = 3"),
            ("Solve: x + y = 10 and x - y = 2", "x = 6, y = 4"),
        ],
        "quadratic equations": [
            ("Solve: x^2 - 9 = 0", "x = 3 or x = -3"),
            ("Solve: x^2 - 5x + 6 = 0", "x = 2 or x = 3"),
        ],
        "percentages": [
            ("Find 20% of 50.", "10"),
            ("A shirt costs 200 shillings. What is 10% of the price?", "20 shillings"),
        ],
        "ratios": [
            ("Simplify the ratio 8:12.", "2:3"),
            ("Share 30 in the ratio 2:3.", "12 and 18"),
        ],
        "indices": [
            ("Simplify: 2^3", "8"),
            ("What is 10^2?", "100"),
        ],
        "trigonometry": [
            ("What is the sine of 90 degrees?", "1"),
            ("What is the cosine of 0 degrees?", "1"),
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
}

LOCAL_TUTOR_KNOWLEDGE = [
    {
        "subject": "maths",
        "keywords": ["derivative", "differentiate", "differentiation", "rate of change"],
        "topic": "calculus",
        "answer": (
            "A derivative shows the rate of change of one quantity with respect to another. "
            "In simple terms, it tells us how quickly a function is changing at a point. "
            "For example, if y = x^2, the derivative is 2x, so the slope changes depending on the value of x. "
            "A good next step is to practise differentiating simple powers such as x^2, 3x^2, and 5x."
        ),
    },
    {
        "subject": "maths",
        "keywords": ["linear equation", "linear equations", "solve for x", "unknown value"],
        "topic": "linear equations",
        "answer": (
            "A linear equation is an equation where the variable has power 1, for example 2x + 3 = 11. "
            "To solve it, isolate the variable step by step by doing the same operation on both sides. "
            "For 2x + 3 = 11, subtract 3 first to get 2x = 8, then divide by 2 to get x = 4. "
            "Always check your answer by substituting it back into the original equation."
        ),
    },
    {
        "subject": "maths",
        "keywords": ["algebra", "expression", "equation"],
        "topic": "algebra",
        "answer": (
            "Algebra uses letters and symbols to represent unknown numbers and relationships. "
            "An expression is a maths phrase like 3x + 2, while an equation has an equals sign, such as x + 5 = 12. "
            "The main skill in algebra is to keep both sides balanced while solving for the unknown value."
        ),
    },
    {
        "subject": "maths",
        "keywords": ["fraction", "fractions", "numerator", "denominator"],
        "topic": "fractions",
        "answer": (
            "A fraction shows part of a whole. The top number is the numerator and the bottom number is the denominator. "
            "To add or subtract fractions, first make sure they have the same denominator. "
            "For example, 1/4 + 1/4 = 2/4, which simplifies to 1/2."
        ),
    },
    {
        "subject": "maths",
        "keywords": ["percentage", "percentages", "percent"],
        "topic": "percentages",
        "answer": (
            "A percentage means a number out of 100. "
            "To find a percentage of a quantity, change the percentage into a fraction or decimal and multiply. "
            "For example, 20% of 50 is 20/100 multiplied by 50, which equals 10."
        ),
    },
    {
        "subject": "maths",
        "keywords": ["ratio", "ratios"],
        "topic": "ratios",
        "answer": (
            "A ratio compares two quantities. "
            "For example, a ratio of 2:3 means for every 2 parts of one quantity, there are 3 parts of the other. "
            "When simplifying a ratio, divide both parts by the same common factor."
        ),
    },
    {
        "subject": "maths",
        "keywords": ["trigonometry", "sine", "cosine", "tangent"],
        "topic": "trigonometry",
        "answer": (
            "Trigonometry studies the relationship between angles and sides in triangles. "
            "The main ratios are sine, cosine, and tangent. "
            "For a right-angled triangle, sine equals opposite over hypotenuse, cosine equals adjacent over hypotenuse, and tangent equals opposite over adjacent."
        ),
    },
    {
        "subject": "english",
        "keywords": ["passive voice", "active voice"],
        "topic": "passive voice",
        "answer": (
            "Passive voice puts the receiver of the action first. "
            "For example, 'The chef cooked the meal' in active voice becomes 'The meal was cooked by the chef' in passive voice. "
            "The common pattern is: object + form of 'be' + past participle + optional doer."
        ),
    },
    {
        "subject": "english",
        "keywords": ["reported speech", "indirect speech", "direct speech"],
        "topic": "reported speech",
        "answer": (
            "Reported speech explains what someone said without repeating the exact words. "
            "For example, 'Amina said, \"I am tired\"' becomes 'Amina said that she was tired.' "
            "When changing direct speech to reported speech, pronouns, tense, and time words may change."
        ),
    },
    {
        "subject": "english",
        "keywords": ["adjective", "adjectives"],
        "topic": "adjectives",
        "answer": (
            "An adjective describes a noun or pronoun. "
            "It tells us more about size, colour, shape, number, or quality. "
            "In 'the tall boy', the word 'tall' is the adjective because it describes the boy."
        ),
    },
    {
        "subject": "english",
        "keywords": ["tense", "tenses", "past tense", "present tense", "future tense"],
        "topic": "tenses",
        "answer": (
            "Tenses show the time of an action. "
            "Present tense describes what happens now, past tense describes what already happened, and future tense describes what will happen. "
            "For example: 'I walk', 'I walked', and 'I will walk'."
        ),
    },
    {
        "subject": "english",
        "keywords": ["noun", "nouns"],
        "topic": "parts of speech",
        "answer": (
            "A noun names a person, place, thing, or idea. "
            "Examples include teacher, Nairobi, book, and happiness. "
            "A good way to identify a noun is to ask whether the word is naming something."
        ),
    },
    {
        "subject": "english",
        "keywords": ["verb", "verbs"],
        "topic": "parts of speech",
        "answer": (
            "A verb shows an action or a state. "
            "Action verbs include run, read, and sing, while state verbs include be, seem, and know. "
            "In a sentence, the verb is the word that tells what is happening."
        ),
    },
    {
        "subject": "english",
        "keywords": ["conjunction", "conjunctions"],
        "topic": "conjunctions",
        "answer": (
            "A conjunction joins words, phrases, or clauses. "
            "Common conjunctions include and, but, because, so, and although. "
            "For example, 'I stayed indoors because it was raining' uses 'because' to join the ideas."
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
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set.")

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

    try:
        with request.urlopen(req, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API error {exc.code}: {error_body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Gemini network error: {exc.reason}") from exc

    text = _extract_text(response_data)
    if not text:
        raise RuntimeError(f"Gemini returned no text: {response_data}")
    return text


def ask_ai(question):
    return _call_gemini(question, system_prompt="You are a helpful tutor.")


def build_local_tutor_answer(question):
    normalized = re.sub(r"\s+", " ", question.strip().lower())
    if not normalized:
        return None

    for entry in LOCAL_TUTOR_KNOWLEDGE:
        if any(keyword in normalized for keyword in entry["keywords"]):
            return {
                "subject": entry["subject"],
                "topic": entry["topic"],
                "answer": entry["answer"],
            }

    for subject in ("maths", "english"):
        for topic in get_supported_topics(subject=subject):
            if topic in normalized:
                topic_title = _titleize_topic(topic)
                if subject == "maths":
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
                return {"subject": subject, "topic": topic, "answer": answer}

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

    prompt = (
        f"Create a detailed secondary school {subject} study pack about '{normalized_topic}'. "
        "Return plain text only. Start with 'SUMMARY:' on one line, then a short summary paragraph. "
        "After that write 'CONTENT:' on its own line and provide a rich lesson handout with:"
        " learning goals, explanation, key ideas, worked examples, common mistakes, guided practice, answers, exam-style practice, and summary."
    )
    system_prompt = (
        "You are creating a study pack for students. "
        "Write clear, accurate, educational content with enough detail for revision. "
        "Do not use markdown code fences."
    )
    try:
        text = _call_gemini(prompt, system_prompt=system_prompt)
    except Exception:
        return _build_local_learning_pack(normalized_topic, subject=subject, slug=slug)
    summary, content = _split_generated_sections(text, "SUMMARY:", "CONTENT:")

    pack = {
        "slug": slug,
        "subject": subject,
        "topic": _titleize_topic(normalized_topic),
        "title": f"{_titleize_topic(normalized_topic)} Pack",
        "summary": summary or f"Detailed revision pack for {_titleize_topic(normalized_topic)}.",
        "content": content,
    }
    GENERATED_LEARNING_PACKS[slug] = pack
    GENERATED_LEARNING_PACKS[normalized_topic] = pack
    return pack


def generate_audio_pack(topic, subject=None, slug=None):
    normalized_topic = _normalize_topic_key(topic)
    subject = subject or _infer_subject(normalized_topic)
    slug = slug or f"audio-{_slugify_topic(normalized_topic)}"

    prompt = (
        f"Create a detailed spoken-style lesson transcript for a secondary school {subject} topic about '{normalized_topic}'. "
        "Return plain text only. Start with 'SUMMARY:' on one line, then a one-paragraph summary. "
        "After that write 'TRANSCRIPT:' on its own line and provide a rich transcript students can read or listen to. "
        "Include explanation, examples, common mistakes, and a short recap."
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

    pack = {
        "slug": slug,
        "subject": subject,
        "topic": _titleize_topic(normalized_topic),
        "title": f"{_titleize_topic(normalized_topic)} Audio Lesson",
        "summary": summary or f"Audio lesson for {_titleize_topic(normalized_topic)}.",
        "transcript": transcript,
    }
    GENERATED_AUDIO_PACKS[slug] = pack
    GENERATED_AUDIO_PACKS[normalized_topic] = pack
    return pack


def get_or_generate_learning_pack(query, subject=None):
    pack = get_learning_pack_by_slug_or_topic(query)
    if pack:
        return pack
    return generate_learning_pack(query, subject=subject)


def get_or_generate_audio_pack(query, subject=None):
    pack = get_audio_pack_by_slug_or_topic(query)
    if pack:
        return pack
    return generate_audio_pack(query, subject=subject)


def generate_question(subject=None, exclude_questions=None, topic=None):
    excluded = set(exclude_questions or [])

    if topic:
        normalized_topic = _normalize_topic_key(topic)
        topic_bank = TOPIC_PRACTICE_QUESTIONS.get(subject or "general", {}).get(normalized_topic, [])
        if topic_bank:
            available = [item for item in topic_bank if item[0] not in excluded]
            if not available:
                available = topic_bank
            return random.choice(available)

        prompt = f"Create one secondary school {subject or 'general'} practice question about '{topic}' and provide the answer separately."
        system_prompt = (
            f"Generate one clear, short {subject or 'general'} practice question based on the student's chosen topic '{topic}'. "
            "Return the question first, then 'Answer:' and the answer."
        )
        text = _call_gemini(prompt, system_prompt=system_prompt)
        parts = text.split("Answer:")
        question = parts[0].strip()
        answer = parts[1].strip() if len(parts) > 1 else "unknown"
        return question, answer

    question_bank = LOCAL_PRACTICE_QUESTIONS.get(subject or "general", LOCAL_PRACTICE_QUESTIONS["general"])
    available = [item for item in question_bank if item[0] not in excluded]
    if not available:
        available = question_bank

    if available:
        return random.choice(available)

    prompt = "Create one question and provide the answer separately."
    system_prompt = "Generate a simple secondary school question with answer."

    if subject:
        prompt = f"Create one {subject} practice question and provide the answer separately."
        system_prompt = (
            f"Generate one simple secondary school {subject} practice question with answer. "
            "Keep it short and clear."
        )

    text = _call_gemini(
        prompt,
        system_prompt=system_prompt,
    )
    parts = text.split("Answer:")
    question = parts[0].strip()
    answer = parts[1].strip() if len(parts) > 1 else "unknown"
    return question, answer


def get_learning_packs(subject=None):
    if not subject:
        return LOCAL_LEARNING_PACKS
    return [pack for pack in LOCAL_LEARNING_PACKS if pack["subject"] == subject]


def get_audio_packs(subject=None):
    if not subject:
        return LOCAL_AUDIO_PACKS
    return [pack for pack in LOCAL_AUDIO_PACKS if pack["subject"] == subject]


def get_learning_pack_by_slug_or_topic(query):
    lowered_query = _normalize_topic_key(query)
    generated_pack = GENERATED_LEARNING_PACKS.get(lowered_query)
    if generated_pack:
        return generated_pack
    for pack in LOCAL_LEARNING_PACKS:
        if pack["slug"] == lowered_query or _normalize_topic_key(pack["topic"]) == lowered_query:
            return pack
    return None


def get_audio_pack_by_slug_or_topic(query):
    lowered_query = _normalize_topic_key(query)
    generated_pack = GENERATED_AUDIO_PACKS.get(lowered_query)
    if generated_pack:
        return generated_pack
    for pack in LOCAL_AUDIO_PACKS:
        if pack["slug"] == lowered_query or _normalize_topic_key(pack["topic"]) == lowered_query:
            return pack
    return None


def get_supported_topics(subject=None):
    topics = set()

    subject_topics = TOPIC_PRACTICE_QUESTIONS.get(subject, {}) if subject else None
    if subject_topics is not None:
        topics.update(subject_topics.keys())
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
