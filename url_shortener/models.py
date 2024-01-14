from django.db import models


# Create your models here.
class UrlShortener(models.Model):
    long_url = models.CharField(max_length=50, unique=True)
    short_url = models.CharField(max_length=5, unique=True)

    class Meta:
        db_table = 'long_short_url'
