from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import LeaveRequest, Employee, ApprovalHistory
from .forms import EmployeeCreationForm, EmployeeUpdateForm
from .utils import send_notification_email

# --- ฟังก์ชันสำหรับตรวจสอบสิทธิ์ ---
def is_hr_or_admin(user):
    """ตรวจสอบว่าผู้ใช้เป็น HR, Admin, หรือ Superuser หรือไม่"""
    if not hasattr(user, 'employee'):
        return user.is_superuser
    return user.employee.role.role_name.lower() in ['hr', 'admin']

# --- ฟังก์ชันตรวจสอบ Superuser สำหรับหน้าทดสอบ ---
def is_superuser(user):
    return user.is_superuser

# --- หน้าหลัก / Dashboard ---
@login_required
def dashboard(request):
    """
    View สำหรับหน้า Dashboard หลัก
    จะแสดงข้อมูลสรุปที่แตกต่างกันไปตามโปรไฟล์และสิทธิ์ของผู้ใช้
    """
    if not hasattr(request.user, 'employee'):
        messages.error(request, 'บัญชีผู้ใช้ของคุณยังไม่ได้ผูกกับโปรไฟล์พนักงาน กรุณาติดต่อฝ่ายบุคคล')
        is_admin_or_superuser = request.user.is_superuser
        return render(request, 'app/dashboard.html', {
            'is_approver_or_admin': is_admin_or_superuser, 
            'is_hr_or_admin': is_admin_or_superuser
        })

    employee = request.user.employee
    my_requests = LeaveRequest.objects.filter(employee=employee)
    pending_my_approval = ApprovalHistory.objects.filter(approver=employee, status='Pending')
    is_approver = employee.role.role_name.lower() in ['manager', 'supervisor', 'hr', 'safety']
    
    context = {
        'pending_requests_count': my_requests.filter(status__in=['Pending', 'Info Requested']).count(),
        'approved_requests_count': my_requests.filter(status='Approved').count(),
        'rejected_requests_count': my_requests.filter(status='Rejected').count(),
        'total_employees_count': Employee.objects.count(),
        'is_approver_or_admin': is_approver or request.user.is_superuser,
        'is_hr_or_admin': is_hr_or_admin(request.user),
        'approval_inbox_count': pending_my_approval.count(),
    }
    return render(request, 'app/dashboard.html', context)

# --- ส่วนของการจัดการคำขอ (สำหรับพนักงาน) ---

@login_required
def create_leave_request(request):
    """View สำหรับหน้าสร้างคำขออนุญาตออกนอกสถานที่"""
    if not hasattr(request.user, 'employee'):
        messages.error(request, 'ไม่สามารถสร้างคำขอได้: บัญชีของคุณยังไม่ได้ผูกกับโปรไฟล์พนักงาน')
        return redirect('app:dashboard')

    if request.method == 'POST':
        employee = request.user.employee
        
        leave_request = LeaveRequest.objects.create(
            employee=employee,
            reason=request.POST.get('reason'),
            leave_date=request.POST.get('leave_date'),
            leave_duration=request.POST.get('leave_duration'),
            status='Pending',
            current_approver_role='manager',
            attachment=request.FILES.get('attachment')
        )

        # ดึงข้อมูลล่าสุดจากฐานข้อมูลเพื่อให้แน่ใจว่าข้อมูลครบถ้วนก่อนส่งอีเมล
        leave_request.refresh_from_db()
        
        try:
            manager = Employee.objects.get(department=employee.department, role__role_name__iexact='Manager')
            ApprovalHistory.objects.create(request=leave_request, approver=manager, approval_order=1, status='Pending')
            messages.success(request, 'ส่งคำขอสำเร็จ กำลังรอการอนุมัติจากผู้จัดการ')
            # Send Email
            send_notification_email(
                subject=f"คำขอใหม่ [{leave_request.request_id}] จากคุณ {employee.name}",
                message_body=f"มีคำขอออกนอกสถานที่ใหม่จากคุณ {employee.name} รอการอนุมัติจากคุณ",
                recipient=manager,
                request_obj=leave_request
            )
        except Employee.DoesNotExist:
            leave_request.status = 'Rejected'
            leave_request.reason += '\n[System: ไม่พบผู้จัดการในแผนกนี้]'
            leave_request.save()
            messages.error(request, 'ไม่สามารถส่งคำขอได้: ไม่พบผู้จัดการสำหรับแผนกของคุณ')
        return redirect('app:dashboard')
    
    return render(request, 'app/create_request_form.html')

