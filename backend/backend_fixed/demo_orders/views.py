from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
from .models import Product, Order, OrderItem
from members.models import Member
from coupons.models import Coupon


# ─────────────────────────────────────────────
#  Timezone helper — handles both naive & aware datetimes
# ─────────────────────────────────────────────
def safe_localtime(dt):
    """Convert dt to local time safely, whether it is naive or aware."""
    if dt is None:
        return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.utc)
    return timezone.localtime(dt)


@require_http_methods(['GET'])
def product_list(request):
    """GET /api/products/"""
    products = Product.objects.filter(is_available=True).prefetch_related('linked_beans')
    data = []
    for p in products:
        beans = list(p.linked_beans.values_list('name', flat=True))
        temps   = [t.strip() for t in p.available_temps.split(',')]   if p.available_temps   else []
        sugars  = [t.strip() for t in p.available_sugars.split(',')]  if p.available_sugars  else []
        data.append({
            'id':                   str(p.id),
            'name':                 p.name,
            'category':             p.category,          # raw key: ESPRESSO / POUROVER / NON-CAFFEINE / SPECIAL
            'category_label':       p.get_category_display(),
            'price':                float(p.price),
            'desc':                 p.description,
            'image':                request.build_absolute_uri(p.image.url) if p.image else '',
            'is_recommended':       p.is_recommended,
            'allow_bean_selection': p.allow_bean_selection,
            'linked_beans':         beans,
            'available_temps':      temps,
            'available_sugars':     sugars,
        })
    return JsonResponse({'success': True, 'products': data})


@csrf_exempt
@require_http_methods(['POST'])
def create_order(request):
    """POST /api/orders/"""
    # ── 1. 解析 JSON ──────────────────────────────────────────
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    member_id   = data.get('member_id')
    items       = data.get('items', [])
    total_price = data.get('total_price', 0)
    pickup_time = data.get('pickup_time', '立即取餐')
    pickup_code = data.get('pickup_code', '')
    coupon_id   = data.get('coupon_id')   # ← 新增：滿減券 ID（可為 None）

    # ── 2. 基本驗證 ────────────────────────────────────────────
    if not items:
        return JsonResponse({'success': False, 'error': '訂單不能是空的'}, status=400)

    try:
        total_price = float(total_price)
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'total_price 格式錯誤'}, status=400)

    if total_price <= 0:
        return JsonResponse({'success': False, 'error': 'total_price 必須大於 0'}, status=400)

    # 檢查每個品項都有必要欄位
    for i, item in enumerate(items):
        if not item.get('id'):
            return JsonResponse({'success': False, 'error': f'第 {i+1} 項缺少 product id'}, status=400)
        if not item.get('name'):
            return JsonResponse({'success': False, 'error': f'第 {i+1} 項缺少 name'}, status=400)
        qty = item.get('quantity', 1)
        if not isinstance(qty, int) or qty < 1:
            return JsonResponse({'success': False, 'error': f'第 {i+1} 項 quantity 必須是正整數'}, status=400)

    # ── 3. 查會員（允許匿名下單）──────────────────────────────
    member = None
    if member_id:
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Member not found'}, status=404)

    # ── 4. 建立 Order（先用 TEMP，生成後更新）────────────────────
    from datetime import date

    today_str = date.today().strftime('%Y%m%d')
    # 找今天最後一筆訂單的序號
    last_today = (
        Order.objects
        .filter(order_number__startswith=today_str)
        .order_by('-order_number')
        .first()
    )
    if last_today and len(last_today.order_number) > 8:
        try:
            seq = int(last_today.order_number[8:]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1

    order_number_str = f'{today_str}{seq:03d}'   # e.g. 20260318001
    pickup_code_str  = f'{seq:03d}'               # e.g. 001

    order = Order.objects.create(
        member=member,
        total_price=total_price,
        pickup_time=pickup_time,
        pickup_code=pickup_code_str,
        status='PENDING',
        items_json=json.dumps(items, ensure_ascii=False),
        order_number=order_number_str,
    )

    # ── 5. 寫入 OrderItem（為日後庫存扣減、銷售統計鋪路）──────
    for item in items:
        try:
            product = Product.objects.get(id=int(item['id']))
        except (Product.DoesNotExist, ValueError, TypeError):
            product = None  # 商品若已下架或 id 格式不符，product 留 null

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=item.get('quantity', 1),
            price_at_order=item.get('price', 0),
            # Frontend may send customization.temp or customization.ice (both accepted)
            selected_temp=item.get('customization', {}).get('temp', '')
                       or item.get('customization', {}).get('ice', ''),
            # Frontend may send customization.sugar or customization.sweetness (both accepted)
            selected_sugar=item.get('customization', {}).get('sugar', '')
                        or item.get('customization', {}).get('sweetness', ''),
        )

    # ── 6. 核銷優惠券 ─────────────────────────────────────────
    if coupon_id and member:
        try:
            coupon = Coupon.objects.get(id=coupon_id, member=member, is_used=False)
            coupon.is_used = True
            coupon.save(update_fields=['is_used'])
        except Coupon.DoesNotExist:
            pass  # 券不存在或已用過，靜默忽略

    # ── 7. 積分在取餐（PICKED_UP）時才給，此處不加 ────────────
    return JsonResponse({
        'success': True,
        'order_id':      order.id,
        'order_no':      order.order_number,
        'pickup_code':   order.pickup_code,
        'earned_points': 0,       # 取餐後才實際入帳
        'level_up':      False,
        'current_level': member.level if member else None,
    })


