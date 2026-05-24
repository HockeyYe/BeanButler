from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import Member
import requests
import os
from django.core.files.storage import default_storage
from django.conf import settings

WECHAT_APP_ID = os.getenv("WECHAT_APP_ID", "wx03a06f3eecbf5aab")
WECHAT_APP_SECRET = os.getenv("WECHAT_APP_SECRET", "082073d38a1d1ef0adb52e1db93ea697")

@csrf_exempt
@require_http_methods(["POST"])
def upload_avatar(request):
    """接收小程序上传的头像实体文件"""
    member_id = request.POST.get("member_id")
    avatar_file = request.FILES.get("avatar")

    if not member_id or not avatar_file:
        return JsonResponse({"success": False, "error": "缺少会员ID或图片文件"}, status=400)

    try:
        member = Member.objects.get(id=member_id)

        ext = avatar_file.name.split(".")[-1]
        filename = f"avatar_user_{member_id}.{ext}"

        file_path = f"avatars/{filename}"
        if default_storage.exists(file_path):
            default_storage.delete(file_path)
        saved_path = default_storage.save(file_path, avatar_file)

        final_url = f"{settings.MEDIA_URL}{saved_path}"

        member.avatar = final_url
        member.save()

        return JsonResponse({
            "success": True,
            "message": "头像上传成功",
            "avatar_url": final_url
        })
    except Member.DoesNotExist:
        return JsonResponse({"success": False, "error": "会员不存在"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def wechat_login(request):
    """微信登录 - 强制要求新用户完善资料"""
    try:
        data = json.loads(request.body)
        avatar_url = data.get("avatarUrl", "")
        code = data.get("code", "")
        nick_name = data.get("nickName", "微信用户")

        if not code:
            return JsonResponse({"success": False, "error": "缺少微信 code"}, status=400)

        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": WECHAT_APP_ID,
            "secret": WECHAT_APP_SECRET,
            "js_code": code,
            "grant_type": "authorization_code"
        }

        response = requests.get(url, params=params)
        wx_data = response.json()
        openid = wx_data.get("openid")

        if not openid:
            return JsonResponse({"success": False, "error": f"微信登录失败: {wx_data.get('errmsg')}"}, status=400)

        temp_student_id = f"TMP_{openid[:6]}"

        member, created = Member.objects.get_or_create(
            openid=openid,
            defaults={
                "nickname": nick_name,
                "name": "",
                "avatar": avatar_url,
                "phone": "",
                "student_id": "",
                "points": 0
            }
        )

        updated = False
        if nick_name and nick_name != "微信用户" and member.nickname != nick_name:
            member.nickname = nick_name
            updated = True

        if avatar_url and member.avatar != avatar_url:
            member.avatar = avatar_url
            updated = True

        if updated:
            member.save()

        needs_profile = not (member.name and member.phone and not member.student_id.startswith("TMP_"))

        return JsonResponse({
            "success": True,
            "member_id": member.id,
            "name": member.name,
            "nickname": member.nickname,
            "student_id": member.student_id,
            "avatar_url": member.avatar,
            "phone": member.phone,
            "points": member.points,
            "level": member.level,
            "is_new": created,
            "needs_profile": needs_profile,
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@require_http_methods(["GET"])
def member_info(request):
    """查询会员资料"""
    member_id = request.GET.get("member_id")
    try:
        member = Member.objects.get(id=member_id)
        return JsonResponse({
            "success": True,
            "name": member.name,
            "nickname": member.nickname,
            "student_id": member.student_id,
            "avatar_url": member.avatar,
            "phone": member.phone,
            "points": member.points,
            "level": member.level,
        })
    except Member.DoesNotExist:
        return JsonResponse({"success": False, "error": "Member not found"}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def update_member_profile(request):
    """更新个人资料（登录后或「我的」页面使用）"""
    try:
        data = json.loads(request.body)
        member_id = data.get("member_id")
        name = data.get("name")
        student_id = data.get("student_id")
        phone = data.get("phone")

        member = Member.objects.get(id=member_id)

        if name:
            member.name = name.strip()
        if student_id:
            if Member.objects.filter(student_id=student_id).exclude(id=member_id).exists():
                return JsonResponse({"success": False, "error": "该学号已被使用"}, status=400)
            member.student_id = student_id.strip()
        if phone:
            member.phone = phone.strip()

        member.save()
        member.update_level()

        return JsonResponse({
            "success": True,
            "message": "个人资料更新成功",
            "name": member.name,
            "nickname": member.nickname,
            "student_id": member.student_id,
            "avatar_url": member.avatar,
            "phone": member.phone,
            "level": member.level,
        })
    except Member.DoesNotExist:
        return JsonResponse({"success": False, "error": "会员不存在"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