@login_required
def provide_info_view(request, request_id):
    """View สำหรับให้พนักงานส่งข้อมูลเพิ่มเติมตามที่ถูกร้องขอ"""
    leave_request = get_object_or_404(LeaveRequest, request_id=request_id, employee=request.user.employee)

    if leave_request.status != 'Info Requested':
        messages.error(request, 'คำขอนี้ไม่ได้อยู่ในสถานะรอข้อมูลเพิ่มเติม')
        return redirect('app:dashboard')
    
    if request.method == 'POST':
        leave_request.reason = request.POST.get('reason', leave_request.reason)
        
        if 'attachment' in request.FILES:
            leave_request.attachment = request.FILES['attachment']
        
        leave_request.status = 'Pending'
        leave_request.info_request_comment = None
        leave_request.save()
        
        history = ApprovalHistory.objects.filter(request=leave_request, status='Pending').first()
        if history:
            send_notification_email(
                subject=f"มีการให้ข้อมูลเพิ่มเติมสำหรับคำขอ [{leave_request.request_id}]",
                message_body=f"คุณ {leave_request.employee.name} ได้ให้ข้อมูลเพิ่มเติมสำหรับคำขอที่คุณร้องขอแล้ว",
                recipient=history.approver,
                request_obj=leave_request
            )

        messages.success(request, f'ส่งข้อมูลเพิ่มเติมสำหรับคำขอ ID: {leave_request.request_id} เรียบร้อยแล้ว')
        return redirect('app:requests-pending')
        
    context = {'request': leave_request}
    return render(request, 'app/provide_info_form.html', context)

# --- ส่วนของการแสดงผลรายการคำขอ ---

@login_required
def pending_requests_view(request):
    if not hasattr(request.user, 'employee'): return redirect('app:dashboard')
    employee = request.user.employee
    requests = LeaveRequest.objects.filter(
        employee=employee, 
        status__in=['Pending', 'Info Requested']
    ).order_by('-request_datetime')
    context = {'requests': requests, 'status_title': 'รอการอนุมัติ/ดำเนินการ'}
    return render(request, 'app/request_list.html', context)

@login_required
def approved_requests_view(request):
    if not hasattr(request.user, 'employee'): return redirect('app:dashboard')
    requests = LeaveRequest.objects.filter(employee=request.user.employee, status='Approved').order_by('-request_datetime')
    context = {'requests': requests, 'status_title': 'อนุมัติแล้ว'}
    return render(request, 'app/request_list.html', context)

@login_required
def rejected_requests_view(request):
    if not hasattr(request.user, 'employee'): return redirect('app:dashboard')
    requests = LeaveRequest.objects.filter(employee=request.user.employee, status='Rejected').order_by('-request_datetime')
    context = {'requests': requests, 'status_title': 'ถูกปฏิเสธ'}
    return render(request, 'app/request_list.html', context)

# --- ส่วนของผู้อนุมัติ (Approvers) ---

@login_required
def approval_inbox(request):
    if not hasattr(request.user, 'employee'):
        messages.error(request, 'คุณไม่มีโปรไฟล์พนักงานสำหรับเข้าถึงหน้านี้')
        return redirect('app:dashboard')
    pending_list = ApprovalHistory.objects.filter(approver=request.user.employee, status='Pending').order_by('request__request_datetime')
    context = {'pending_list': pending_list}
    return render(request, 'app/approval_inbox.html', context)

