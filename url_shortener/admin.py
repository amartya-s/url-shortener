from django.contrib import admin

# Register your models here.
from django.contrib import admin
from url_shortener.models import UrlShortener


class UrlShortenerAdmin(admin.ModelAdmin):
    pass


admin.site.register(UrlShortener, UrlShortenerAdmin)
