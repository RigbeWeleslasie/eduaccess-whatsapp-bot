# EduAccess WhatsApp Bot

EduAccess WhatsApp Bot is a Django-based chatbot that connects WhatsApp users to an AI assistant through Twilio. It is designed to support learning interactions by receiving messages from WhatsApp, sending them to an AI model, and replying automatically.

## Features

- WhatsApp message handling with Twilio
- AI-generated responses
- Django backend for easy customization
- Environment variable configuration with `.env`
- Ready for feature-branch and pull request workflow

## Tech Stack

- Python
- Django
- Twilio WhatsApp API
- Gemini 2.5 Flash
- SQLite for local development

## Project Structure

```text
eduaccess-whatsapp-bot/
├── eduaccess/
│   ├── manage.py
│   ├── .env
│   ├── db.sqlite3
│   ├── eduaccess/
│   └── whatsapp_bot/
├── venv/
└── README.md
## env

GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
