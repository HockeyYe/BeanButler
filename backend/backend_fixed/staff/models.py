from django.db import models

class Staff(models.Model):
    """独立的员工信息"""
    name = models.CharField(max_length=50, verbose_name="员工姓名")
    phone = models.CharField(max_length=11, blank=True, verbose_name="联系电话")
    
    class Meta:
        verbose_name = "员工信息"
        verbose_name_plural = "员工信息"

    def __str__(self):
        return self.name

class WeeklySchedule(models.Model):
    """周循环排班模型"""
    WEEKDAY_CHOICES = [
        (1, '周一'), (2, '周二'), (3, '周三'), 
        (4, '周四'), (5, '周五'), (6, '周六'), (7, '周日'),
    ]
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, verbose_name="员工")
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES, verbose_name="星期几")
    # 使用 TimeField 只记录时间（如 08:00），不记录日期
    start_time = models.TimeField(verbose_name="上班时间")
    end_time = models.TimeField(verbose_name="下班时间")

    class Meta:
        verbose_name = "排班设置"
        verbose_name_plural = "排班设置"