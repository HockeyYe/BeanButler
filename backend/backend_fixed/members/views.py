from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import Member
import requests
import os
from django.core.files.storage import default_storage
from django.conf import settings
# 你的微信小程序配置（建议写在 settings.py 里，这里为了直观先写出来）
WECHAT_APP_ID = 'wx03a06f3eecbf5aab'
WECHAT_APP_SECRET = '082073d38a1d1ef0adb52e1db93ea697'

@csrf_exempt
@require_http_methods(['POST'])
def upload_avatar(request):
    """接收小程式上傳的頭像實體文件"""
    member_id = request.POST.get('member_id')
    avatar_file = request.FILES.get('avatar') # 獲取二進制圖片文件

    if not member_id or not avatar_file:
        return JsonResponse({'success': False, 'error': '缺少會員ID或圖片文件'}, status=400)

    try:
        member = Member.objects.get(id=member_id)
        
        # 為了防止檔名衝突，我們用 member_id 重新命名圖片
        ext = avatar_file.name.split('.')[-1] # 獲取副檔名 (jpg, png)
        filename = f"avatar_user_{member_id}.{ext}"
        
        # 覆蓋或保存到 media/avatars/ 目錄下
        file_path = f"avatars/{filename}"
        if default_storage.exists(file_path):
            default_storage.delete(file_path) # 刪除舊頭像
            
        saved_path = default_storage.save(file_path, avatar_file)
        
        # 生成相對路徑，例如 /media/avatars/avatar_user_4.jpg
        # 確保 settings.MEDIA_URL 是 '/media/'
        final_url = f"{settings.MEDIA_URL}{saved_path}"
        
        # 存入資料庫
        member.avatar = final_url
        member.save()

        return JsonResponse({
            'success': True, 
            'message': '頭像上傳成功',
            'avatar_url': final_url
        })
    except Member.DoesNotExist:
        return JsonResponse({'success': False, 'error': '會員不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def wechat_login(request):
    """微信登入 - 強制要求新用戶完善資料"""
    try:
        data = json.loads(request.body)
        avatar_url = data.get('avatarUrl', '') 
        code = data.get('code', '')
        nick_name = data.get('nickName', '微信用戶')
        
        if not code:
            return JsonResponse({'success': False, 'error': '缺少微信 code'}, status=400)

        # 向微信服务器发送请求，用 code 换取 openid
        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            'appid': WECHAT_APP_ID,
            'secret': WECHAT_APP_SECRET,
            'js_code': code,
            'grant_type': 'authorization_code'
        }
        
        response = requests.get(url, params=params)
        wx_data = response.json()
        openid = wx_data.get('openid')
        
        if not openid:
            return JsonResponse({'success': False, 'error': f'微信登录失败: {wx_data.get("errmsg")}'}, status=400)

        temp_student_id = f'TMP_{openid[:6]}'
        
        member, created = Member.objects.get_or_create(
            openid=openid,  
            defaults={
                'nickname': nick_name,
                'name': '',
                'avatar': avatar_url,
                'phone': '',
                'student_id': '',
                'points': 0
            }
        )

        # ✅ 【核心新增】：强制更新昵称和头像
        # 如果前端传来的不是占位符，就覆写进数据库
        updated = False
        if nick_name and nick_name != '微信用戶' and member.nickname != nick_name:
            member.nickname = nick_name
            updated = True
            
        if avatar_url and member.avatar != avatar_url:
            member.avatar = avatar_url
            updated = True
            
        if updated:
            member.save()

        # 判斷是否需要完善資料
        needs_profile = not (member.name and member.phone and not member.student_id.startswith('TMP_'))
    
        return JsonResponse({
            'success': True,
            'member_id': member.id,
            'name': member.name, 
            'nickname': member.nickname,# 返回昵称供前端展示
            'student_id': member.student_id,
            'avatar_url': member.avatar,
            'phone': member.phone,
            'points': member.points,
            'level': member.level,
            'is_new': created,
            'needs_profile': needs_profile,      
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(['GET'])
def member_info(request):
    """查詢會員資料"""
    member_id = request.GET.get('member_id')
    try:
        member = Member.objects.get(id=member_id)
        return JsonResponse({
            'success': True,
            'name': member.name,
            'nickname':member.nickname,
            'student_id': member.student_id,
            'avatar_url': member.avatar,
            'phone': member.phone,
            'points': member.points,
            'level': member.level,
        })
    except Member.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Member not found'}, status=404)


@csrf_exempt
@require_http_methods(['POST'])
def update_member_profile(request):
    """更新個人資料（登入後或「我的」頁面使用）"""
    try:
        data = json.loads(request.body)
        member_id = data.get('member_id')
        name = data.get('name')
        student_id = data.get('student_id')
        phone = data.get('phone')

        member = Member.objects.get(id=member_id)

        if name:
            member.name = name.strip()
        if student_id:
            # 防止學號重複
            if Member.objects.filter(student_id=student_id).exclude(id=member_id).exists():
                return JsonResponse({'success': False, 'error': '該學號已被使用'}, status=400)
            member.student_id = student_id.strip()
        if phone:
            member.phone = phone.strip()

        member.save()
        member.update_level()   # 更新會員等級

        return JsonResponse({
            'success': True,
            'message': '個人資料更新成功',
            'name': member.name,
            'nickname': member.nickname,
            'student_id': member.student_id,
            'avatar_url': member.avatar,
            'phone': member.phone,
            'level': member.level,
        })
    except Member.DoesNotExist:
        return JsonResponse({'success': False, 'error': '會員不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)