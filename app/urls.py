from django.urls import path
from . import views

# กำหนด namespace สำหรับแอปพลิเคชันนี้ เพื่อป้องกันชื่อ URL ซ้ำกัน
app_name = 'app'

urlpatterns = [
    # URL สำหรับหน้า Dashboard หลัก
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # URL สำหรับ "กล่องงานอนุมัติ" ของผู้จัดการ, HR, etc.
    # หมายเหตุ: ตอนนี้เราจะให้มันชี้ไปที่ view dashboard ชั่วคราวก่อน
    # เพื่อป้องกัน Error เวลาคลิกลิงก์
    path('approval-inbox/', views.dashboard, name='approval-inbox'),
    
    # URL สำหรับหน้า "ประวัติคำขอของฉัน" ของพนักงาน
    # หมายเหตุ: ตอนนี้เราจะให้มันชี้ไปที่ view dashboard ชั่วคราวก่อนเช่นกัน
    path('my-requests/', views.dashboard, name='my-requests'),
]

