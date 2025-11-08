from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import Employee # ⬅️ เพิ่ม import นี้

class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. ถ้ายังไม่ login หรือเป็น superuser ก็ปล่อยผ่าน (Superuser ไม่ควรถูกบังคับ)
        if not request.user.is_authenticated or request.user.is_superuser:
            return self.get_response(request)

        # 2. ถ้าไม่มี profile employee (อาจจะยัง setup ไม่เสร็จ) ก็ปล่อยผ่าน
        try:
            employee_profile = request.user.employee
        except Employee.DoesNotExist:
             return self.get_response(request)

        # 3. ตรวจสอบว่าต้องเปลี่ยนรหัสผ่านหรือไม่
        if employee_profile.must_change_password:
            
            # 4. ตรวจสอบว่าหน้าทีกำลังจะไป คือหน้า "บังคับเปลี่ยนรหัส" หรือ "logout" หรือไม่
            force_change_url = reverse('app:force-change-password')
            logout_url = reverse('app:logout')
            
            # อนุญาตให้เข้าถึงหน้า media (สำหรับไฟล์ CSS/JS รูปภาพ)
            if (request.path.startswith(force_change_url) or 
                request.path.startswith(logout_url) or
                request.path.startswith('/media/')): # ⬅️ เพิ่มเงื่อนไขนี้
                
                return self.get_response(request) # 6. ถ้าใช่ ก็ปล่อยผ่าน
            
            # 5. ถ้าไม่ใช่, ให้ redirect ไปหน้าบังคับเปลี่ยนรหัส
            messages.warning(request, "กรุณาเปลี่ยนรหัสผ่านเริ่มต้นของคุณก่อนเข้าใช้งาน")
            return redirect(force_change_url)
        
        # 7. ถ้าเงื่อนไขไม่ตรง (ไม่ต้องเปลี่ยนรหัส) ก็ไปหน้าถัดไปตามปกติ
        return self.get_response(request)