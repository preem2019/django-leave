import json
import os
from django.conf import settings

# ระบุตำแหน่งไฟล์ Config
CONFIG_FILE_PATH = os.path.join(settings.BASE_DIR, 'site_config.json')

def load_site_config(request):
    try:
        # เปิดไฟล์ .json เพื่ออ่านค่า
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # ถ้าไฟล์ไม่มี หรือไฟล์เสีย ให้ใช้ค่าเริ่มต้นแทน
        config = {
            'brand_name': 'eLeave (Default)',
            'footer_text': '&copy; 2025 (Default)',
            'color_primary': '#3498db',
            'color_success': '#198754',
            'color_warning': '#f39c12',
            'color_danger': '#e74c3c'
        }
    return {'site_config': config}