@login_required
def process_approval(request, history_id):
    history = get_object_or_404(ApprovalHistory, history_id=history_id, approver=request.user.employee)
    leave_request = history.request
    
    if request.method == 'POST':
        decision = request.POST.get('decision')
        comment = request.POST.get('comment', '')

        if decision == 'request_info':
            leave_request.status = 'Info Requested'
            leave_request.info_request_comment = comment
            history.comment = f"ขอข้อมูลเพิ่มเติม: {comment}"
            leave_request.save()
            history.save()
            messages.info(request, f'ส่งคำขอข้อมูลเพิ่มเติมสำหรับ ID: {leave_request.request_id} กลับไปยังพนักงานแล้ว')
            send_notification_email(
                subject=f"ต้องการข้อมูลเพิ่มเติมสำหรับคำขอ [{leave_request.request_id}]",
                message_body=f"ผู้อนุมัติของคุณต้องการข้อมูลเพิ่มเติมสำหรับคำขอของคุณ เหตุผล: {comment}",
                recipient=leave_request.employee,
                request_obj=leave_request
            )
            return redirect('app:approval_inbox')

        history.comment = comment
        history.approval_date = timezone.now().date()
        history.approval_time = timezone.now().time()

        if decision == 'approve':
            history.status = 'Approved'
            if history.approval_order == 1: # Manager
                try:
                    supervisor = Employee.objects.get(department=leave_request.employee.department, role__role_name__iexact='Supervisor')
                    leave_request.current_approver_role = 'supervisor'
                    ApprovalHistory.objects.create(request=leave_request, approver=supervisor, approval_order=2, status='Pending')
                    messages.success(request, f'อนุมัติคำขอ ID: {leave_request.request_id} สำเร็จ ส่งต่อไปยัง Supervisor')
                    send_notification_email(
                        subject=f"คำขอ [{leave_request.request_id}] รอการอนุมัติจากคุณ",
                        message_body=f"มีคำขอจากคุณ {leave_request.employee.name} รอการอนุมัติจากคุณ",
                        recipient=supervisor,
                        request_obj=leave_request
                    )
                except Employee.DoesNotExist:
                     leave_request.status = 'Rejected'
                     leave_request.current_approver_role = 'completed'
                     messages.error(request, 'ไม่พบ Supervisor ในแผนก คำขอจึงถูกยกเลิก')
            
            elif history.approval_order == 2: # Supervisor
                hr_and_safety = Employee.objects.filter(Q(role__role_name__iexact='hr') | Q(role__role_name__iexact='safety'))
                if hr_and_safety.exists():
                    leave_request.current_approver_role = 'hr_safety'
                    for approver in hr_and_safety:
                        ApprovalHistory.objects.create(request=leave_request, approver=approver, approval_order=3, status='Pending')
                        send_notification_email(
                            subject=f"คำขอ [{leave_request.request_id}] รอการอนุมัติจาก HR/Safety",
                            message_body=f"มีคำขอจากคุณ {leave_request.employee.name} รอการอนุมัติจากแผนกของท่าน",
                            recipient=approver,
                            request_obj=leave_request
                        )
                    messages.success(request, f'อนุมัติคำขอ ID: {leave_request.request_id} สำเร็จ ส่งต่อไปยัง HR/Safety')
                else:
                    leave_request.status = 'Rejected'
                    leave_request.current_approver_role = 'completed'
                    messages.error(request, 'ไม่พบตำแหน่ง HR หรือ Safety คำขอจึงถูกยกเลิก')
            
            elif history.approval_order == 3: # HR or Safety
                leave_request.status = 'Approved'
                leave_request.current_approver_role = 'completed'
                ApprovalHistory.objects.filter(request=leave_request, status='Pending').delete()
                messages.success(request, f'การอนุมัติสำหรับคำขอ ID: {leave_request.request_id} เสร็จสมบูรณ์')
                send_notification_email(
                    subject=f"คำขอ [{leave_request.request_id}] ของคุณได้รับการอนุมัติแล้ว",
                    message_body="ยินดีด้วย! คำขอออกนอกสถานที่ของคุณได้รับการอนุมัติอย่างสมบูรณ์แล้ว",
                    recipient=leave_request.employee,
                    request_obj=leave_request
                )
        
        elif decision == 'reject':
            history.status = 'Rejected'
            leave_request.status = 'Rejected'
            leave_request.current_approver_role = 'completed'
            messages.warning(request, f'คุณได้ปฏิเสธคำขอ ID: {leave_request.request_id}')
            send_notification_email(
                subject=f"คำขอ [{leave_request.request_id}] ของคุณถูกปฏิเสธ",
                message_body=f"คำขอออกนอกสถานที่ของคุณถูกปฏิเสธโดยผู้อนุมัติ เหตุผล: {comment}",
                recipient=leave_request.employee,
                request_obj=leave_request
            )

        leave_request.save()
        history.save()
    return redirect('app:approval_inbox')

