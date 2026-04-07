from django.contrib import admin

from .models import AudioLearningPack, LearningPack, PracticeQuestion, TopicProgress, UserProgress


admin.site.register(UserProgress)
admin.site.register(PracticeQuestion)
admin.site.register(TopicProgress)
admin.site.register(LearningPack)
admin.site.register(AudioLearningPack)
