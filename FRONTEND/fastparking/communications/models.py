from django.db import models


class Message(models.Model):
    date_displayed = models.DateTimeField(null=True, blank=True)
    news_text = models.TextField()
    is_displayed = models.BooleanField(default=False)

    def __str__(self):
        return self.news_text
