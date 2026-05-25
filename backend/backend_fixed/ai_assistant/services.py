import json
import logging
import os
from time import perf_counter

import requests

from demo_orders.models import Order, OrderItem, Product, Recommendation

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Raised when the upstream AI service cannot return usable content."""


def success_response(data, message='推荐成功'):
    return {
        'success': True,
        'data': data,
        'message': message,
        'error_code': None,
    }


def error_response(error_code, message, intent='need_more_info'):
    return {
        'success': False,
        'data': {
            'intent': intent,
            'recommendations': [],
            'follow_up_question': message,
        },
        'message': message,
        'error_code': error_code,
    }


def product_to_menu_item(product):
    temps = [item.strip() for item in product.available_temps.split(',') if item.strip()]
    sugars = [item.strip() for item in product.available_sugars.split(',') if item.strip()]
    return {
        'product_id': product.id,
        'product_name': product.name,
        'category': product.category,
        'price': float(product.price),
        'description': product.description,
        'available_temps': temps,
        'available_sugars': sugars,
    }


def product_to_recommendation(product, reason, options=None):
    options = options or {}
    return {
        'product_id': product.id,
        'product_name': product.name,
        'reason': reason,
        'options': {
            'temperature': options.get('temperature', ''),
            'sugar': options.get('sugar', ''),
            'milk': options.get('milk', ''),
        },
    }


def get_available_products():
    return Product.objects.filter(is_available=True).order_by('id')


def get_fallback_products(member_id=None, limit=3):
    """Reuse the existing recommendation idea: member CF first, then popular products."""
    products = []

    if member_id:
        try:
            rec = Recommendation.objects.get(member_id=member_id)
            names = json.loads(rec.items_json)
            if isinstance(names, list) and names:
                products = list(
                    Product.objects.filter(name__in=names, is_available=True)
                )
        except (Recommendation.DoesNotExist, json.JSONDecodeError, TypeError):
            products = []

    if not products:
        from collections import Counter
        from django.db.models import Count

        orderitem_counts = (
            OrderItem.objects
            .filter(order__status='PICKED_UP', product__is_available=True)
            .values('product_id')
            .annotate(cnt=Count('id'))
            .order_by('-cnt')[:limit]
        )
        top_ids = [row['product_id'] for row in orderitem_counts if row['product_id']]
        if top_ids:
            product_map = Product.objects.in_bulk(top_ids)
            products = [product_map[pid] for pid in top_ids if pid in product_map]

        if not products:
            name_counter = Counter()
            historical_orders = Order.objects.filter(status='PICKED_UP').exclude(items_json__in=['', '[]'])
            for order in historical_orders:
                try:
                    for item in json.loads(order.items_json):
                        name = str(item.get('name', '')).strip()
                        if name:
                            name_counter[name] += item.get('quantity', 1)
                except (json.JSONDecodeError, TypeError, AttributeError):
                    continue
            top_names = [name for name, _ in name_counter.most_common(limit)]
            if top_names:
                products = list(Product.objects.filter(name__in=top_names, is_available=True)[:limit])

    if not products:
        products = list(Product.objects.filter(is_available=True, is_recommended=True).order_by('id')[:limit])

    if not products:
        products = list(Product.objects.filter(is_available=True).order_by('id')[:limit])

    return products[:limit]


def fallback_data(member_id=None, reason_code='AI_SERVICE_ERROR'):
    products = get_fallback_products(member_id=member_id)
    reason = '根据历史数据和当前商品销售热度综合推荐。'
    return {
        'intent': 'fallback_recommendation',
        'recommendations': [
            product_to_recommendation(product, reason)
            for product in products
        ],
        'follow_up_question': '',
        'is_fallback': True,
        'fallback_reason': reason_code,
    }


def build_order_prompt(user_input, menu_items):
    return (
        '你是 BeanButler 的咖啡点单助手。请根据用户需求，从给定菜单中推荐 1-3 个最合适的商品。\n'
        '你必须遵守：\n'
        '1. 只能推荐菜单中存在的商品。\n'
        '2. product_id 必须来自给定菜单，不能编造。\n'
        '3. 输出必须是合法 JSON，不要 Markdown，不要代码块，不要额外解释。\n'
        '4. 如果用户输入和咖啡、饮品、菜单、点单无关，intent 返回 out_of_scope，recommendations 返回空数组。\n'
        '5. options.temperature 尽量使用菜单 available_temps 里的值，例如 HOT、ICE、LESS_ICE、NO_ICE。\n'
        '6. options.sugar 尽量使用菜单 available_sugars 里的值，例如 NORMAL、MORE、LESS、NONE。\n'
        '7. milk 当前只是软建议字段，可返回 none、milk、oat_milk 或空字符串。\n\n'
        '输出 JSON 格式：\n'
        '{'
        '"intent":"recommend_drink|need_more_info|out_of_scope|menu_unavailable",'
        '"recommendations":[{"product_id":1,"product_name":"商品名","reason":"推荐理由","options":{"temperature":"ICE","sugar":"LESS","milk":"none"}}],'
        '"follow_up_question":""'
        '}\n\n'
        f'用户需求：{user_input}\n\n'
        f'可选菜单：{json.dumps(menu_items, ensure_ascii=False)}'
    )


def call_deepseek_order_assistant(user_input, menu_items):
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key:
        raise AIServiceError('AI_SERVICE_ERROR')

    base_url = os.getenv('DEEPSEEK_API_BASE_URL', 'https://api.deepseek.com').rstrip('/')
    model = os.getenv('DEEPSEEK_MODEL', 'deepseek-v4-flash')
    try:
        timeout = float(os.getenv('DEEPSEEK_TIMEOUT_SECONDS', '20'))
    except ValueError:
        timeout = 20

    payload = {
        'model': model,
        'messages': [
            {
                'role': 'system',
                'content': '你只返回合法 JSON。不要输出 Markdown、代码块或任何额外说明。',
            },
            {
                'role': 'user',
                'content': build_order_prompt(user_input, menu_items),
            },
        ],
        'temperature': 0.2,
        'response_format': {'type': 'json_object'},
    }

    started_at = perf_counter()
    try:
        response = requests.post(
            f'{base_url}/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        body = response.json()
        content = body['choices'][0]['message']['content']
        logger.info('DeepSeek order assistant succeeded in %.0f ms', (perf_counter() - started_at) * 1000)
        return content
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning('DeepSeek order assistant failed: %s', exc)
        raise AIServiceError('AI_SERVICE_ERROR') from exc


def parse_ai_json(raw_content):
    text = (raw_content or '').strip()
    if text.startswith('```'):
        text = text.strip('`').strip()
        if text.lower().startswith('json'):
            text = text[4:].strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIServiceError('AI_INVALID_JSON') from exc
    if not isinstance(parsed, dict):
        raise AIServiceError('AI_INVALID_JSON')
    return parsed


def validate_ai_recommendations(ai_data, available_products):
    product_map = {product.id: product for product in available_products}
    valid_recommendations = []

    for rec in ai_data.get('recommendations', []):
        if not isinstance(rec, dict):
            continue
        try:
            product_id = int(rec.get('product_id'))
        except (TypeError, ValueError):
            continue
        product = product_map.get(product_id)
        if not product:
            continue

        options = rec.get('options') if isinstance(rec.get('options'), dict) else {}
        valid_recommendations.append(product_to_recommendation(
            product,
            str(rec.get('reason') or '符合你的点单需求。'),
            options,
        ))

    return {
        'intent': ai_data.get('intent') or 'recommend_drink',
        'recommendations': valid_recommendations[:3],
        'follow_up_question': ai_data.get('follow_up_question') or '',
        'is_fallback': False,
    }
