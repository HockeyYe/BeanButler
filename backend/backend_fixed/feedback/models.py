# feedback/models.py
from django.db import models

class Feedback(models.Model):
    # --- Relationship ---
    # 核心：关联会员，而非订单
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, verbose_name="Associated Member")
    
    # --- Content Details ---
    user_message = models.TextField(
        verbose_name="Customer Inquiry", 
        help_text="Original message submitted by the member from the ordering terminal."
    )
    admin_reply = models.TextField(
        verbose_name="Official Resolution", 
        blank=True, 
        null=True, 
        help_text="Administrative response/feedback to be transmitted back to the member."
    )
    
    # --- Status & Timestamps ---
    is_replied = models.BooleanField(
        default=False, 
        verbose_name="Response Status" # 翻译为响应状态，更专业
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Submission Timestamp"
    )
    replied_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Resolution Timestamp"
    )

    class Meta:
        # 翻译为“客户心声与互动”或“咨询管理”
        verbose_name = "Customer Feedback & Interaction"
        verbose_name_plural = "Customer Feedback & Interaction"
        ordering = ['-created_at'] # 最新的留言排在最前面

    def __str__(self):
        # 这里的返回文字也需要英文处理
        return f"Inquiry from {self.member.name}"