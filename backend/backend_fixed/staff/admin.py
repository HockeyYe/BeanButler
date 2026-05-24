from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from .models import Staff, WeeklySchedule
from django import forms

class WeeklyScheduleForm(forms.ModelForm):
    class Meta:
        model = WeeklySchedule
        fields = '__all__'
        widgets = {
            # 强制原生 HTML5 时间选择器以 1800 秒（30分钟）为间隔
            'start_time': forms.TimeInput(attrs={'step': 1800, 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'step': 1800, 'type': 'time'}),
        }

# 1. 必须注册 Staff，它才会出现在侧边栏
@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone')
    search_fields = ('name',)

@admin.register(WeeklySchedule)
class WeeklyScheduleAdmin(admin.ModelAdmin):
    form = WeeklyScheduleForm
    # 只保留关键表头：员工、星期、时间范围
    list_display = ('staff', 'display_weekday', 'time_range')
    
    def time_range(self, obj):
        return f"{obj.start_time.strftime('%H:%M')} - {obj.end_time.strftime('%H:%M')}"
    time_range.short_description = '上班时间'
    
    def display_weekday(self, obj):
        return obj.get_weekday_display()
    display_weekday.short_description = '星期几'

    # 为了实现“更便捷”，建议在 formfield_for_dbfield 中针对时间字段
    # 强制设置步长为 1800 秒（30分钟）
    def formfield_for_dbfield(self, db_field, **kwargs):
        field = super().formfield_for_dbfield(db_field, **kwargs)
        if db_field.name in ['start_time', 'end_time']:
            field.widget.attrs['step'] = 1800  # 限制选择器以30分钟为跳动单位
        return field