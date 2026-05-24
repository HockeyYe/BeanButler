# feedback/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import Feedback
from members.models import Member


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def feedback_list(request):
    """
    GET  /api/feedback/?member_id=123  → 取得該會員的所有留言
    POST /api/feedback/               → 新增留言
        body: { member_id, message }
    """
    if request.method == 'GET':
        member_id = request.GET.get('member_id')
        if not member_id:
            return JsonResponse({'success': False, 'error': 'member_id is required'}, status=400)

        feedbacks = Feedback.objects.filter(member_id=member_id)
        data = []
        for fb in feedbacks:
            data.append({
                'id': fb.id,
                'content': fb.user_message,
                'time': fb.created_at.strftime('%Y-%m-%d %H:%M'),
                'reply': fb.admin_reply or '',
                'is_replied': fb.is_replied,
            })
        return JsonResponse({'success': True, 'messages': data})

    # POST：新增留言
    body = json.loads(request.body)
    member_id = body.get('member_id')
    message = body.get('message', '').strip()

    if not member_id or not message:
        return JsonResponse({'success': False, 'error': 'member_id and message are required'}, status=400)

    try:
        member = Member.objects.get(id=member_id)
    except Member.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Member not found'}, status=404)

    fb = Feedback.objects.create(member=member, user_message=message)

    return JsonResponse({
        'success': True,
        'id': fb.id,
        'content': fb.user_message,
        'time': fb.created_at.strftime('%Y-%m-%d %H:%M'),
        'reply': '',
        'is_replied': False,
    }, status=201)
