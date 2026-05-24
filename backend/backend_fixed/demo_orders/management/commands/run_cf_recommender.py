"""
Management command: run_cf_recommender
Usage:
    python manage.py run_cf_recommender              # manual trigger
    python manage.py run_cf_recommender --trigger scheduled  # cron trigger
"""
import json
import time
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Train Item-based CF model and refresh recommendations for all members'

    def add_arguments(self, parser):
        parser.add_argument(
            '--trigger',
            type=str,
            default='manual',
            choices=['manual', 'scheduled'],
            help='How this run was triggered (manual or scheduled)',
        )

    def handle(self, *args, **options):
        from demo_orders.models import Order, Recommendation, RecommenderRunLog
        from members.models import Member

        trigger    = options['trigger']
        start_time = time.time()
        self.stdout.write(f'Starting CF recommender (trigger={trigger})...')

        # ── 1. Build purchase records ────────────────────────────────
        # Primary: OrderItem rows (new API orders)
        # Fallback: items_json field (historical SQL-inserted orders)
        order_qs = (
            Order.objects
            .filter(status='PICKED_UP')
            .prefetch_related('items__product')
            .select_related('member')
        )

        records = []
        for order in order_qs:
            if not order.member:
                continue

            item_rows = list(order.items.all())

            if item_rows:
                # Normal path: OrderItem records exist
                for item in item_rows:
                    if item.product:
                        records.append({
                            'member_id':    order.member_id,
                            'product_name': item.product.name,
                            'purchased':    1,
                        })
            else:
                # Fallback: parse items_json for SQL-inserted historical orders
                if order.items_json and order.items_json.strip() not in ('', '[]'):
                    try:
                        items_data = json.loads(order.items_json)
                        for item_data in items_data:
                            name = item_data.get('name', '').strip()
                            if name:
                                records.append({
                                    'member_id':    order.member_id,
                                    'product_name': name,
                                    'purchased':    1,
                                })
                    except (json.JSONDecodeError, TypeError):
                        pass

        if not records:
            msg = 'No purchase records found (neither OrderItem rows nor items_json). Aborting.'
            self.stdout.write(self.style.WARNING(f'WARNING: {msg}'))
            RecommenderRunLog.objects.create(
                triggered_by=trigger, members_updated=0,
                members_created=0,
                duration_secs=round(time.time() - start_time, 2),
                note=msg,
            )
            return

        self.stdout.write(f'   Raw purchase records: {len(records)}')

        # ── 2. Pivot matrix ──────────────────────────────────────────
        import pandas as pd
        from sklearn.metrics.pairwise import cosine_similarity

        df = pd.DataFrame(records)
        matrix = (
            df.pivot_table(
                index='product_name',
                columns='member_id',
                values='purchased',
                aggfunc='sum',
            )
            .fillna(0)
            .clip(upper=1)
        )

        self.stdout.write(f'   Matrix shape: {matrix.shape[0]} products x {matrix.shape[1]} members')

        # ── 3. Item similarity + popularity ─────────────────────────
        sim_df = pd.DataFrame(
            cosine_similarity(matrix),
            index=matrix.index, columns=matrix.index
        )
        pop = matrix.sum(axis=1)
        pop_score = (
            (pop - pop.min()) / (pop.max() - pop.min())
            if pop.max() != pop.min()
            else pop / pop.max()
        )

        from demo_orders.models import Product
        available_names = set(
            Product.objects.filter(is_available=True).values_list('name', flat=True)
        )

        global_top3 = (
            pop_score[pop_score.index.isin(available_names)]
            .sort_values(ascending=False)
            .head(3)
            .index.tolist()
        )

        # ── 4. Recommender (alpha=0.4) ────────────────────────────────
        ALPHA, TOP_N = 0.4, 3

        def recommend(member_id):
            if member_id not in matrix.columns:
                return global_top3[:TOP_N]

            user_vec = matrix[member_id]
            bought   = user_vec[user_vec > 0].index.tolist()

            cf_scores = sim_df.dot(user_vec)
            if cf_scores.max() > 0:
                cf_scores = cf_scores / cf_scores.max()

            final = ALPHA * cf_scores + (1 - ALPHA) * pop_score
            final_available = final[final.index.isin(available_names)]

            recs = (
                final_available
                .drop(labels=bought, errors='ignore')
                .sort_values(ascending=False)
                .head(TOP_N)
                .index.tolist()
            )
            for g in global_top3:
                if len(recs) >= TOP_N:
                    break
                if g not in recs and g not in bought:
                    recs.append(g)
            return recs

        # ── 5. Write results for ALL members ─────────────────────────
        members = Member.objects.all()
        created = updated = 0

        for member in members:
            _, is_new = Recommendation.objects.update_or_create(
                member=member,
                defaults={
                    'items_json':   json.dumps(recommend(member.id), ensure_ascii=False),
                    'generated_at': timezone.now(),
                },
            )
            if is_new: created += 1
            else:      updated += 1

        duration = round(time.time() - start_time, 2)

        RecommenderRunLog.objects.create(
            triggered_by    = trigger,
            members_updated = updated,
            members_created = created,
            duration_secs   = duration,
            note            = (
                f'Matrix: {matrix.shape[0]} products x {matrix.shape[1]} members. '
                f'Available products for recs: {len(available_names)}. alpha=0.4'
            ),
        )

        self.stdout.write(self.style.SUCCESS(
            f'Done -- {created} created, {updated} updated in {duration}s. '
            f'Total: {created + updated} members.'
        ))
