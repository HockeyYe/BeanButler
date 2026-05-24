from django.db import models


class Coupon(models.Model):
    """
    滿減券
    - min_spend:       消費門檻（例如 30）
    - discount_amount: 折扣金額（例如 5）
    - 顯示名稱自動產生：滿 MOP 30 減 MOP 5
    """
    member          = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='coupons',
        verbose_name='所屬會員',
    )
    name            = models.CharField(max_length=100, verbose_name='券名稱')
    min_spend       = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='最低消費門檻 (MOP)')
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='折扣金額 (MOP)')
    expire_date     = models.DateField(verbose_name='到期日')
    is_used         = models.BooleanField(default=False, verbose_name='已使用')
    created_at      = models.DateTimeField(auto_now_add=True, verbose_name='發放時間')

    class Meta:
        verbose_name        = '優惠券'
        verbose_name_plural = '優惠券'
        ordering            = ['-created_at']

    def __str__(self):
        status = '已用' if self.is_used else '可用'
        return f'[{status}] {self.name}  滿{self.min_spend}減{self.discount_amount}  → {self.member.name}'
