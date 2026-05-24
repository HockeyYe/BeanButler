from django.db import models

class AnalyticsDashboard(models.Model):
    # 这是一个占位模型，后续可以由同伴扩展为真正的报表数据表
    title = models.CharField(max_length=100, default="Global Sales Overview", verbose_name="报表标题")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")

    class Meta:
        verbose_name = "Reporting System (BI)"  # 对应 Proposal 2.2.4
        verbose_name_plural = verbose_name