from django.contrib import admin
from django.urls import path, include
# --- Import ที่เพิ่มเข้ามาใหม่ ---
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app.urls')),
    path('db-manager/', include('db_manager.urls')),
]

# --- การตั้งค่าที่เพิ่มเข้ามาใหม่ ---
# เพิ่ม path สำหรับให้บริการไฟล์ media ในระหว่างการพัฒนา (development)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

