from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import requests

def send_notification_email(subject, message_body, recipient, request_obj):
    """
    ฟังก์ชันสำหรับส่งอีเมลแจ้งเตือน (เวอร์ชันอัปเดต)
    - recipient: รับเป็น Employee object
    - request_obj: รับเป็น LeaveRequest object
    """
    try:
        # ตรวจสอบว่าผู้รับมีอีเมลที่ถูกต้องหรือไม่
        if not recipient or not recipient.user or not recipient.user.email:
            print(f"Email not sent: Recipient '{recipient.name}' has no valid email.")
            return

        # สร้าง context เพื่อส่งไปยัง template
        context = {
            'recipient_name': recipient.name,
            'message_body': message_body,
            'request_obj': request_obj
        }
        
        # ใช้ template ในการสร้างเนื้อหาอีเมล (เป็น plain text)
        email_content = render_to_string('app/email/notification_email.txt', context)
        
        send_mail(
            subject=subject,
            message=email_content, # เนื้อหาหลักตอนนี้คือ plain text
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.user.email],
            fail_silently=False,
        )
        print(f"Email sent to: {recipient.name} ({recipient.user.email})")

    except Exception as e:
        print(f"Error sending email: {e}")

def send_notification_line(message, recipient):
    """
    ฟังก์ชันสำหรับส่งข้อความแจ้งเตือนไปยัง Line
    - message: ข้อความที่ต้องการส่ง (String)
    - recipient: Employee object ของผู้รับ
    """
    target_line_id = None

    # --- ส่วนที่แก้ไข: ตรวจสอบโหมด DEBUG ---
    # ถ้า DEBUG = True และมีการตั้งค่า LINE_TEST_USER_ID, ให้ส่งไปที่ ID นั้นแทน
    if settings.DEBUG and hasattr(settings, 'LINE_TEST_USER_ID') and settings.LINE_TEST_USER_ID:
        target_line_id = settings.LINE_TEST_USER_ID
        print(f"--- DEBUG MODE: Redirecting Line message for '{recipient.name}' to TEST_USER_ID ---")
    # ------------------------------------
    else:
        # การทำงานปกติ
        if not recipient or not recipient.line_user_id:
            print(f"Line not sent: Recipient '{recipient.name}' has no Line User ID.")
            return
        target_line_id = recipient.line_user_id

    if not target_line_id:
        print("Line not sent: No target user ID found.")
        return

    try:
        url = 'https://api.line.me/v2/bot/message/push'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}'
        }
        data = {
            'to': target_line_id, # <-- ใช้ target_line_id ที่กำหนดไว้
            'messages': [{'type': 'text', 'text': message}]
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status() # ทำให้เกิด Error ถ้าหาก status code ไม่ใช่ 2xx
        
        print(f"Line sent to: {target_line_id}, Status: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Error sending Line message: {e}")
        # สามารถเพิ่มการ log error ที่ละเอียดขึ้นได้ตามต้องการ
    except Exception as e:
        print(f"An unexpected error occurred during Line notification: {e}")