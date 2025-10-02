from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Complain, Employee, ApprovalHistory

@login_required
def dashboard(request):
    """
    Viewสำหรับหน้าแดชบอร์ด
    จะแสดงข้อมูลสรุปที่แตกต่างกันตามบทบาทของผู้ใช้
    """
    
    user = request.user
    employee = None # กำหนดค่าเริ่มต้นเป็น None
    
    # --- จุดที่แก้ไข ---
    # ใช้วิธีที่ปลอดภัยกว่าในการตรวจสอบว่า user มี employee profile หรือไม่
    if hasattr(user, 'employee'):
        employee = user.employee

    # กำหนดค่าเริ่มต้นสำหรับตัวแปรทั้งหมด
    pending_requests_count = 0
    approved_requests_count = 0
    rejected_requests_count = 0
    total_employees_count = Employee.objects.count()
    is_approver_or_admin = False
    approval_inbox_count = 0

    if user.is_superuser:
        is_approver_or_admin = True
        # Superuser จะเห็นภาพรวมทั้งหมดของระบบ
        pending_requests_count = Complain.objects.filter(status='Pending').count()
        approved_requests_count = Complain.objects.filter(status='Approved').count()
        rejected_requests_count = Complain.objects.filter(status='Rejected').count()
        if employee: # ตรวจสอบอีกครั้งว่า superuser มี profile หรือไม่
             approval_inbox_count = ApprovalHistory.objects.filter(approver=employee, status='Pending').count()

    elif employee:
        # --- คำนวณข้อมูลสำหรับพนักงานทั่วไป ---
        pending_requests_count = Complain.objects.filter(employee=employee, status='Pending').count()
        approved_requests_count = Complain.objects.filter(employee=employee, status='Approved').count()
        rejected_requests_count = Complain.objects.filter(employee=employee, status='Rejected').count()

        # --- ตรวจสอบสิทธิ์และคำนวณข้อมูลสำหรับผู้อนุมัติ ---
        approver_roles = ['manager', 'supervisor', 'hr', 'safety']
        if employee.role and (employee.role.role_name.lower() in approver_roles):
            is_approver_or_admin = True
        
        if is_approver_or_admin:
            approval_inbox_count = ApprovalHistory.objects.filter(approver=employee, status='Pending').count()

    context = {
        'pending_requests_count': pending_requests_count,
        'approved_requests_count': approved_requests_count,
        'rejected_requests_count': rejected_requests_count,
        'total_employees_count': total_employees_count,
        'is_approver_or_admin': is_approver_or_admin,
        'approval_inbox_count': approval_inbox_count,
    }
    
    return render(request, 'app/dashboard.html', context)

