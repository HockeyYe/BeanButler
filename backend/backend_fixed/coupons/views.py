from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
import json
from .models import Coupon


# 可兌換的滿減券選項（固定配置，不放資料庫）
REDEEM_OPTIONS = [
    {'id': 1, 'name': '滿減券 MOP 5',  'min_spend': 30,  'discount_amount': 5,  'points_cost': 50,  'validity_days': 30},
    {'id': 2, 'name': '滿減券 MOP 10', 'min_spend': 60,  'discount_amount': 10, 'points_cost': 100, 'validity_days': 30},
    {'id': 3, 'name': '滿減券 MOP 20', 'min_spend': 100, 'discount_amount': 20, 'points_cost': 180, 'validity_days': 30},
]


@require_http_methods(['GET'])
def coupon_list(request):
    """
    GET /api/coupons/?member_id=123
    回傳該會員所有「未使用 + 未過期」的滿減券
    """
    member_id = request.GET.get('member_id')
    if not member_id:
        return JsonResponse({'success': False, 'error': 'member_id is required'}, status=400)

    today = timezone.now().date()
    coupons = Coupon.objects.filter(
        member_id=member_id,
        is_used=False,
        expire_date__gte=today,
    )

    data = []
    for c in coupons:
        data.append({
            'id':              c.id,
            'name':            c.name,
            'min_spend':       float(c.min_spend),
            'discount_amount': float(c.discount_amount),
            'expire_date':     c.expire_date.strftime('%Y-%m-%d'),
            'is_used':         c.is_used,
            'condition_text':  f'滿 MOP {int(c.min_spend)} 可用',
            'discount_text':   f'減 MOP {int(c.discount_amount)}',
        })

    return JsonResponse({'success': True, 'coupons': data})


@csrf_exempt
@require_http_methods(['GET'])
def redeem_options(request):
    """GET /api/coupons/options/ — 回傳可兌換選項"""
    return JsonResponse({'success': True, 'options': REDEEM_OPTIONS})


@csrf_exempt
@require_http_methods(['POST'])
def redeem_coupon(request):
    """
    POST /api/coupons/redeem/
    Body: { member_id, option_id }
    扣積分 + 建 Coupon 記錄
    """
    from members.models import Member

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    member_id = data.get('member_id')
    option_id = data.get('option_id')

    if not member_id or not option_id:
        return JsonResponse({'success': False, 'error': 'member_id and option_id required'}, status=400)

    # 找兌換選項
    option = next((o for o in REDEEM_OPTIONS if o['id'] == option_id), None)
    if not option:
        return JsonResponse({'success': False, 'error': 'Invalid option_id'}, status=400)

    # 找會員
    try:
        member = Member.objects.get(id=member_id)
    except Member.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Member not found'}, status=404)

    # 檢查積分夠不夠
    if member.points < option['points_cost']:
        return JsonResponse({'success': False, 'error': '積分不足'}, status=400)

    # 扣積分
    member.points -= option['points_cost']
    member.save(update_fields=['points'])

    # 建 Coupon 記錄
    expire_date = timezone.now().date() + timedelta(days=option['validity_days'])
    coupon = Coupon.objects.create(
        member=member,
        name=option['name'],
        min_spend=option['min_spend'],
        discount_amount=option['discount_amount'],
        expire_date=expire_date,
        is_used=False,
    )

    return JsonResponse({
        'success':        True,
        'remaining_points': member.points,
        'coupon': {
            'id':              coupon.id,
            'name':            coupon.name,
            'min_spend':       float(coupon.min_spend),
            'discount_amount': float(coupon.discount_amount),
            'expire_date':     coupon.expire_date.strftime('%Y-%m-%d'),
            'condition_text':  f'滿 MOP {int(coupon.min_spend)} 可用',
            'discount_text':   f'減 MOP {int(coupon.discount_amount)}',
        }
    })

