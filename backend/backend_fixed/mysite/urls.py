"""
URL configuration for mysite project.
"""
from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

# ===== 匯入所有需要的 views =====
from analytics.views import admin_index, dashboard_data
# 修正：將 upload_avatar 加入匯入列表
from members.views import wechat_login, member_info, update_member_profile, upload_avatar 
from demo_orders.views import product_list, create_order, order_list, recommendations
from feedback.views import feedback_list
from coupons.views import coupon_list, redeem_options, redeem_coupon

urlpatterns = [
    # 根路徑直接跳轉到 admin 登入頁
    path('', RedirectView.as_view(url='/admin/', permanent=False)),
    
    # 自定義 dashboard 必須在 admin.site.urls 之前
    path('admin/dashboard/', admin_index, name='admin_dashboard'),
    path('api/dashboard/data/', dashboard_data, name='dashboard_data'),
    
    # Django admin 後台
    path('admin/', admin.site.urls),

    # ===== 小程序 API =====
    path('api/login/', wechat_login),
    path('api/member/', member_info),
    
    # 個人資料更新 API
    path('api/member/update-profile/', update_member_profile),

    path('api/products/', product_list),
    path('api/orders/', create_order),
    path('api/orders/list/', order_list),
    path('api/recommendations/', recommendations),
    path('api/feedback/', feedback_list),
    path('api/coupons/', coupon_list),
    path('api/coupons/options/', redeem_options),
    path('api/coupons/redeem/', redeem_coupon),
    
    # 修正：直接使用 upload_avatar 函數
    path('api/upload_avatar/', upload_avatar, name='upload_avatar'),
]

# 為了確保在雲端環境（DEBUG=False）下也能正常顯示媒體檔案（如頭像與產品圖）
# 我們強制允許 Django 處理媒體檔案路由，這對畢業設計系統的展示至關重要
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]