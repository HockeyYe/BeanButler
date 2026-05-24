from django.contrib import admin
from .models import Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display  = ('name', 'member', 'min_spend', 'discount_amount', 'expire_date', 'is_used', 'created_at')
    list_filter   = ('is_used', 'expire_date')
    search_fields = ('name', 'member__name')
    list_editable = ('is_used',)
    ordering      = ('-created_at',)
