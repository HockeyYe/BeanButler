import json
from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.urls import path, reverse
from django.template.response import TemplateResponse
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.utils import timezone
from .models import Order, OrderItem, Product, Material, Recommendation


# ─────────────────────────────────────────────
#  Timezone helper — handles both naive & aware datetimes
# ─────────────────────────────────────────────
def safe_localtime(dt):
    """Convert dt to local time safely, whether it is naive or aware."""
    if dt is None:
        return None
    if timezone.is_naive(dt):
        # Treat naive datetimes as UTC (Django default when USE_TZ=True)
        dt = timezone.make_aware(dt, timezone.utc)
    return timezone.localtime(dt)


# ─────────────────────────────────────────────
#  OrderItem Inline
# ─────────────────────────────────────────────
class OrderItemInline(admin.TabularInline):
    model  = OrderItem
    fields = ('product', 'selected_bean', 'selected_temp', 'selected_sugar', 'quantity', 'price_at_order')
    extra  = 1


# ─────────────────────────────────────────────
#  Batch Actions（3 個狀態，2 個 action）
# ─────────────────────────────────────────────
@admin.action(description='✅ 批量確認 → 已確認')
def mark_confirmed(modeladmin, request, queryset):
    updated = queryset.filter(status='PENDING').update(status='CONFIRMED')
    modeladmin.message_user(request, f'{updated} 筆訂單已確認')

@admin.action(description='☕ 批量開始製作 → 製作中')
def mark_in_progress(modeladmin, request, queryset):
    updated = queryset.filter(status='CONFIRMED').update(status='IN_PROGRESS')
    modeladmin.message_user(request, f'{updated} 筆訂單開始製作')

@admin.action(description='🔔 批量備好 → 待取餐')
def mark_ready(modeladmin, request, queryset):
    updated = queryset.filter(status='IN_PROGRESS').update(status='READY')
    modeladmin.message_user(request, f'{updated} 筆訂單已備好，等待取餐')

@admin.action(description='🏁 批量完成 → 已取餐')
def mark_picked_up(modeladmin, request, queryset):
    orders = queryset.filter(status='READY').select_related('member')
    updated = 0
    for order in orders:
        order.status = 'PICKED_UP'
        order.save(update_fields=['status'])
        # 取餐時才給積分
        if order.member:
            order.member.points += int(order.total_price)
            order.member.save(update_fields=['points'])
            order.member.update_level()
        updated += 1
    modeladmin.message_user(request, f'{updated} 筆訂單已取餐，積分已發放')