@require_http_methods(['GET'])
def recommendations(request):
    """GET /api/recommendations/?member_id=123
    Returns top-3 recommended products for a member.
    Falls back to global top-3 popular products for cold-start / guests.
    """
    from .models import Recommendation

    member_id = request.GET.get('member_id')

    def _product_to_dict(p):
        return {
            'id':    str(p.id),
            'name':  p.name,
            'price': float(p.price),
            'image': request.build_absolute_uri(p.image.url) if p.image else '',
            'desc':  p.description,
        }

    # Try personalised recommendations
    if member_id:
        try:
            rec = Recommendation.objects.get(member_id=member_id)
            names = json.loads(rec.items_json)
            products = [
                _product_to_dict(p)
                for p in Product.objects.filter(name__in=names, is_available=True)
            ]
            if products:
                return JsonResponse({'success': True, 'source': 'cf', 'recommendations': products})
        except Recommendation.DoesNotExist:
            pass

    # Fallback: global top-3 by order count
    # Primary: OrderItem rows; fallback: items_json for SQL-inserted historical orders
    from django.db.models import Count
    from collections import Counter

    # Count from OrderItem rows (new API orders)
    orderitem_counts = (
        OrderItem.objects
        .filter(order__status='PICKED_UP', product__is_available=True)
        .values('product_id')
        .annotate(cnt=Count('id'))
        .order_by('-cnt')[:10]
    )
    top_ids_from_items = [row['product_id'] for row in orderitem_counts]

    # If OrderItem is empty (all historical SQL data), parse items_json
    if not top_ids_from_items:
        name_counter = Counter()
        historical_orders = Order.objects.filter(status='PICKED_UP').exclude(items_json__in=['', '[]'])
        for order in historical_orders:
            try:
                for item in json.loads(order.items_json):
                    name = item.get('name', '').strip()
                    if name:
                        name_counter[name] += item.get('quantity', 1)
            except (json.JSONDecodeError, TypeError):
                pass
        top_names = [name for name, _ in name_counter.most_common(3)]
        products = [
            _product_to_dict(p)
            for p in Product.objects.filter(name__in=top_names, is_available=True)
        ]
    else:
        products = [_product_to_dict(p) for p in Product.objects.filter(id__in=top_ids_from_items[:3])]

    return JsonResponse({'success': True, 'source': 'popular', 'recommendations': products})


@require_http_methods(['GET'])
def order_list(request):
    """GET /api/orders/list/?member_id=123"""
    member_id = request.GET.get('member_id')
    orders = Order.objects.filter(member_id=member_id).order_by('-created_at')
    data = []
    for o in orders:
        items = json.loads(o.items_json) if o.items_json else []
        data.append({
            'id':           str(o.id),
            'order_no':     o.order_number,
            'status':       o.status,
            'status_label': o.get_status_display(),
            'create_time':  safe_localtime(o.created_at).strftime('%Y-%m-%d %H:%M'),
            'pickup_code':  o.pickup_code,
            'total_price':  float(o.total_price),
            'items':        items,
        })
    return JsonResponse({'success': True, 'orders': data})
