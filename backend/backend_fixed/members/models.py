from django.db import models
from django.contrib.auth.models import User

class Member(models.Model):
    LEVEL_CHOICES = [
        ('GOLD', 'Gold'),
        ('SILVER', 'Silver'), 
        ('BRONZE', 'Bronze'),
    ]

    name       = models.CharField(max_length=50, verbose_name="Real Name")
    nickname   = models.CharField(max_length=50, blank=True, verbose_name="Nickname / Display Name")
    student_id = models.CharField(max_length=20, unique=True, verbose_name="Student ID")
    avatar = models.URLField(max_length=500, null=True, blank=True, verbose_name="头像URL") #新加的
    openid     = models.CharField(max_length=100, blank=True, unique=True, null=True, verbose_name="WeChat OpenID")
    phone = models.CharField(max_length=11, verbose_name="Contact Number")
    level = models.CharField(
        max_length=10, 
        choices=LEVEL_CHOICES, 
        default='BRONZE', 
        verbose_name="level"
    )
    points = models.IntegerField(default=0, verbose_name="Credit")
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="Created Time")

    LEVEL_THRESHOLDS = [
        (300, 'GOLD'),
        (100, 'SILVER'),
    ]
    def __str__(self):
        # 優先顯示暱稱，沒有暱稱就顯示真名
        display_name = self.nickname or self.name
        
        # 如果連真名都沒有（例如導入數據缺失），就顯示學號或 ID 保底
        if not display_name:
            display_name = f"Student_{self.student_id}" if self.student_id else f"Member_{self.id}"
            
        return display_name

    # models.py 中的 Member 類別

    def update_level(self):
    # 1. 定義等級權重，用來判斷「高低」
        level_weights = {
            'BRONZE': 1,
            'SILVER': 2,
            'GOLD': 3,
        }

        # 2. 根據當前 points 計算「理論上」應該處於的等級
        new_calculated_level = 'BRONZE'
        for threshold, level in self.LEVEL_THRESHOLDS:
            if self.points >= threshold:
                new_calculated_level = level
                break
    
        # 3. 獲取當前等級和新計算等級的權重
        current_weight = level_weights.get(self.level, 0)
        new_weight = level_weights.get(new_calculated_level, 0)

        # 4. 關鍵判斷：只有當「新算出來的等級」高於「現在的等級」時，才執行更新
        # 這解決了兩個問題：
        # - 消耗積分（買優惠券）時，new_weight 會小於 current_weight，不會降級
        # - 手動在後台改高後，只要積分沒達到更高標準，就不會被低等級覆蓋
        if new_weight > current_weight:
            self.level = new_calculated_level
            self.save(update_fields=['level'])
            return True
    
        return False