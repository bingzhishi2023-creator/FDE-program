from django.contrib import admin
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "active")
    list_filter = ("active",)
    search_fields = ("title", "text")
