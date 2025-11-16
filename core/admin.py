from django.contrib import admin
from .models import ContactMessage, TransactionBroadcast

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "created_at")
    search_fields = ("name", "email", "subject")

@admin.register(TransactionBroadcast)
class TransactionBroadcastAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "user_name", "timestamp", "is_active")
    list_filter = ("status", "is_active")
    search_fields = ("title", "user_name")