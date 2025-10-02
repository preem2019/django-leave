from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import LeaveRequest, Employee, ApprovalHistory

# --- หน้าหลัก / Dashboard ---
@login_required
def dashboard(request):
    if not hasattr(request.user, 'employee'):
        messages.error(request, 'บัญชีผู้ใช้ของคุณยังไม่ได้ผูกกับโปรไฟล์พนักงาน กรุณาติดต่อฝ่ายบุคคล')
        return render(request, 'app/dashboard.html', {'is_approver_or_admin': request.user.is_superuser})

    employee = request.user.employee
    
    # ดึงข้อมูลสำหรับ Cards บน Dashboard
    pending_requests_count = LeaveRequest.objects.filter(employee=employee, status='Pending').count()
    approved_requests_count = LeaveRequest.objects.filter(employee=employee, status='Approved').count()
    rejected_requests_count = LeaveRequest.objects.filter(employee=employee, status='Rejected').count()
    total_employees_count = Employee.objects.count()
    is_approver_or_admin = employee.role.role_name.lower() in ['manager', 'supervisor', 'hr', 'safety', 'admin'] or request.user.is_superuser
    
    # คำนวณรายการที่รอเราอนุมัติ
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


# --- Section for creating and managing requests ---

@login_required
def create_leave_request(request):
    if not hasattr(request.user, 'employee'):
        messages.error(request, 'ไม่สามารถสร้างคำขอได้: บัญชีผู้ใช้ของคุณยังไม่ได้ผูกกับโปรไฟล์พนักงาน')
        return redirect('app:dashboard')

    if request.method == 'POST':
        employee = request.user.employee
        reason = request.POST.get('reason')
        leave_date = request.POST.get('leave_date')
        leave_duration = request.POST.get('leave_duration')
        
        # สร้างคำขอหลัก
        leave_request = LeaveRequest.objects.create(
            employee=employee,
            reason=reason,
            leave_date=leave_date,
            leave_duration=leave_duration,
            status='Pending',
            current_approver_role='manager'
        )

        # ค้นหาผู้อนุมัติคนแรก (Manager)
        try:
            manager = Employee.objects.get(
                department=employee.department,
                role__role_name__iexact='Manager'
            )
            # สร้างประวัติการอนุมัติให้ Manager
            ApprovalHistory.objects.create(
                request=leave_request,
                approver=manager,
                approval_order=1,
                status='Pending'
            )
            messages.success(request, 'ส่งคำขอสำเร็จ กำลังรอการอนุมัติจากผู้จัดการ')
        except Employee.DoesNotExist:
            leave_request.status = 'Rejected'
            leave_request.reason += '\n[System: ไม่พบผู้จัดการในแผนกของคุณ]'
            leave_request.save()
            messages.error(request, 'ไม่สามารถส่งคำขอได้: ไม่พบผู้จัดการในแผนกของคุณ')
        
        return redirect('app:dashboard')

    return render(request, 'app/create_request_form.html')

# --- Views for displaying request lists based on status ---

@login_required
def pending_requests_view(request):
    """ แสดงรายการคำขอที่กำลังรออนุมัติ """
    if not hasattr(request.user, 'employee'):
        return redirect('app:dashboard')
    employee = request.user.employee
    # *** FIXED: Changed order_by to use 'request_datetime' ***
    requests = LeaveRequest.objects.filter(employee=employee, status='Pending').order_by('-request_datetime')
    context = {
        'requests': requests,
        'title': 'คำขอที่รออนุมัติ',
        'icon': 'fa-user-clock'
        }
    return render(request, 'app/request_list.html', context)

@login_required
def approved_requests_view(request):
    """ แสดงรายการคำขอที่อนุมัติแล้ว """
    if not hasattr(request.user, 'employee'):
        return redirect('app:dashboard')
    employee = request.user.employee
    # *** FIXED: Changed order_by to use 'request_datetime' ***
    requests = LeaveRequest.objects.filter(employee=employee, status='Approved').order_by('-request_datetime')
    context = {
        'requests': requests,
        'title': 'คำขอที่อนุมัติแล้ว',
        'icon': 'fa-check-circle'
    }
    return render(request, 'app/request_list.html', context)

