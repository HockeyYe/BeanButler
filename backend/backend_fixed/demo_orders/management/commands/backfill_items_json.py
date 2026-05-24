"""
Management command: backfill_items_json

Reads existing OrderItem rows and writes them back into Order.items_json
for orders where items_json is currently empty ( [] or '' ).

Safe to run multiple times — only touches orders where items_json is blank.

Usage:
    python manage.py backfill_items_json           # dry-run preview
    python manage.py backfill_items_json --write   # actually update DB
"""
import json
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Backfill Order.items_json from existing OrderItem rows'

    def add_arguments(self, parser):
        parser.add_argument(
            '--write',
            action='store_true',
            default=False,
            help='Actually write to database (default is dry-run preview only)',
        )

    def handle(self, *args, **options):
        from demo_orders.models import Order

        write_mode = options['write']
        mode_label = 'WRITE' if write_mode else 'DRY-RUN'
        self.stdout.write(f'[{mode_label}] Backfilling items_json from OrderItem records...\n')

        # Only target orders where items_json is empty but OrderItem rows exist
        target_orders = (
            Order.objects
            .filter(items_json__in=['', '[]'])
            .prefetch_related('items__product', 'items__selected_bean')
        )

        total_orders = 0
        total_items  = 0
        skipped      = 0

        for order in target_orders:
            order_items = order.items.all()

            if not order_items.exists():
                skipped += 1
                continue

            # Build items_json structure from OrderItem rows
            items_data = []
            for oi in order_items:
                item_dict = {
                    'id':       oi.product.id if oi.product else None,
                    'name':     oi.product.name if oi.product else '已刪除商品',
                    'quantity': oi.quantity,
                    'price':    float(oi.price_at_order),
                    'customization': {
                        'temp':  oi.selected_temp  or '',
                        'sugar': oi.selected_sugar or '',
                        'bean':  oi.selected_bean.name if oi.selected_bean else '',
                    }
                }
                items_data.append(item_dict)

            json_str = json.dumps(items_data, ensure_ascii=False)

            self.stdout.write(
                f'  Order {order.order_number}: {len(items_data)} item(s) → {json_str[:80]}...'
                if len(json_str) > 80 else
                f'  Order {order.order_number}: {len(items_data)} item(s) → {json_str}'
            )

            if write_mode:
                order.items_json = json_str
                order.save(update_fields=['items_json'])

            total_orders += 1
            total_items  += len(items_data)

        self.stdout.write('')
        if write_mode:
            self.stdout.write(self.style.SUCCESS(
                f'Done: updated {total_orders} orders, '
                f'{total_items} items written into items_json. '
                f'({skipped} orders had no OrderItem rows — skipped)'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'DRY-RUN: would update {total_orders} orders '
                f'({total_items} items total). '
                f'{skipped} orders have no OrderItem rows.\n'
                f'Run with --write to actually apply.'
            ))
