"""
Management command: backfill_order_items

Converts items_json data from SQL-inserted historical orders into
proper OrderItem database rows. Safe to run multiple times (idempotent).

Usage:
    python manage.py backfill_order_items           # dry-run preview
    python manage.py backfill_order_items --write   # actually write to DB
"""
import json
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Backfill OrderItem rows from items_json for historical SQL-inserted orders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--write',
            action='store_true',
            default=False,
            help='Actually write to database (default is dry-run preview only)',
        )

    def handle(self, *args, **options):
        from demo_orders.models import Order, OrderItem, Product

        write_mode = options['write']
        mode_label = 'WRITE' if write_mode else 'DRY-RUN'
        self.stdout.write(f'[{mode_label}] Backfilling OrderItem from items_json...\n')

        # Only process orders that have no OrderItem rows yet
        orders_without_items = (
            Order.objects
            .prefetch_related('items')
            .exclude(items_json__in=['', '[]', None])
        )

        total_orders = 0
        total_items  = 0
        skipped      = 0
        errors       = 0

        for order in orders_without_items:
            # Skip if OrderItem rows already exist for this order
            if order.items.exists():
                skipped += 1
                continue

            try:
                items_data = json.loads(order.items_json)
            except (json.JSONDecodeError, TypeError):
                self.stdout.write(self.style.WARNING(
                    f'  Order {order.order_number}: malformed items_json — skipped'
                ))
                errors += 1
                continue

            if not items_data:
                continue

            total_orders += 1
            self.stdout.write(f'  Order {order.order_number} ({order.status}): {len(items_data)} items')

            for item_data in items_data:
                name  = item_data.get('name', '').strip()
                qty   = item_data.get('quantity', 1)
                price = item_data.get('price', 0)
                customization = item_data.get('customization', {})
                temp  = customization.get('temp', '')
                sugar = customization.get('sugar', '')

                # Try to match product by name
                product = None
                if name:
                    product = Product.objects.filter(name=name).first()

                self.stdout.write(
                    f'    -> "{name}" x{qty} | temp={temp or "-"} sugar={sugar or "-"} '
                    f'| product_id={product.id if product else "NOT FOUND"}'
                )

                if write_mode:
                    OrderItem.objects.create(
                        order          = order,
                        product        = product,
                        quantity       = qty,
                        price_at_order = price,
                        selected_temp  = temp,
                        selected_sugar = sugar,
                    )
                total_items += 1

        self.stdout.write('')
        if write_mode:
            self.stdout.write(self.style.SUCCESS(
                f'Done: {total_orders} orders backfilled, {total_items} OrderItem rows created. '
                f'({skipped} orders already had items, {errors} errors)'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f'DRY-RUN complete: would create {total_items} OrderItem rows across {total_orders} orders. '
                f'({skipped} orders already had items, {errors} errors)\n'
                f'Run with --write to actually apply changes.'
            ))
