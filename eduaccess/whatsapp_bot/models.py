
from django.db import models

class UserProgress(models.Model):
    phone_number = models.CharField(max_length=20, unique=True)
    last_question = models.TextField(blank=True)
    correct_answers = models.IntegerField(default=0)
    total_attempts = models.IntegerField(default=0)

class PracticeQuestion(models.Model):
    question_text = models.TextField()
    answer_text = models.TextField()
    topic = models.CharField(max_length=100)