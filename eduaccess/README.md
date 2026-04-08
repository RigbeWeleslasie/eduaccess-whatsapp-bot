# EduAccess

EduAccess is a Django-based low-data learning assistant for secondary-school learners. It combines a simple study assistant, topic practice, WhatsApp access, and an installable offline library for English and Maths revision materials.

For Phase 3 of the hackathon, the MVP is intentionally framed around one core use case:

Student asks for help on a learning topic, receives a simple explanation, and can open related offline study materials for later use when connectivity is weak.

## MVP Focus

The codebase includes several supporting features, but the clearest demo flow is:

1. Student opens EduAccess on web or WhatsApp.
2. Student asks for help on a topic such as `Teach me linear equations`.
3. EduAccess returns a short explanation.
4. EduAccess links the student to downloadable text packs, audio lesson pages, and transcripts.
5. The student can later reopen cached resources through the PWA offline library.

This keeps the MVP aligned to one key use case while still showing the product vision.

## Current Features

- Web login and registration flow
- Study assistant for English and Maths
- Topic-aware replies with related study resources
- Practice questions with scoring
- Offline library with downloadable text packs and audio lesson pages
- PWA manifest and service worker for caching
- WhatsApp webhook for text and audio-based study requests
- Local fallback content when external AI is unavailable

## Tech Stack

- Python
- Django 5
- SQLite by default
- Twilio WhatsApp webhook
- Gemini API integration
- OpenAI SDK installed in dependencies
- WhiteNoise for static files

## Project Structure

`eduaccess/` contains Django project settings and URL configuration.

`whatsapp_bot/` contains:

- views for web, API, PWA, and WhatsApp flows
- AI and local content logic
- models for user progress and learning packs
- templates for study assistant, dashboard, offline library, and PWA pages
- tests for core user journeys

## Core User Flow

### Web Flow

1. User registers or logs in.
2. User opens the study assistant.
3. User asks a learning question like `Explain passive voice` or `Teach me linear equations`.
4. EduAccess returns an explanation and adds study pack and audio links when a topic is detected.
5. User can open the offline library and reuse cached materials later.

### WhatsApp Flow

1. User sends a message to the WhatsApp bot.
2. EduAccess reads the question and generates a reply.
3. If the message is about a known topic, related resources are included in the response.
4. If the user sends audio, the system transcribes it before answering.

## AI Logic Summary

AI is used in a layered way rather than as a single dependency:

- `ask_ai(...)` handles normal tutoring questions.
- Topic resolution detects likely subject and topic from a learner message.
- Question generation creates practice prompts.
- Learning pack and audio pack generation can provide topic resources.
- Audio transcription supports WhatsApp voice questions.

To reduce delivery risk for the MVP, the most important AI role is:

Answer a learner's topic question and connect that learner to reusable study materials.

The system also contains local fallback logic. If external AI fails, EduAccess can still:

- answer some known topics locally
- solve simple linear equations
- serve local packs and transcripts
- direct users to the offline library

## Minimum Offline Experience

The current minimum offline experience is:

- User visits the offline library while online
- Service worker caches the library and supported resource pages
- User can later reopen cached study pages, transcripts, and audio lesson pages offline

Important limitation:

First-time fully offline use is limited. The learner must first load the app and resources while connected so they can be cached.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file in the project root with the variables you need. Common examples:

```env
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-2.5-flash
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
WHATSAPP_SANDBOX_NUMBER=+14155238886
WHATSAPP_SANDBOX_JOIN_CODE=join sentence-settle
```

### 3. Run migrations

```bash
python manage.py migrate
```

### 4. Start the development server

```bash
python manage.py runserver
```

### 5. Open the app

Use:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/offline-library/`

## Test Suite

Run:

```bash
python manage.py test
```

The test suite covers:

- PWA endpoints
- offline library rendering
- study assistant flows
- practice question handling
- learning pack downloads
- WhatsApp webhook behavior

## Demo Guidance For Phase 3

The strongest mentor demo is:

1. Register or log in.
2. Ask `Teach me linear equations`.
3. Show the AI explanation and linked study resources.
4. Open the offline library.
5. Show the installable PWA flow and cached resources.
6. Optionally show the same question through the WhatsApp webhook.

## Engineering Notes

- Version control is recommended through GitHub.
- Code is organized by Django app responsibilities.
- Tests are already included for core flows.
- The app currently contains more than one feature set, but Phase 3 documentation should present one primary use case and treat the rest as supporting capabilities.
