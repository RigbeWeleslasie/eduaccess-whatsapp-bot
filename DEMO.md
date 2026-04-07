# EduAccess MVP Demo Guide

## Demo Objective

Show that EduAccess works as a lightweight mobile learning assistant for students through a clear, guided walkthrough.

## Recommended Demo Script

### 1. Open the app
- visit `http://localhost:8000/login/`
- explain that the app supports student accounts and web-based study access

### 2. Register or log in
- create a student account
- explain that progress is linked to the student account

### 3. Show the Study Assistant
- open the study assistant
- explain that the same tutor logic supports both WhatsApp and the PWA

### 4. Ask a normal academic question
- example: `Explain algebra`
- show tutor response

### 5. Show practice mode
- type `practice maths`
- let the app generate a question
- answer it
- show:
  - feedback
  - score
  - subject progress

### 6. Show a second subject
- type `practice english`
- explain that subject practice is separated and tracked

### 7. Show downloadable learning content
- type `pack algebra`
- open the generated study pack
- mention that the pack includes expanded lesson content

### 8. Show audio/transcript learning
- type `audio pack passive voice`
- open the audio lesson or transcript

### 9. Show offline/PWA angle
- open the offline library
- mention manifest/service worker/offline fallback support

## What Mentors Should See

- clear student use case
- working sign-in flow
- working tutor interface
- practice questions and grading
- subject-specific progress
- downloadable learning resources
- mobile-friendly PWA structure

## Suggested Talking Points

- The MVP focuses on accessibility and low-data learning.
- The app provides both guided study content and interactive practice.
- Core logic is modularized into tutor flow, practice flow, AI/content layer, and PWA support.
- The prototype is designed to evolve into a stronger student learning platform.
