from django.db import models
from django.utils import timezone

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('ESPRESSO',     'Espresso-Based'),
        ('POUROVER',     'Filter / Hand-Brewed'),
        ('NON-CAFFEINE', 'Non-Caffeinated'),
        ('SPECIAL',      'Signature Specials'),
    ]
    TEMP_OPTIONS = (
        ('HOT',      'Hot'),
        ('ICE',      'Standard Ice'),
        ('LESS_ICE', 'Less Ice'),
        ('NO_ICE',   'No Ice'),
    )
    SUGAR_OPTIONS = (
        ('NORMAL', 'Standard Sweetness'),
        ('MORE',   'Extra Sweetness'),
        ('LESS',   'Reduced Sweetness'),
        ('NONE',   'No Added Sugar'),
    )

    name              = models.CharField(max_length=100, verbose_name='Product Name')
    category          = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='ESPRESSO', verbose_name='Category')
    price             = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Base Price')
    description       = models.TextField(blank=True, verbose_name='Description')
    image             = models.ImageField(upload_to='products/', null=True, blank=True, verbose_name='Product Image')
    is_available      = models.BooleanField(default=True, verbose_name='Availability')
    is_recommended    = models.BooleanField(default=False, verbose_name='Show in Recommended')
    allow_bean_selection = models.BooleanField(default=False, verbose_name='Enable Bean Selection')
    linked_beans      = models.ManyToManyField(
        'Material',
        limit_choices_to={'category': 'BEAN'},
        blank=True,
        verbose_name='Available Coffee Beans',
    )
    available_temps   = models.CharField(max_length=200, blank=True, verbose_name='Temperature/Ice Options')
    available_sugars  = models.CharField(max_length=200, blank=True, verbose_name='Sweetness Level Options')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name        = 'Product Catalog'
        verbose_name_plural = 'Product Catalog'


class Material(models.Model):
    CATEGORY_CHOICES = [
        ('BEAN',     'Coffee Bean'),
        ('DAIRY',    'Dairy Products'),
        ('FOOD',     'Food Ingredients'),
        ('NON_FOOD', 'Non-Food Assets'),
    ]
    ROAST_CHOICES = [
        ('DARK',   'Dark Roast'),
        ('MEDIUM', 'Medium Roast'),
        ('LIGHT',  'Light Roast'),
    ]

    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='Material Category')
    name        = models.CharField(max_length=100, verbose_name='Material Name')
    price       = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Unit Price')
    quantity    = models.PositiveIntegerField(verbose_name='Stock Quantity')
    roast_level = models.CharField(max_length=10, choices=ROAST_CHOICES, blank=True, null=True, verbose_name='Roast Profile')
    expiry_date = models.DateField(blank=True, null=True, verbose_name='Expiry Date')

    class Meta:
        verbose_name        = 'Inventory Assets'
        verbose_name_plural = 'Inventory Assets'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.roast_level and self.category != 'BEAN':
            raise ValidationError({
                'roast_level': (
                    f'Roast level can only be set for Coffee Bean (BEAN) materials. '
                    f'This item is categorised as "{self.get_category_display()}".'
                )
            })

    def __str__(self):
        return f'[{self.get_category_display()}] {self.name}'


class Order(models.Model):
    # ── 3 個狀態 ──────────────────────────────────────────────
    STATUS_CHOICES = [
        ('PENDING',     '待確認'),    # 顧客下單，等待店員確認
        ('CONFIRMED',   '已確認'),    # 店員確認接單
        ('IN_PROGRESS', '製作中'),    # 店員開始製作
        ('READY',       '待取餐'),    # 製作完成，等待取餐
        ('PICKED_UP',   '已取餐'),    # 顧客取走
    ]

    order_number = models.CharField(max_length=20, unique=True, verbose_name='Order No.')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='Order Status')
    created_at   = models.DateTimeField(auto_now_add=True, verbose_name='Order Timestamp')
    member       = models.ForeignKey(
        'members.Member', null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Member'
    )
    total_price  = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name='Total Amount')
    pickup_time  = models.CharField(max_length=50, default='立即取餐')
    pickup_code  = models.CharField(max_length=10, blank=True)
    items_json   = models.TextField(blank=True, default='[]')

    class Meta:
        verbose_name        = 'Order Records'
        verbose_name_plural = 'Order Records'

    def __str__(self):
        return f'Order {self.order_number}'


class RecommenderRunLog(models.Model):
    """Records every execution of the CF recommender for audit/history."""
    TRIGGER_CHOICES = [
        ('manual',    'Manual (Admin Button)'),
        ('scheduled', 'Scheduled (Cron)'),
    ]
    ran_at          = models.DateTimeField(auto_now_add=True, verbose_name='Run Time')
    triggered_by    = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default='manual', verbose_name='Trigger')
    members_updated = models.PositiveIntegerField(default=0, verbose_name='Members Updated')
    members_created = models.PositiveIntegerField(default=0, verbose_name='New Entries Created')
    duration_secs   = models.FloatField(default=0.0, verbose_name='Duration (s)')
    note            = models.TextField(blank=True, verbose_name='Notes / Errors')

    class Meta:
        verbose_name        = 'Recommender Run Log'
        verbose_name_plural = 'Recommender Run Logs'
        ordering            = ['-ran_at']

    def __str__(self):
        return f'{self.ran_at.strftime("%Y-%m-%d %H:%M")} — {self.members_updated + self.members_created} members'


class Recommendation(models.Model):
    """Stores the latest CF recommendation for each member."""
    member       = models.OneToOneField(
        'members.Member', on_delete=models.CASCADE,
        related_name='recommendation', verbose_name='Member'
    )
    items_json   = models.TextField(default='[]', verbose_name='Recommended Product Names (JSON)')
    generated_at = models.DateTimeField(auto_now=True, verbose_name='Last Generated')

    class Meta:
        verbose_name        = 'AI Recommendation'
        verbose_name_plural = 'AI Recommendations'

    def __str__(self):
        return f'Recs for {self.member}'


class OrderItem(models.Model):
    order         = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name='Order Reference')
    product       = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Product Name')
    selected_bean = models.ForeignKey(
        'Material', on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={'category': 'BEAN'}, verbose_name='Selected Bean'
    )
    selected_temp   = models.CharField(max_length=50, choices=Product.TEMP_OPTIONS, blank=True, verbose_name='Selected Temp/Ice')
    selected_sugar  = models.CharField(max_length=50, choices=Product.SUGAR_OPTIONS, blank=True, verbose_name='Selected Sweetness')
    quantity        = models.PositiveIntegerField(default=1, verbose_name='Quantity')
    price_at_order  = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='Transaction Price')

    def __str__(self):
        name = self.product.name if self.product else '(deleted product)'
        extras = []
        if self.selected_temp:  extras.append(self.get_selected_temp_display())
        if self.selected_sugar: extras.append(self.get_selected_sugar_display())
        suffix = f' ({" / ".join(extras)})' if extras else ''
        return f'{name} ×{self.quantity}{suffix}'

    class Meta:
        verbose_name        = 'Line Item Detail'
        verbose_name_plural = 'Line Item Details'
