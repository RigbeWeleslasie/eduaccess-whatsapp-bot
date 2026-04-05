from django.db import models


class UserProgress(models.Model):
    phone_number = models.CharField(max_length=20, unique=True)
    low_data_mode = models.BooleanField(default=True)
    offline_mode = models.BooleanField(default=False)
    last_question = models.TextField(blank=True)
    last_answer = models.TextField(blank=True)
    last_topic = models.CharField(max_length=100, blank=True)
    last_subject = models.CharField(max_length=50, blank=True)
    practice_difficulty = models.CharField(max_length=20, default="foundation")
    awaiting_practice_answer = models.BooleanField(default=False)
    awaiting_remediation = models.BooleanField(default=False)
    correct_answers = models.IntegerField(default=0)
    total_attempts = models.IntegerField(default=0)
    session_correct_answers = models.IntegerField(default=0)
    session_total_attempts = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    lesson_topic = models.CharField(max_length=100, blank=True)
    lesson_subject = models.CharField(max_length=50, blank=True)
    lesson_goal = models.IntegerField(default=3)
    lesson_progress = models.IntegerField(default=0)


class PracticeQuestion(models.Model):
    question_text = models.TextField()
    answer_text = models.TextField()
    topic = models.CharField(max_length=100)
    subject = models.CharField(max_length=50, default="maths")
    difficulty = models.CharField(max_length=20, default="foundation")


class LearningPack(models.Model):
    slug = models.SlugField(unique=True)
    subject = models.CharField(max_length=50)
    topic = models.CharField(max_length=100)
    title = models.CharField(max_length=150)
    summary = models.TextField()
    content = models.TextField()


class AudioLearningPack(models.Model):
    slug = models.SlugField(unique=True)
    subject = models.CharField(max_length=50)
    topic = models.CharField(max_length=100)
    title = models.CharField(max_length=150)
    summary = models.TextField()
    transcript = models.TextField()
    audio_url = models.URLField(blank=True)
    duration_label = models.CharField(max_length=50, blank=True)


class TopicProgress(models.Model):
    user = models.ForeignKey(
        UserProgress,
        on_delete=models.CASCADE,
        related_name="topic_progress",
    )
    subject = models.CharField(max_length=50)
    topic = models.CharField(max_length=100)
    attempts = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    last_outcome = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ("user", "subject", "topic")
