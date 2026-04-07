# EduAccess WhatsApp Bot and PWA

EduAccess is a low-data learning assistant designed to support students through both WhatsApp and a Progressive Web App (PWA). The current MVP focuses on helping students access study support, practice questions, downloadable learning packs, and audio/transcript learning materials through a simple mobile-friendly interface.

## MVP Problem Statement

Many learners face barriers such as:
- unreliable internet
- limited access to structured learning materials
- difficulty revising independently
- lack of lightweight digital tools that work well on mobile

EduAccess addresses this by providing:
- a study assistant for question-and-answer support
- subject practice in Maths and English
- offline-friendly downloadable learning packs
- audio lessons and transcripts
- a PWA interface for easier mobile access

## Phase 3 MVP Goal

This MVP demonstrates one clear use case:

Students can sign in, interact with EduAccess through the web app, practise core subjects, and access simple offline learning materials from a mobile-friendly interface.

## Current MVP Features

### Student Authentication
- student registration
- login and logout
- logged-in access to the study assistant

### Study Assistant
- ask normal tutor-style questions
- request a Maths learning pack
- request an English learning pack
- request an audio lesson
- browse offline library content

### Practice Mode
- `practice english`
- `practice maths`
- waits for the student answer before grading
- gives feedback after the student responds
- tracks subject-level score and progress
- avoids immediate repetition of the same subject question

### Learning Materials
- downloadable text study packs
- audio lesson player pages
- transcript downloads
- expanded learning content for Algebra and Passive Voice

### PWA / Offline Support
- manifest and service worker
- install messaging
- offline fallback page
- mobile-friendly templates

### WhatsApp Support
- WhatsApp webhook endpoint
- shared tutor logic between WhatsApp and the PWA

## Tech Stack

- Python
- Django 5
- Twilio for WhatsApp webhook integration
- OpenAI / Gemini-compatible tutor logic in the AI layer
- HTML templates with a lightweight PWA frontend
- SQLite for local development

## Project Structure

```text
eduaccess-whatsapp-bot/
├── eduaccess/
│   ├── eduaccess/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── manage.py
│   ├── requirements.txt
│   ├── Procfile
│   ├── build.sh
│   └── whatsapp_bot/
│       ├── ai.py
│       ├── forms.py
│       ├── models.py
│       ├── views.py
│       ├── tests.py
│       ├── migrations/
│       └── templates/whatsapp_bot/
```

## Core Logic Overview

### 1. Tutor Request Flow

Main tutor request handling lives in:
- [`whatsapp_bot/views.py`](eduaccess/whatsapp_bot/views.py)

The shared reply logic:
- detects special commands such as `practice english`, `pack algebra`, and `audio pack passive voice`
- returns guided responses for known commands
- falls back to AI tutoring for general questions

### 2. Practice Logic

Practice flow supports:
- generating a subject-specific practice question
- storing the pending question
- waiting for the learner response
- evaluating correctness
- updating score and subject progress

This logic is handled through:
- in-session/user progress state in [`whatsapp_bot/views.py`](eduaccess/whatsapp_bot/views.py)
- user progress persistence in [`whatsapp_bot/models.py`](eduaccess/whatsapp_bot/models.py)

### 3. AI Logic

AI-related logic is located in:
- [`whatsapp_bot/ai.py`](eduaccess/whatsapp_bot/ai.py)

This file currently supports:
- tutor-style question answering through `ask_ai(...)`
- practice question generation through `generate_question(...)`
- local fallback study packs and audio content

For the current MVP:
- subject practice questions are drawn from local subject-specific question banks
- pack and transcript content is currently stored as local structured content
- AI is mainly used for open-ended tutoring and optional question generation fallback

### 4. PWA Logic

The PWA layer includes:
- manifest endpoint
- service worker endpoint
- install UI
- offline fallback

Relevant files:
- [`whatsapp_bot/views.py`](eduaccess/whatsapp_bot/views.py)
- [`whatsapp_bot/templates/whatsapp_bot/base_pwa.html`](eduaccess/whatsapp_bot/templates/whatsapp_bot/base_pwa.html)
- [`whatsapp_bot/templates/whatsapp_bot/service-worker.js`](eduaccess/whatsapp_bot/templates/whatsapp_bot/service-worker.js)

## Local Setup

### 1. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
cd eduaccess
pip install -r requirements.txt
```

### 3. Set environment variables

Create or update `.env` inside `eduaccess/`:

```env
DJANGO_DEBUG=True
DJANGO_SECURE_SSL_REDIRECT=False
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=
DJANGO_SECRET_KEY=dev-secret-key
OPENAI_API_KEY=
GEMINI_API_KEY=
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Start the server

```bash
python manage.py runserver
```

### 6. Open the app

Use:

```text
http://localhost:8000/login/
```

For local testing, `localhost` is currently safer than `127.0.0.1` because browser PWA/service-worker state may remain cached on the numeric host.

## Demo Flow for Mentors

1. Open the app and register a student account.
2. Log in and open the Study Assistant.
3. Ask a normal question such as:
   - `Explain algebra`
4. Request a practice question:
   - `practice maths`
5. Answer the question and show:
   - feedback
   - score
   - subject progress
6. Request a pack:
   - `pack algebra`
7. Open or download the pack.
8. Request an audio lesson:
   - `audio pack passive voice`
9. Show transcript or audio player.
10. Open the offline library / PWA flow.

## Tests

Tests are located in:
- [`whatsapp_bot/tests.py`](eduaccess/whatsapp_bot/tests.py)

Run tests with:

```bash
python manage.py test whatsapp_bot.tests
```

## Deployment Notes

This repository includes basic deployment preparation:
- `requirements.txt`
- `Procfile`
- `build.sh`
- production-aware settings

Recommended deployment target:
- Render

Recommended production setup:
- PostgreSQL via `DATABASE_URL`
- secure secret key via environment variable
- `DJANGO_DEBUG=False`
- configured allowed hosts and CSRF trusted origins

## Known MVP Gaps

These are the main areas still suitable for future improvement:
- stronger learner dashboard and analytics
- richer PDF generation instead of plain text downloads
- broader subject coverage
- stronger AI evaluation feedback for free-text answers
- fully verified production deployment
- final mentor demo polish for PWA onboarding

## Deliverable Summary

This project currently satisfies the MVP direction by demonstrating:
- a real working prototype
- one clear learner-centered use case
- usable web flows
- modular Django structure
- documented AI and practice logic
- a testable codebase for mentor demo
