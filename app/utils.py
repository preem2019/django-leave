from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

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