@login_required
def rejected_requests_view(request):
    """ แสดงรายการคำขอที่ถูกปฏิเสธ """
    if not hasattr(request.user, 'employee'):
        return redirect('app:dashboard')
    employee = request.user.employee
    # *** FIXED: Changed order_by to use 'request_datetime' ***
    requests = LeaveRequest.objects.filter(employee=employee, status='Rejected').order_by('-request_datetime')
    context = {
        'requests': requests,
        'title': 'คำขอที่ถูกปฏิเสธ',
        'icon': 'fa-times-circle'
    }
    return render(request, 'app/request_list.html', context)


# --- Section for approvers ---

@login_required
def approval_inbox(request):
    """ กล่องงานอนุมัติ """
    if not hasattr(request.user, 'employee'):
        messages.error(request, 'คุณไม่มีโปรไฟล์พนักงานสำหรับเข้าถึงหน้านี้')
        return redirect('app:dashboard')

    employee = request.user.employee
    pending_list = ApprovalHistory.objects.filter(
        approver=employee, 
        status='Pending'
    ).order_by('request__request_datetime') # Ordered by when the request was made
    
    context = {'pending_list': pending_list}
    return render(request, 'app/approval_inbox.html', context)

@login_required
def process_approval(request, history_id):
    """ View สำหรับจัดการการอนุมัติและปฏิเสธ """
    if not hasattr(request.user, 'employee'):
        messages.error(request, 'คุณไม่มีสิทธิ์ดำเนินการ')
        return redirect('app:dashboard')

    history = get_object_or_404(ApprovalHistory, history_id=history_id, approver=request.user.employee)
    leave_request = history.request

    if request.method == 'POST':
        decision = request.POST.get('decision') # 'approve' or 'reject'
        comment = request.POST.get('comment')

        history.comment = comment
        history.approval_date = timezone.now().date()
        history.approval_time = timezone.now().time()

        if decision == 'approve':
            history.status = 'Approved'
            history.save()
            
            # --- Approval Workflow Logic ---
            if history.approval_order == 1: # Manager approved
                try:
                    supervisor = Employee.objects.get(department=leave_request.employee.department, role__role_name__iexact='Supervisor')
                    leave_request.current_approver_role = 'supervisor'
                    leave_request.save()
                    ApprovalHistory.objects.create(request=leave_request, approver=supervisor, approval_order=2, status='Pending')
                    messages.success(request, f'อนุมัติคำขอ #{leave_request.request_id} สำเร็จ ส่งต่อไปยัง Supervisor')
                except Employee.DoesNotExist:
                     messages.error(request, 'ไม่พบ Supervisor ในแผนก คำขอจึงถูกยกเลิก')
                     leave_request.status = 'Rejected'
                     leave_request.current_approver_role = 'completed'
                     leave_request.save()

            elif history.approval_order == 2: # Supervisor approved
                hr_and_safety = Employee.objects.filter(role__role_name__in=['HR', 'Safety'])
                if hr_and_safety.exists():
                    leave_request.current_approver_role = 'hr_safety'
                    leave_request.save()
                    for approver in hr_and_safety:
                        ApprovalHistory.objects.create(request=leave_request, approver=approver, approval_order=3, status='Pending')
                    messages.success(request, f'อนุมัติคำขอ #{leave_request.request_id} สำเร็จ ส่งต่อไปยัง HR/Safety')
                else:
                    messages.error(request, 'ไม่พบพนักงานฝ่าย HR หรือ Safety ในระบบ คำขอจึงถูกยกเลิก')
                    leave_request.status = 'Rejected'
                    leave_request.current_approver_role = 'completed'
                    leave_request.save()
            
            elif history.approval_order == 3: # HR or Safety approved
                leave_request.status = 'Approved'
                leave_request.current_approver_role = 'completed'
                leave_request.save()
                
                # ลบ Pending อื่นๆ ของ HR/Safety ที่ยังไม่ได้กดอนุมัติสำหรับคำขอนี้
                ApprovalHistory.objects.filter(request=leave_request, status='Pending').delete()
                messages.success(request, f'การอนุมัติสำหรับคำขอ #{leave_request.request_id} เสร็จสมบูรณ์')

        elif decision == 'reject':
            history.status = 'Rejected'
            history.save()
            leave_request.status = 'Rejected'
            leave_request.current_approver_role = 'completed'
            leave_request.save()
            messages.warning(request, f'คุณได้ปฏิเสธคำขอ #{leave_request.request_id}')

        return redirect('app:approval-inbox')

    return redirect('app:approval-inbox')

