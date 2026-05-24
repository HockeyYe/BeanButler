import json
from datetime import date, timedelta, datetime
from django.shortcuts import render
from django.contrib import admin
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, F, FloatField, Min, Max
from django.db.models.functions import TruncDate, ExtractHour, TruncMonth, ExtractWeekDay


def admin_index(request):
    context = admin.site.each_context(request)
    return render(request, 'admin/bi_dashboard.html', context)


def dashboard_data(request):
    from demo_orders.models import Order, OrderItem
    from members.models import Member

    today             = date.today()
    yesterday         = today - timedelta(days=1)
    thirty_days_ago   = today - timedelta(days=30)
    twelve_months_ago = today - timedelta(days=365)

    # ── PARSE RANGE FILTER ────────────────────────────────────
    range_param = request.GET.get('range', '30d')
    start_param = request.GET.get('start', '')
    end_param   = request.GET.get('end', '')

    if range_param == '1y':
        filter_start = twelve_months_ago
        filter_end   = today
        range_label  = '過去 1 年'
    elif range_param == 'all':
        filter_start = None
        filter_end   = today
        range_label  = '全部時間'
    elif range_param == '1d':  # ✅ 新增：處理前端傳來的 "今日 (1d)" 篩選
        filter_start = today
        filter_end   = today
        range_label  = '今日'
    elif range_param == 'custom' and start_param and end_param:
        try:
            filter_start = datetime.strptime(start_param, '%Y-%m-%d').date()
            filter_end   = datetime.strptime(end_param,   '%Y-%m-%d').date()
            range_label  = f'{start_param} ~ {end_param}'
        except ValueError:
            filter_start = thirty_days_ago
            filter_end   = today
            range_label  = '過去 30 天'
    else:
        range_param  = '30d'
        filter_start = thirty_days_ago
        filter_end   = today
        range_label  = '過去 30 天'

    def apply_date_filter(qs, date_field='order__created_at__date'):
        if filter_start:
            qs = qs.filter(**{f'{date_field}__gte': filter_start})
        return qs.filter(**{f'{date_field}__lte': filter_end})

    def apply_order_date_filter(qs, date_field='created_at__date'):
        if filter_start:
            qs = qs.filter(**{f'{date_field}__gte': filter_start})
        return qs.filter(**{f'{date_field}__lte': filter_end})

    # ── TODAY KPIs (always fixed, no range filter) ────────────
    def day_stats(d):
        qs  = Order.objects.filter(created_at__date=d)
        rev = float(qs.filter(status='PICKED_UP').aggregate(v=Sum('total_price'))['v'] or 0)
        cnt = qs.count()
        avg = float(qs.aggregate(v=Avg('total_price'))['v'] or 0)
        mem = qs.filter(member__isnull=False).count()
        return rev, cnt, avg, mem

    t_rev, t_cnt, t_avg, t_mem = day_stats(today)
    y_rev, y_cnt, y_avg, y_mem = day_stats(yesterday)

    def pct_change(new, old):
        if old == 0: return None
        return round((new - old) / old * 100, 1)

    # ── OVERALL: PERIOD REVENUE STATS (range-filtered) ────────
    period_qs  = apply_order_date_filter(Order.objects.filter(status='PICKED_UP'))
    period_rev = float(period_qs.aggregate(v=Sum('total_price'))['v'] or 0)
    period_cnt = period_qs.count()
    period_avg = float(period_qs.aggregate(v=Avg('total_price'))['v'] or 0)

    # Operating days in period (days that had at least 1 PICKED_UP order)
    operating_days_qs = (apply_order_date_filter(Order.objects.filter(status='PICKED_UP'))
                         .annotate(day=TruncDate('created_at'))
                         .values('day').distinct())
    operating_days = operating_days_qs.count() or 1
    rev_per_day = round(period_rev / operating_days, 1)

    # Monthly revenue breakdown (range-filtered)
    monthly_rev_qs = (apply_order_date_filter(Order.objects.filter(status='PICKED_UP'))
                      .annotate(month=TruncMonth('created_at'))
                      .values('month')
                      .annotate(rev=Sum('total_price'), cnt=Count('id'))
                      .order_by('month'))
    monthly_rev = [
        {'m': r['month'].strftime('%Y/%m'), 'rev': float(r['rev'] or 0), 'cnt': r['cnt']}
        for r in monthly_rev_qs
    ]

    # Day-of-week revenue (range-filtered): 1=Sun ... 7=Sat in Django ExtractWeekDay
    DOW_LABEL = {1:'日', 2:'一', 3:'二', 4:'三', 5:'四', 6:'五', 7:'六'}
    dow_qs = (apply_order_date_filter(Order.objects.filter(status='PICKED_UP'))
              .annotate(dow=ExtractWeekDay('created_at'))
              .values('dow')
              .annotate(rev=Sum('total_price'), cnt=Count('id'))
              .order_by('dow'))
    dow_map = {r['dow']: {'rev': float(r['rev'] or 0), 'cnt': r['cnt']} for r in dow_qs}
    dow_data = [
        {'d': DOW_LABEL.get(i, str(i)),
         'rev': dow_map.get(i, {}).get('rev', 0),
         'cnt': dow_map.get(i, {}).get('cnt', 0)}
        for i in range(1, 8)
    ]

    # All-time totals (always full, ignore range filter)
    alltime_rev = float(Order.objects.filter(status='PICKED_UP')
                        .aggregate(v=Sum('total_price'))['v'] or 0)
    alltime_cnt = Order.objects.filter(status='PICKED_UP').count()

    # ── 30-DAY REVENUE TREND (always fixed 30d window for Sales tab) ──
    rev_qs = (Order.objects
              .filter(created_at__date__gte=thirty_days_ago, status='PICKED_UP')
              .annotate(day=TruncDate('created_at'))
              .values('day').annotate(rev=Sum('total_price')).order_by('day'))
    rev_map = {r['day']: float(r['rev']) for r in rev_qs}
    days30 = []
    for i in range(30):
        d = thirty_days_ago + timedelta(days=i)
        days30.append({'date': d.strftime('%m/%d'), 'rev': rev_map.get(d, 0)})

    # ── HOURLY DISTRIBUTION (range-filtered) ───────────────────────────
    # ✅ 修正：改用 apply_order_date_filter，讓每小時分佈可以套用 1天/1年/全部 等時間範圍
    hourly_qs = (apply_order_date_filter(Order.objects.all())
                 .annotate(hour=ExtractHour('created_at'))
                 .values('hour').annotate(count=Count('id')).order_by('hour'))
    hourly_map = {h['hour']: h['count'] for h in hourly_qs}
    hourly = [{'h': f'{h:02d}', 'n': hourly_map.get(h, 0)} for h in range(8, 22)]

    # ── CATEGORY REVENUE (range-filtered) ────────────────────
    CAT_LABEL = {
        'ESPRESSO': '意式咖啡', 'POUROVER': '手沖滴濾',
        'NON-CAFFEINE': '無咖啡因', 'SPECIAL': '招牌特調',
    }
    cat_qs = (apply_date_filter(OrderItem.objects.filter(order__status='PICKED_UP'))
              .values('product__category')
              .annotate(rev=Sum(F('price_at_order') * F('quantity'), output_field=FloatField()))
              .order_by('-rev'))
    total_cat_rev = sum(float(c['rev'] or 0) for c in cat_qs)
    cat_data = [
        {'name': CAT_LABEL.get(c['product__category'], c['product__category'] or '其他'),
         'rev': float(c['rev'] or 0),
         'pct': round(float(c['rev'] or 0) / max(total_cat_rev, 1) * 100)}
        for c in cat_qs if c['product__category']
    ]

    # ── TOP PRODUCTS (range-filtered) ────────────────────────
    top_qs = (apply_date_filter(OrderItem.objects.all())
              .values('product__name').annotate(total=Sum('quantity')).order_by('-total')[:8])
    top_products = [
        {'name': t['product__name'] or '已刪除商品', 'sales': t['total']} for t in top_qs
    ]

    # ── PREFERENCES (range-filtered) ─────────────────────────
    TEMP_LABEL  = {'HOT': '熱飲', 'ICE': '正常冰', 'LESS_ICE': '少冰', 'NO_ICE': '去冰'}
    SUGAR_LABEL = {'NORMAL': '全糖', 'MORE': '多糖', 'LESS': '少糖', 'NONE': '無糖'}

    temp_qs  = (apply_date_filter(OrderItem.objects.exclude(selected_temp=''))
                .values('selected_temp').annotate(count=Count('id')).order_by('-count'))
    sugar_qs = (apply_date_filter(OrderItem.objects.exclude(selected_sugar=''))
                .values('selected_sugar').annotate(count=Count('id')).order_by('-count'))
    bean_qs  = (apply_date_filter(OrderItem.objects.filter(selected_bean__isnull=False))
                .values('selected_bean__name').annotate(count=Count('id')).order_by('-count'))

    temp_total  = sum(r['count'] for r in temp_qs)
    sugar_total = sum(r['count'] for r in sugar_qs)
    bean_total  = sum(r['count'] for r in bean_qs)

    temp_data  = [{'n': TEMP_LABEL.get(r['selected_temp'],  r['selected_temp']),
                   'v': round(r['count'] / max(temp_total,  1) * 100)} for r in temp_qs]
    sugar_data = [{'n': SUGAR_LABEL.get(r['selected_sugar'], r['selected_sugar']),
                   'v': round(r['count'] / max(sugar_total, 1) * 100)} for r in sugar_qs]
    bean_data  = [{'n': r['selected_bean__name'],
                   'v': round(r['count'] / max(bean_total,  1) * 100)} for r in bean_qs]

    # ── MEMBER LEVELS ─────────────────────────────────────────
    LEVEL_LABEL = {'GOLD': '金牌', 'SILVER': '銀牌', 'BRONZE': '銅牌'}
    LEVEL_COL   = {'GOLD': '#c47a30', 'SILVER': '#8b9bb4', 'BRONZE': '#7a6555'}
    level_qs    = Member.objects.values('level').annotate(count=Count('id'))
    level_map   = {l['level']: l['count'] for l in level_qs}
    levels      = [{'name': LEVEL_LABEL[lv], 'count': level_map.get(lv, 0), 'col': LEVEL_COL[lv]}
                   for lv in ['GOLD', 'SILVER', 'BRONZE']]
    total_members  = sum(l['count'] for l in levels)
    new_this_month = Member.objects.filter(
        joined_at__year=today.year, joined_at__month=today.month).count()

    active_ids  = (Order.objects.filter(created_at__date__gte=thirty_days_ago, member__isnull=False)
                   .values_list('member_id', flat=True).distinct())
    active_rate = round(len(active_ids) / max(total_members, 1) * 100)

    spend_qs  = (Order.objects.filter(member__isnull=False)
                 .values('member__level').annotate(avg_spend=Avg('total_price'), order_count=Count('id')))
    spend_map = {s['member__level']: s for s in spend_qs}
    freq_qs   = (Order.objects.filter(member__isnull=False, created_at__date__gte=thirty_days_ago)
                 .values('member__level', 'member_id').annotate(cnt=Count('id')))
    freq_map = {}; freq_cnt_map = {}
    for r in freq_qs:
        lv = r['member__level']
        freq_map[lv]     = freq_map.get(lv, 0) + r['cnt']
        freq_cnt_map[lv] = freq_cnt_map.get(lv, 0) + 1

    spend_data = []
    for lv in ['BRONZE', 'SILVER', 'GOLD']:
        sm = spend_map.get(lv, {})
        fc_cnt = freq_cnt_map.get(lv, 1)
        spend_data.append({'lv': LEVEL_LABEL[lv],
                           'avg': round(float(sm.get('avg_spend') or 0), 1),
                           'freq': round(freq_map.get(lv, 0) / max(fc_cnt, 1), 1)})

    growth_qs = (Member.objects.filter(joined_at__gte=twelve_months_ago)
                 .annotate(month=TruncMonth('joined_at'))
                 .values('month').annotate(new=Count('id')).order_by('month'))
    growth_raw = {g['month'].strftime('%b'): g['new'] for g in growth_qs}
    months_12  = list(dict.fromkeys(
        [(today.replace(day=1) - timedelta(days=i*28)).strftime('%b') for i in range(11,-1,-1)]))
    cumulative_base = Member.objects.filter(
        joined_at__lt=(today.replace(day=1) - timedelta(days=11*28))).count()
    growth_data = []
    running = cumulative_base
    for m in months_12:
        new_cnt = growth_raw.get(m, 0); running += new_cnt
        growth_data.append({'m': m, 'new': new_cnt, 'total': running})

    all_orders  = Order.objects.count()
    mem_orders  = Order.objects.filter(member__isnull=False).count()
    mem_pct     = round(mem_orders / max(all_orders, 1) * 100)
    mem_rev_val = float(Order.objects.filter(status='PICKED_UP', member__isnull=False)
                        .aggregate(v=Sum('total_price'))['v'] or 0)
    mem_rev_pct = round(mem_rev_val / max(alltime_rev, 1) * 100)

    # ══════════════════════════════════════════════════════════
    # ── FORECAST: always uses ALL historical data ─────────────
    # ══════════════════════════════════════════════════════════
    all_daily_qs = (Order.objects
                    .filter(status='PICKED_UP')
                    .annotate(day=TruncDate('created_at'))
                    .values('day')
                    .annotate(rev=Sum('total_price'))
                    .order_by('day'))
    all_daily_map = {r['day']: float(r['rev']) for r in all_daily_qs}

    fc_hist_labels = []
    fc_hist_rev    = []
    if all_daily_map:
        first_day = min(all_daily_map.keys())
        last_day  = max(all_daily_map.keys())
        # Build complete daily series from first order to today
        num_days = (today - first_day).days + 1
        full_series = []
        full_labels = []
        for i in range(num_days):
            d = first_day + timedelta(days=i)
            full_series.append(all_daily_map.get(d, 0))
            full_labels.append(d.strftime('%m/%d'))

        # Exponential smoothing on full history
        alpha = 0.3
        s = full_series[0]
        smoothed = [s]
        for v in full_series[1:]:
            s = alpha * v + (1 - alpha) * s
            smoothed.append(s)
        es = smoothed[-1]

        # RMSE on last 30 fitted vs actual for CI
        n_fit = min(30, len(full_series))
        actual_tail  = full_series[-n_fit:]
        smoothed_tail = smoothed[-n_fit:]
        resid = (sum((a-f)**2 for a,f in zip(actual_tail, smoothed_tail)) / max(n_fit,1)) ** 0.5

        # Show last 30 days as historical context in chart
        fc_hist_labels = full_labels[-30:]
        fc_hist_rev    = full_series[-30:]

        fc_data_start = first_day.strftime('%Y%m%d')
        fc_data_days  = num_days
    else:
        es    = 0
        resid = 0
        fc_data_start = today.strftime('%Y%m%d')
        fc_data_days  = 0

    WK_MULT = [1.0, 1.05, 1.10, 1.05, 0.95, 1.30, 1.38]
    fc_labels, fc_pred, fc_low, fc_high = [], [], [], []
    for i in range(14):
        d = today + timedelta(days=i+1)
        fc_labels.append(d.strftime('%m/%d'))
        mult = WK_MULT[d.weekday()]
        pred = round(es * mult * (1 + i * 0.005))
        ci   = round(resid * 1.96 * (1 + i * 0.07))
        fc_pred.append(pred); fc_low.append(max(0, pred-ci)); fc_high.append(pred+ci)

    fc_7day_total = sum(fc_pred[:7])
    best_idx = fc_pred[:7].index(max(fc_pred[:7])) if fc_pred else 0
    best_day = fc_labels[best_idx] if fc_labels else '-'
    best_rev = fc_pred[best_idx]   if fc_pred  else 0

    THRESHOLDS = {'BRONZE': 100, 'SILVER': 300}
    def upgrade_eta(from_level, to_level, threshold):
        members    = Member.objects.filter(level=from_level)
        count      = members.count()
        avg_pts    = float(members.aggregate(v=Avg('points'))['v'] or 0)
        avg_gap    = max(0, threshold - avg_pts)
        weekly_qs  = (Order.objects.filter(member__level=from_level,
                      created_at__date__gte=thirty_days_ago, status='PICKED_UP')
                      .values('member_id').annotate(rev=Sum('total_price')))
        weekly_earn = (float(weekly_qs.aggregate(avg=Avg('rev'))['avg'] or 0) / 4
                       if weekly_qs.exists() else (20 if from_level == 'BRONZE' else 40))
        weekly_earn = max(weekly_earn, 1)
        return {'from': LEVEL_LABEL[from_level], 'to': LEVEL_LABEL[to_level],
                'count': count, 'avg_pts': round(avg_pts), 'avg_gap': round(avg_gap),
                'weekly_earn': round(weekly_earn), 'weeks': round(avg_gap/weekly_earn, 1),
                'pct': min(round(avg_pts/threshold*100) if threshold else 100, 100),
                'col': LEVEL_COL[from_level]}

    upgrade_data = [upgrade_eta('BRONZE','SILVER',100), upgrade_eta('SILVER','GOLD',300)]
    near_upgrade = (Member.objects.filter(level='BRONZE', points__gte=80).count() +
                    Member.objects.filter(level='SILVER', points__gte=280).count())

    # Demand forecast also uses all data (not range-filtered)
    demand_qs = (OrderItem.objects.all()
                 .values('product__name', 'product__category')
                 .annotate(total=Sum('quantity')).order_by('-total')[:6])
    demand_fc = []
    for d2 in demand_qs:
        weekly_avg = round(d2['total'] / max(fc_data_days / 7, 1))
        next_wk    = round(weekly_avg * 1.05)
        demand_fc.append({'name': d2['product__name'] or '未知', 'pred': next_wk,
                          'trend': 'up' if next_wk >= weekly_avg else 'dn'})

    data = {
        'range': {'active': range_param, 'label': range_label,
                  'start': filter_start.isoformat() if filter_start else None,
                  'end':   filter_end.isoformat()},
        'kpi': {
            'today_rev': round(t_rev, 1), 'today_orders': t_cnt,
            'today_avg': round(t_avg, 1),
            'member_rate': round(t_mem / max(t_cnt, 1) * 100),
            'rev_chg':      pct_change(t_rev, y_rev),
            'orders_chg':   pct_change(t_cnt, y_cnt),
            'avg_chg':      pct_change(t_avg, y_avg),
            'mem_rate_chg': pct_change(t_mem/max(t_cnt,1), y_mem/max(y_cnt,1)) if y_cnt else None,
        },
        'overall': {
            'period_rev':      round(period_rev, 1),
            'period_cnt':      period_cnt,
            'period_avg':      round(period_avg, 1),
            'rev_per_day':     rev_per_day,
            'operating_days':  operating_days,
            'alltime_rev':     round(alltime_rev, 1),
            'alltime_cnt':     alltime_cnt,
            'monthly_rev':     monthly_rev,
            'dow_data':        dow_data,
        },
        'days30':       days30,
        'hourly':       hourly,
        'cat_data':     cat_data,
        'top_products': top_products,
        'prefs':        {'temp': temp_data, 'sugar': sugar_data, 'bean': bean_data},
        'members': {
            'levels': levels, 'total': total_members, 'new_month': new_this_month,
            'active_rate': active_rate, 'spend_data': spend_data, 'growth': growth_data,
            'mem_pct': mem_pct, 'mem_rev_pct': mem_rev_pct,
        },
        'forecast': {
            'hist_labels':  fc_hist_labels,
            'hist_rev':     fc_hist_rev,
            'fc_labels':    fc_labels,
            'fc_pred':      fc_pred,
            'fc_low':       fc_low,
            'fc_high':      fc_high,
            'fc_7day':      fc_7day_total,
            'best_day':     best_day,
            'best_rev':     best_rev,
            'near_upgrade': near_upgrade,
            'upgrade_data': upgrade_data,
            'demand_fc':    demand_fc,
            'data_start':   fc_data_start,
            'data_days':    fc_data_days,
        },
    }
    return JsonResponse(data)