# ─────────────────────────────────────────────
#  OrderAdmin
# ─────────────────────────────────────────────
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ('order_number', 'pickup_code', 'colored_status', 'member', 'total_price', 'pickup_time', 'created_at')
    list_filter   = ('status', 'created_at')
    search_fields = ('order_number', 'pickup_code')
    ordering      = ('-created_at',)
    inlines       = [OrderItemInline]
    actions       = [mark_confirmed, mark_in_progress, mark_ready, mark_picked_up]

    # ── Bug 2 fix: auto-generate order_number & pickup_code when admin creates an order ──
    def save_model(self, request, obj, form, change):
        if not change:  # only on creation
            from datetime import date
            today_str = date.today().strftime('%Y%m%d')
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
            obj.order_number = f'{today_str}{seq:03d}'
            obj.pickup_code  = f'{seq:03d}'
        super().save_model(request, obj, form, change)

    # ── Bug 1 fix: sync items_json from OrderItem inlines after saving ──
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        order = form.instance
        items_data = []
        for item in order.items.select_related('product', 'selected_bean').all():
            if not item.product:
                continue
            customization = {}
            if item.selected_bean:  customization['bean']  = item.selected_bean.name
            if item.selected_temp:  customization['temp']  = item.selected_temp
            if item.selected_sugar: customization['sugar'] = item.selected_sugar
            custom_parts = []
            if item.selected_bean:  custom_parts.append(item.selected_bean.name)
            if item.selected_temp:  custom_parts.append(item.get_selected_temp_display())
            if item.selected_sugar: custom_parts.append(item.get_selected_sugar_display())
            items_data.append({
                'id':            str(item.product.id),
                'name':          item.product.name,
                'price':         float(item.price_at_order),
                'quantity':      item.quantity,
                'image':         '',
                'customization': customization,
                'customText':    ' / '.join(custom_parts),
            })
        order.items_json = json.dumps(items_data, ensure_ascii=False)
        order.save(update_fields=['items_json'])

    def colored_status(self, obj):
        palette = {
            'PENDING':     ('#F56C6C', '⏳ 待確認'),
            'CONFIRMED':   ('#409EFF', '✅ 已確認'),
            'IN_PROGRESS': ('#E6A23C', '☕ 製作中'),
            'READY':       ('#9C27B0', '🔔 待取餐'),
            'PICKED_UP':   ('#67C23A', '🏁 已取餐'),
        }
        color, label = palette.get(obj.status, ('#909399', obj.status))
        return format_html(
            '<span style="color:white;background:{};padding:4px 12px;'
            'border-radius:20px;font-size:12px;font-weight:600;">{}</span>',
            color, label
        )
    colored_status.short_description = '訂單狀態'
    colored_status.admin_order_field = 'status'

    def get_urls(self):
        urls   = super().get_urls()
        custom = [
            path('station/',         self.admin_site.admin_view(self.station_view),       name='order-station'),
            path('station/orders/',  self.admin_site.admin_view(self.orders_json_view),   name='order-station-orders'),
            path('station/update/',  self.admin_site.admin_view(self.update_order_view),  name='order-station-update'),
            path('station/stats/',    self.admin_site.admin_view(self.stats_view),          name='order-station-stats'),
        ]
        return custom + urls

    def station_view(self, request):
        context = dict(self.admin_site.each_context(request))
        return TemplateResponse(request, 'admin/orderstation.html', context)

    def orders_json_view(self, request):
        orders_qs = (
            Order.objects
            .exclude(status='PICKED_UP')
            .prefetch_related('items__product', 'items__selected_bean')
            .select_related('member')
            .order_by('created_at')
        )
        data = []
        for order in orders_qs:
            item_lines = []
            for item in order.items.all():
                if not item.product:
                    continue  # product 為 null，由下方 items_json fallback 處理
                desc   = item.product.name
                extras = []
                if item.selected_bean:  extras.append(item.selected_bean.name)
                if item.selected_temp:  extras.append(item.get_selected_temp_display())
                if item.selected_sugar: extras.append(item.get_selected_sugar_display())
                if extras: desc += f" ({' / '.join(extras)})"
                item_lines.append(f"{item.quantity}× {desc}")

            if not item_lines and order.items_json:
                try:
                    for i in json.loads(order.items_json):
                        line = f"{i.get('quantity',1)}× {i.get('name','')}"
                        note = i.get('customText', '')
                        if note: line += f" ({note})"
                        item_lines.append(line)
                except Exception:
                    pass

            data.append({
                'id':             order.id,
                'order_number':   order.order_number,
                'pickup_code':    order.pickup_code or order.order_number,
                'status':         order.status,
                'status_display': order.get_status_display(),
                'created_at':     safe_localtime(order.created_at).strftime('%H:%M:%S'),
                'pickup_time':    order.pickup_time,
                'member':         str(order.member) if order.member else 'Guest',
                'total_price':    str(order.total_price),
                'items':          item_lines,
            })
        return JsonResponse({'orders': data})

    def update_order_view(self, request):
        if request.method != 'POST':
            return JsonResponse({'error': 'POST only'}, status=405)
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        order_id   = body.get('order_id')
        new_status = body.get('status')
        valid = {'CONFIRMED', 'IN_PROGRESS', 'READY', 'PICKED_UP'}
        if new_status not in valid:
            return JsonResponse({'error': f'Invalid status: {new_status}'}, status=400)
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)

        prev_status = order.status
        order.status = new_status
        order.save(update_fields=['status'])

        # ── 取餐時才給積分 ──────────────────────────────────────
        if new_status == 'PICKED_UP' and prev_status != 'PICKED_UP' and order.member:
            earned = int(order.total_price)
            order.member.points += earned
            order.member.save(update_fields=['points'])
            order.member.update_level()

        return JsonResponse({'success': True, 'id': order.id, 'new_status': new_status})

    # GET /admin/demo_orders/order/station/stats/
    def stats_view(self, request):
        from django.db.models import Sum
        today = safe_localtime(timezone.now()).date()
        result = (
            Order.objects
            .filter(status="PICKED_UP", created_at__date=today)
            .aggregate(revenue=Sum("total_price"), count=Sum("total_price") - Sum("total_price") + 0)
        )
        revenue = float(result["revenue"] or 0)
        done_count = Order.objects.filter(status="PICKED_UP", created_at__date=today).count()
        return JsonResponse({"revenue": revenue, "done_today": done_count})


