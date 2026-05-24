# feedback/admin.py
from django.contrib import admin
from django.utils import timezone
from .models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('member', 'message_excerpt', 'is_replied', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    readonly_fields = ('member', 'user_message', 'created_at', 'replied_at')
    fields = ('member', 'user_message', 'admin_reply', 'is_replied', 'created_at', 'replied_at')

    def save_model(self, request, obj, form, change):
        """管理員填寫回覆並勾選已回覆時，自動記錄回覆時間"""
        if obj.is_replied and obj.admin_reply and not obj.replied_at:
            obj.replied_at = timezone.now()
        # 如果取消勾選已回覆，清空回覆時間
        if not obj.is_replied:
            obj.replied_at = None
        super().save_model(request, obj, form, change)

    def message_excerpt(self, obj):
        return obj.user_message[:20] + '...' if len(obj.user_message) > 20 else obj.user_message
    message_excerpt.short_description = "留言摘要"