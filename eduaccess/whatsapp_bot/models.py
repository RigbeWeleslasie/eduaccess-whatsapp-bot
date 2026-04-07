from django.conf import settings
from django.db import models


class UserProgress(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="learning_progress",
    )
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    last_question = models.TextField(blank=True)
    correct_answers = models.IntegerField(default=0)
    total_attempts = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username if self.user else (self.phone_number or "progress")


class PracticeQuestion(models.Model):
    question_text = models.TextField()
    answer_text = models.TextField()
    topic = models.CharField(max_length=100)