# ─────────────────────────────────────────────
#  ProductAdmin
# ─────────────────────────────────────────────
class ProductForm(forms.ModelForm):
    temp_choices = forms.MultipleChoiceField(
        choices=Product.TEMP_OPTIONS, widget=forms.CheckboxSelectMultiple,
        required=False, label='Temperature & Ice Customization')
    sugar_choices = forms.MultipleChoiceField(
        choices=Product.SUGAR_OPTIONS, widget=forms.CheckboxSelectMultiple,
        required=False, label='Sweetness Level Configuration')

    class Meta:
        model   = Product
        exclude = ['available_temps', 'available_sugars']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.available_temps:
                self.initial['temp_choices']  = self.instance.available_temps.split(',')
            if self.instance.available_sugars:
                self.initial['sugar_choices'] = self.instance.available_sugars.split(',')

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.available_temps  = ','.join(self.cleaned_data.get('temp_choices', []))
        instance.available_sugars = ','.join(self.cleaned_data.get('sugar_choices', []))
        if commit:
            instance.save()
        return instance


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display      = ('name', 'category', 'price', 'is_available')
    list_editable     = ('is_available',)
    filter_horizontal = ('linked_beans',)
    fieldsets = (
        ('Basic Specifications',    {'fields': ('name', 'category', 'price', 'description', 'image', 'is_available')}),
        ('Coffee Bean Association', {'fields': ('allow_bean_selection', 'linked_beans')}),
        ('Product Customization',   {'fields': ('temp_choices', 'sugar_choices')}),
    )

    def get_form(self, request, obj=None, **kwargs):
        kwargs['form'] = ProductForm
        return super().get_form(request, obj, **kwargs)

    def get_changelist_form(self, request, **kwargs):
        from django.forms import modelform_factory
        return modelform_factory(Product, fields=['is_available'])


# ─────────────────────────────────────────────
#  RecommendationAdmin — shows results + Run Now button
# ─────────────────────────────────────────────
@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display         = ('member', 'items_preview', 'generated_at')
    readonly_fields      = ('member', 'items_json', 'generated_at')
    ordering             = ('member__name',)
    search_fields        = ('member__name',)
    change_list_template = 'admin/demo_orders/recommendation/change_list.html'

    def items_preview(self, obj):
        try:
            names = json.loads(obj.items_json)
            return ' · '.join(names[:3])
        except Exception:
            return obj.items_json
    items_preview.short_description = 'Top 3 Recommendations'

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                'run-now/',
                self.admin_site.admin_view(self.run_recommender_view),
                name='recommendation-run-now',
            ),
        ]
        return custom + urls

    def run_recommender_view(self, request):
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        try:
            call_command('run_cf_recommender', trigger='manual', stdout=out)
            msg = out.getvalue().strip() or 'Done.'
            self.message_user(request, f'✅ {msg}', messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f'❌ Error: {e}', messages.ERROR)
        return HttpResponseRedirect(
            reverse('admin:demo_orders_recommendation_changelist')
        )


# ─────────────────────────────────────────────
#  RecommenderRunLogAdmin — execution history
# ─────────────────────────────────────────────
from .models import RecommenderRunLog

@admin.register(RecommenderRunLog)
class RecommenderRunLogAdmin(admin.ModelAdmin):
    list_display   = ('ran_at', 'trigger_badge', 'members_updated', 'members_created', 'duration_secs', 'note')
    list_filter    = ('triggered_by',)
    readonly_fields = ('ran_at', 'triggered_by', 'members_updated', 'members_created', 'duration_secs', 'note')
    ordering       = ('-ran_at',)

    def trigger_badge(self, obj):
        if obj.triggered_by == 'manual':
            return format_html(
                '<span style="background:#409EFF;color:#fff;padding:2px 10px;'
                'border-radius:12px;font-size:11px;font-weight:600;">👆 Manual</span>'
            )
        return format_html(
            '<span style="background:#67C23A;color:#fff;padding:2px 10px;'
            'border-radius:12px;font-size:11px;font-weight:600;">⏰ Scheduled</span>'
        )
    trigger_badge.short_description = 'Trigger'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ─────────────────────────────────────────────
#  MaterialAdmin
# ─────────────────────────────────────────────
@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display   = ('name', 'category', 'quantity', 'price', 'expiry_date')
    list_filter    = ('category', 'roast_level')
    search_fields  = ('name',)
    fieldsets = (
        ('Inventory Information',          {'fields': ('category', 'name', 'quantity', 'price')}),
        ('Coffee Bean Attributes',         {'fields': ('roast_level',)}),
        ('Dairy & Perishables Attributes', {'fields': ('expiry_date',)}),
    )
