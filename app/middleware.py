import json
import os
from django.conf import settings  # ⬅️ (เพิ่ม)
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import Employee

CONFIG_FILE_PATH = os.path.join(settings.BASE_DIR, "site_config.json")


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            # .get(..., True) หมายความว่า ถ้ายังไม่มีคีย์นี้ในไฟล์ ให้ถือว่า "เปิดใช้งาน" (True) เป็นค่าเริ่มต้น
            is_feature_enabled = config.get("force_password_change_enabled", True)
        except (FileNotFoundError, json.JSONDecodeError):
            is_feature_enabled = True  # ถ้าไฟล์ config เจ๊ง ให้เปิดใช้งานไว้ก่อน (ปลอดภัย)

        # 2. ถ้าฟีเจอร์นี้ถูก "ปิด" ให้ออกจาก middleware นี้ไปเลย
        if not is_feature_enabled:
            return self.get_response(request)
        # --- ⬆️ (สิ้นสุดส่วนที่เพิ่ม) ⬆️ ---

        # 3. (ตรรกะเดิม) ถ้าฟีเจอร์เปิดอยู่ ก็ให้ทำงานตรวจสอบตามปกติ
        if not request.user.is_authenticated or request.user.is_superuser:
            return self.get_response(request)

        try:
            employee_profile = request.user.employee
        except Employee.DoesNotExist:
            return self.get_response(request)

        if employee_profile.must_change_password:

            force_change_url = reverse("app:force-change-password")
            logout_url = reverse("app:logout")

            if (
                request.path.startswith(force_change_url)
                or request.path.startswith(logout_url)
                or request.path.startswith("/media/")
            ):

                return self.get_response(request)

            messages.warning(request, "กรุณาเปลี่ยนรหัสผ่านเริ่มต้นของคุณก่อนเข้าใช้งาน")
            return redirect(force_change_url)

        return self.get_response(request)
