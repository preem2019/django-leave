from django.contrib import admin
from django.urls import path, include
from app import views as app_views # Import view จากแอปพลิเคชัน 'app' ของเรา

urlpatterns = [
    # 1. URL สำหรับหน้า Admin ของ Django
    path('admin/', admin.site.urls),
    
    # 2. ตั้งค่าให้หน้าแรกของเว็บ ('') เรียกใช้ view ที่ชื่อ dashboard
    # และตั้งชื่อว่า 'home' เพื่อให้ลิงก์ "หน้าหลัก" ใน base.html ทำงานได้
    path('', app_views.dashboard, name='home'), 
    
    # 3. นำ URL ทั้งหมดจากไฟล์ app/urls.py เข้ามารวมในโปรเจกต์
    # บรรทัดนี้จะทำให้ URL 'dashboard/' จากไฟล์ข้างบนใช้งานได้
    path('', include('app.urls')),
]