# --- ส่วนของการจัดการพนักงาน (HR/Admin) ---

@login_required
@user_passes_test(is_hr_or_admin, login_url='/')
def employee_list_view(request):
    employees = Employee.objects.all().order_by('name')
    return render(request, 'app/members_list.html', {'employees': employees})

@login_required
@user_passes_test(is_hr_or_admin, login_url='/')
def create_user_view(request):
    if request.method == 'POST':
        form = EmployeeCreationForm(request.POST, request.FILES)
        if form.is_valid():
            employee = form.save()
            messages.success(request, f'สร้างพนักงาน "{employee.name}" เรียบร้อยแล้ว')
            return redirect('app:employee-list')
    else:
        form = EmployeeCreationForm()
    return render(request, 'app/create_user.html', {'form': form})

@login_required
@user_passes_test(is_hr_or_admin, login_url='/')
def edit_employee_view(request, employee_id):
    employee = get_object_or_404(Employee, employee_id=employee_id)
    if request.method == 'POST':
        form = EmployeeUpdateForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, f'อัปเดตข้อมูลของ "{employee.name}" เรียบร้อยแล้ว')
            return redirect('app:employee-list')
    else:
        form = EmployeeUpdateForm(instance=employee)
    return render(request, 'app/edit_employee.html', {'form': form})

@login_required
@user_passes_test(is_hr_or_admin, login_url='/')
def delete_employee_view(request, employee_id):
    if request.method == 'POST':
        employee = get_object_or_404(Employee, employee_id=employee_id)
        user_to_delete = employee.user
        employee_name = employee.name
        if request.user == user_to_delete:
            messages.error(request, 'คุณไม่สามารถลบบัญชีของตัวเองได้')
            return redirect('app:employee-list')
        if user_to_delete.is_superuser:
            messages.error(request, 'ไม่สามารถลบ Superuser ได้')
            return redirect('app:employee-list')
        user_to_delete.delete()
        messages.success(request, f'ลบพนักงาน "{employee_name}" ออกจากระบบเรียบร้อยแล้ว')
    return redirect('app:employee-list')


# --- ฟังก์ชันสำหรับทดสอบอีเมล ---
@login_required
@user_passes_test(is_superuser) # จำกัดให้ Superuser เท่านั้นที่เข้าได้
def test_email_view(request, request_id):
    """
    View สำหรับทดสอบการแสดงผลของ Template อีเมล
    """
    leave_request = get_object_or_404(LeaveRequest, pk=request_id)
    # จำลองการส่งหา Manager
    recipient = Employee.objects.filter(department=leave_request.employee.department, role__role_name__iexact='Manager').first()

    context = {
        'recipient_name': recipient.name if recipient else 'ไม่มีผู้รับ',
        'message_body': 'นี่คือข้อความทดสอบสำหรับอีเมลแจ้งเตือน',
        'request_obj': leave_request
    }
    return render(request, 'app/test_email.html', context)

