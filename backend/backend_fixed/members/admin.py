from django.contrib import admin
from .models import Member

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display  = ('name', 'nickname', 'student_id', 'openid', 'phone', 'level', 'points', 'joined_at')
    list_editable = ('level', 'points')
    search_fields = ('name', 'nickname', 'student_id', 'openid', 'phone')
    list_filter   = ('level',)
    fieldsets = (
        ('身份信息', {
            'fields': ('name', 'nickname'),
            'description': 'name = 真实姓名（用于核验），nickname = 微信昵称或自定义显示名。',
        }),
        ('账号标识', {
            'fields': ('student_id', 'openid'),
            'description': 'student_id = 校园学号（唯一），openid = 微信 OpenID（由登录接口写入）。',
        }),
        ('联系方式', {'fields': ('phone',)}),
        ('会员状态', {'fields': ('level', 'points')}),
    )
