import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from members.models import Member

from .services import (
    AIServiceError,
    call_deepseek_order_assistant,
    error_response,
    fallback_data,
    get_available_products,
    parse_ai_json,
    product_to_menu_item,
    success_response,
    validate_ai_recommendations,
)

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(['POST'])
def order_assistant(request):
    """POST /api/ai/order-assistant/"""
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse(error_response(
            'INVALID_INPUT',
            '请求格式错误，请发送合法 JSON。',
            intent='need_more_info',
        ), status=400)

    user_input = str(payload.get('user_input') or '').strip()
    user_id = payload.get('user_id') or payload.get('member_id')

    if not user_id:
        return JsonResponse(error_response(
            'LOGIN_REQUIRED',
            '请先登录后再使用 AI 点单助手。',
            intent='login_required',
        ))

    try:
        member = Member.objects.get(id=user_id)
    except (Member.DoesNotExist, ValueError, TypeError):
        return JsonResponse(error_response(
            'LOGIN_REQUIRED',
            '请先登录后再使用 AI 点单助手。',
            intent='login_required',
        ))

    if not user_input:
        return JsonResponse(error_response(
            'INVALID_INPUT',
            '请告诉我你想喝什么，比如冰的、低糖、提神、不要牛奶或预算范围。',
            intent='need_more_info',
        ))

    products = list(get_available_products())
    if not products:
        return JsonResponse(error_response(
            'MENU_EMPTY',
            '当前暂无可推荐商品，请稍后再试。',
            intent='menu_unavailable',
        ))

    menu_items = [product_to_menu_item(product) for product in products]
    logger.info('AI order assistant request member=%s input=%s', member.id, user_input)

    try:
        raw_content = call_deepseek_order_assistant(user_input, menu_items)
        ai_data = parse_ai_json(raw_content)
        data = validate_ai_recommendations(ai_data, products)

        if data['intent'] == 'out_of_scope':
            logger.info('AI order assistant out_of_scope member=%s', member.id)
            return JsonResponse(error_response(
                'OUT_OF_SCOPE',
                '我主要负责咖啡和饮品点单，可以告诉我你的口味、温度、甜度或预算。',
                intent='out_of_scope',
            ))

        if not data['recommendations']:
            logger.warning('AI order assistant product mismatch member=%s raw=%s', member.id, raw_content)
            data = fallback_data(member_id=member.id, reason_code='AI_PRODUCT_MISMATCH')
            return JsonResponse(success_response(
                data,
                'AI 暂时没有生成稳定推荐，以下是根据历史数据和当前商品销售热度为你综合推荐的饮品。',
            ))

        logger.info(
            'AI order assistant success member=%s products=%s',
            member.id,
            [item['product_id'] for item in data['recommendations']],
        )
        return JsonResponse(success_response(data))

    except AIServiceError as exc:
        logger.warning('AI order assistant fallback member=%s error=%s', member.id, exc)
        reason_code = str(exc) if str(exc) in {'AI_INVALID_JSON', 'AI_SERVICE_ERROR'} else 'AI_SERVICE_ERROR'
        data = fallback_data(member_id=member.id, reason_code=reason_code)
        return JsonResponse(success_response(
            data,
            'AI 暂时没有生成稳定推荐，以下是根据历史数据和当前商品销售热度为你综合推荐的饮品。',
        ))
