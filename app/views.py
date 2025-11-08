# --- Library ---
import json
import os
from datetime import date

import openpyxl

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Count, DateField
from django.db.models.functions import TruncMonth, Cast
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

# --- 4. Local Application Imports ---
from .forms import EmployeeCreationForm, EmployeeUpdateForm, SiteConfigurationForm,UserProfileForm
from .models import LeaveRequest, Employee, ApprovalHistory, InOutHistory, VisitorLog
from .utils import send_notification_email, send_notification_line


# --- ฟังก์ชันสำหรับตรวจสอบสิทธิ์ ---
def is_hr_or_admin(user):
    """ตรวจสอบว่าผู้ใช้เป็น HR, Admin, หรือ Superuser หรือไม่"""
    if not hasattr(user, "employee"):
        return user.is_superuser
    return user.employee.role.role_name.lower() in ["hr", "admin", "safety"]


def is_security(user):
    """ตรวจสอบว่าผู้ใช้เป็น Security หรือไม่"""
    if not hasattr(user, "employee"):
        return False
    return user.employee.role.role_name.lower() == "security"


def is_superuser(user):
    return user.is_superuser


# --- หน้าหลัก / Dashboard (อัปเดต) ---
@login_required
def dashboard(request):
    """
    View สำหรับหน้า Dashboard หลัก
    จะแสดงข้อมูลสรุปที่แตกต่างกันไปตามโปรไฟล์และสิทธิ์ของผู้ใช้
    """
    # --- ⬇️ ให้เพิ่ม 2 บรรทัดนี้เข้าไปครับ ⬇️ ---
    if is_security(request.user):
        return redirect("app:security-dashboard")
    # --- ⬆️ สิ้นสุดโค้ดที่เพิ่ม ⬆️ ---

    if not hasattr(request.user, "employee"):
        messages.error(request, "บัญชีผู้ใช้ของคุณยังไม่ได้ผูกกับโปรไฟล์พนักงาน กรุณาติดต่อฝ่ายบุคคล")
        is_admin_or_superuser = request.user.is_superuser
        return render(
            request,
            "app/dashboard.html",
            {
                "is_approver_or_admin": is_admin_or_superuser,
                "is_hr_or_admin": is_admin_or_superuser,
            },
        )

    employee = request.user.employee
    my_requests = LeaveRequest.objects.filter(employee=employee)
    pending_my_approval = ApprovalHistory.objects.filter(
        approver=employee, status="Pending"
    )
    is_approver = employee.role.role_name.lower() in [
        "manager",
        "supervisor",
        "hr",
        "safety",
    ]

    context = {
        "pending_requests_count": my_requests.filter(
            status__in=["Pending", "Info Requested"]
        ).count(),
        "approved_requests_count": my_requests.filter(status="Approved").count(),
        "rejected_requests_count": my_requests.filter(status="Rejected").count(),
        "total_employees_count": Employee.objects.count(),
        "is_approver_or_admin": is_approver or is_hr_or_admin(request.user),
        "is_hr_or_admin": is_hr_or_admin(request.user),
        "is_security": is_security(request.user),  # เพิ่ม context สำหรับ security
        "approval_inbox_count": pending_my_approval.count(),
    }
    return render(request, "app/dashboard.html", context)


# --- ส่วนของการจัดการคำขอ (สำหรับพนักงาน) ---


@login_required
def create_leave_request(request):
    """View สำหรับหน้าสร้างคำขออนุญาตออกนอกสถานที่"""
    if not hasattr(request.user, "employee"):
        messages.error(request, "ไม่สามารถสร้างคำขอได้: บัญชีของคุณยังไม่ได้ผูกกับโปรไฟล์พนักงาน")
        return redirect("app:dashboard")

    if request.method == "POST":
        employee = request.user.employee

        leave_request = LeaveRequest.objects.create(
            employee=employee,
            reason=request.POST.get("reason"),
            leave_date=request.POST.get("leave_date"),
            leave_duration=request.POST.get("leave_duration"),
            status="Pending",
            current_approver_role="manager",
            attachment=request.FILES.get("attachment"),
        )

        leave_request.refresh_from_db()

        try:
            manager = Employee.objects.get(
                department=employee.department, role__role_name__iexact="Manager"
            )
            ApprovalHistory.objects.create(
                request=leave_request,
                approver=manager,
                approval_order=1,
                status="Pending",
            )
            messages.success(request, "ส่งคำขอสำเร็จ กำลังรอการอนุมัติจากผู้จัดการ")

            send_notification_email(
                subject=f"คำขอใหม่ [{leave_request.request_id}] จากคุณ {employee.name}",
                message_body=f"มีคำขอออกนอกสถานที่ใหม่จากคุณ {employee.name} รอการอนุมัติจากคุณ",
                recipient=manager,
                request_obj=leave_request,
            )

            # --- Send Line ---
            line_message = (
                f"สวัสดีคุณ {manager.name}\n\n"
                f"มีคำขอจากคุณ {leave_request.employee.name} รอการอนุมัติจากคุณ\n\n"
                f"---\n"
                f"รายละเอียดคำขอ:\n"
                f"  รหัสคำขอ: {leave_request.request_id}\n"
                f"  พนักงาน: {leave_request.employee.name}\n"
                f"  วันที่: {leave_request.leave_date.strftime('%d/%m/%Y')}\n"
                f"  ระยะเวลา: {leave_request.get_leave_duration_display()}\n"
                f"  เหตุผล: {leave_request.reason}\n"
                f"---"
            )
            send_notification_line(line_message, manager)
            # -----------------

        except Employee.DoesNotExist:
            leave_request.status = "Rejected"
            leave_request.reason += "\n[System: ไม่พบผู้จัดการในแผนกนี้]"
            leave_request.save()
            messages.error(request, "ไม่สามารถส่งคำขอได้: ไม่พบผู้จัดการสำหรับแผนกของคุณ")
        return redirect("app:dashboard")

    return render(request, "app/create_request_form.html")


@login_required
def provide_info_view(request, request_id):
    """View สำหรับให้พนักงานส่งข้อมูลเพิ่มเติมตามที่ถูกร้องขอ"""
    leave_request = get_object_or_404(
        LeaveRequest, request_id=request_id, employee=request.user.employee
    )

    if leave_request.status != "Info Requested":
        messages.error(request, "คำขอนี้ไม่ได้อยู่ในสถานะรอข้อมูลเพิ่มเติม")
        return redirect("app:dashboard")

    if request.method == "POST":
        leave_request.reason = request.POST.get("reason", leave_request.reason)

        if "attachment" in request.FILES:
            leave_request.attachment = request.FILES["attachment"]

        leave_request.status = "Pending"
        leave_request.info_request_comment = None
        leave_request.save()

        history = ApprovalHistory.objects.filter(
            request=leave_request, status="Pending"
        ).first()
        if history:
            send_notification_email(
                subject=f"มีการให้ข้อมูลเพิ่มเติมสำหรับคำขอ [{leave_request.request_id}]",
                message_body=f"คุณ {leave_request.employee.name} ได้ให้ข้อมูลเพิ่มเติมสำหรับคำขอที่คุณร้องขอแล้ว",
                recipient=history.approver,
                request_obj=leave_request,
            )
            # --- Send Line ---
            line_message = (
                f"สวัสดีคุณ {history.approver.name}\n\n"
                f"คุณ {leave_request.employee.name} ได้ให้ข้อมูลเพิ่มเติมสำหรับคำขอ [{leave_request.request_id}] แล้ว"
            )
            send_notification_line(line_message, history.approver)
            # -----------------

        messages.success(
            request, f"ส่งข้อมูลเพิ่มเติมสำหรับคำขอ ID: {leave_request.request_id} เรียบร้อยแล้ว"
        )
        return redirect("app:requests-pending")

    context = {"request": leave_request}
    return render(request, "app/provide_info_form.html", context)


@login_required
def cancel_leave_request(request, request_id):
    """
    View สำหรับให้พนักงาน 'ยกเลิก' คำขอของตนเอง
    (ตราบเท่าที่สถานะยังเป็น Pending หรือ Info Requested)
    """
    # 1. ค้นหาคำขอ และตรวจสอบว่าเป็นของพนักงานคนนี้จริง
    leave_request = get_object_or_404(
        LeaveRequest, request_id=request_id, employee=request.user.employee
    )

    # 2. ตรวจสอบว่าคำขอยังยกเลิกได้หรือไม่
    if leave_request.status not in ["Pending", "Info Requested"]:
        messages.error(request, "ไม่สามารถยกเลิกคำขอที่ถูกดำเนินการไปแล้วได้")
        return redirect("app:requests-pending")

    if request.method == "POST":
        # 3. ดึงเหตุผลการยกเลิกจากฟอร์ม
        cancel_reason = request.POST.get("cancel_reason")
        if not cancel_reason:
            messages.error(request, "กรุณาระบุเหตุผลในการยกเลิก")
            return redirect("app:requests-pending")

        # 4. ค้นหาประวัติการอนุมัติ(งาน) ที่ค้างอยู่
        pending_history = ApprovalHistory.objects.filter(
            request=leave_request, status="Pending"
        ).first()  # ค้นหางานที่ค้างอยู่ (อาจจะเป็นของ Manager หรือ Supervisor)

        # 5. อัปเดตสถานะ (นี่คือส่วนที่สำคัญที่สุด)
        if pending_history:
            # 5.1 อัปเดตประวัติที่ค้างอยู่ ให้เป็น 'Rejected'
            pending_history.status = "Rejected"
            pending_history.comment = f"ยกเลิกโดยพนักงาน: {cancel_reason}"
            pending_history.approval_date = timezone.now().date()
            pending_history.approval_time = timezone.now().time()
            pending_history.save()

            # 5.2 ส่งแจ้งเตือน (LINE/Email) ไปยังผู้อนุมัติที่ "เคย" ถืองานนั้นอยู่
            line_message = (
                f"สวัสดีคุณ {pending_history.approver.name}\n\n"
                f"คำขอ [{leave_request.request_id}] "
                f"จากคุณ {leave_request.employee.name} ได้ถูก 'ยกเลิก' โดยพนักงานแล้ว\n\n"
                f"เหตุผล: {cancel_reason}"
            )
            send_notification_line(line_message, pending_history.approver)
            send_notification_email(
                subject=f"คำขอ [{leave_request.request_id}] ถูกยกเลิกโดยพนักงาน",
                message_body=f"คำขอ [{leave_request.request_id}] จากคุณ {leave_request.employee.name} ได้ถูกยกเลิกแล้ว\nเหตุผล: {cancel_reason}",
                recipient=pending_history.approver,
                request_obj=leave_request,
            )

        # 5.3 อัปเดตคำขอหลัก (LeaveRequest) ให้เป็น 'Rejected'
        leave_request.status = "Rejected"
        leave_request.current_approver_role = "completed"  # ปิดกระบวนการ
        leave_request.save()

        messages.success(
            request, f"คำขอ # {leave_request.request_id} ได้ถูกยกเลิกเรียบร้อยแล้ว"
        )
        return redirect("app:requests-rejected")  # ส่งไปหน้า "ถูกปฏิเสธ"

    # หากไม่ใช่ POST (ปกติไม่ควรเกิดขึ้น)
    return redirect("app:requests-pending")


@login_required
def print_leave_request(request, request_id):
    """
    View สำหรับแสดงหน้า "พิมพ์คำขอ" ที่อนุมัติแล้ว
    ใช้ Template 'app/base_simple.html' ที่ไม่มี Navbar
    """
    leave_request = get_object_or_404(
        LeaveRequest, request_id=request_id, employee=request.user.employee
    )

    # เพื่อความปลอดภัย เราจะอนุญาตให้พิมพ์ได้เฉพาะคำขอที่ "อนุมัติแล้ว" เท่านั้น
    if leave_request.status != "Approved":
        messages.error(request, "ไม่สามารถพิมพ์คำขอที่ยังไม่ได้รับการอนุมัติได้")
        return redirect("app:requests-approved")

    # ดึงประวัติการอนุมัติทั้งหมด
    approval_history = leave_request.ordered_approval_history.filter(status="Approved")

    context = {
        "request": leave_request,
        "approval_history": approval_history,
    }

    # เราจะใช้ Template ใหม่ชื่อ 'print_request.html' (ซึ่งจะสร้างในขั้นตอนถัดไป)
    return render(request, "app/print_request.html", context)


# --- ส่วนของการแสดงผลรายการคำขอ ---


@login_required
def pending_requests_view(request):
    if not hasattr(request.user, "employee"):
        return redirect("app:dashboard")  # noqa: E701
    employee = request.user.employee
    requests = LeaveRequest.objects.filter(
        employee=employee, status__in=["Pending", "Info Requested"]
    ).order_by("-request_datetime")
    context = {"requests": requests, "status_title": "รอการอนุมัติ/ดำเนินการ"}
    return render(request, "app/request_list.html", context)


@login_required
def approved_requests_view(request):
    if not hasattr(request.user, "employee"):
        return redirect("app:dashboard")
    requests = LeaveRequest.objects.filter(
        employee=request.user.employee, status="Approved"
    ).order_by("-request_datetime")
    context = {"requests": requests, "status_title": "อนุมัติแล้ว"}
    return render(request, "app/request_list.html", context)


@login_required
def rejected_requests_view(request):
    if not hasattr(request.user, "employee"):
        return redirect("app:dashboard")
    requests = LeaveRequest.objects.filter(
        employee=request.user.employee, status="Rejected"
    ).order_by("-request_datetime")
    context = {"requests": requests, "status_title": "ถูกปฏิเสธ"}
    return render(request, "app/request_list.html", context)


# --- ส่วนของผู้อนุมัติ (Approvers) ---


@login_required
def approval_inbox(request):
    if not hasattr(request.user, "employee"):
        messages.error(request, "คุณไม่มีโปรไฟล์พนักงานสำหรับเข้าถึงหน้านี้")
        return redirect("app:dashboard")
    pending_list = ApprovalHistory.objects.filter(
        approver=request.user.employee, status="Pending"
    ).order_by("request__request_datetime")
    context = {"pending_list": pending_list}
    return render(request, "app/approval_inbox.html", context)


@login_required
def process_approval(request, history_id):
    history = get_object_or_404(
        ApprovalHistory, history_id=history_id, approver=request.user.employee
    )
    leave_request = history.request

    if request.method == "POST":
        decision = request.POST.get("decision")
        comment = request.POST.get("comment", "")

        if decision == "request_info":
            leave_request.status = "Info Requested"
            leave_request.info_request_comment = comment
            history.comment = f"ขอข้อมูลเพิ่มเติม: {comment}"
            leave_request.save()
            history.save()
            messages.info(
                request,
                f"ส่งคำขอข้อมูลเพิ่มเติมสำหรับ ID: {leave_request.request_id} กลับไปยังพนักงานแล้ว",
            )

            email_message_body = (
                f"ผู้อนุมัติของคุณต้องการข้อมูลเพิ่มเติมสำหรับคำขอของคุณ เหตุผล: {comment}"
            )
            send_notification_email(
                subject=f"ต้องการข้อมูลเพิ่มเติมสำหรับคำขอ [{leave_request.request_id}]",
                message_body=email_message_body,
                recipient=leave_request.employee,
                request_obj=leave_request,
            )
            # --- Send Line ---
            line_message = (
                f"สวัสดีคุณ {leave_request.employee.name}\n\n"
                f"ผู้อนุมัติต้องการข้อมูลเพิ่มเติมสำหรับคำขอ [{leave_request.request_id}]\n"
                f"เหตุผล: {comment}"
            )
            send_notification_line(line_message, leave_request.employee)
            # -----------------

            return redirect("app:approval-inbox")

        history.comment = comment
        history.approval_date = timezone.now().date()
        history.approval_time = timezone.now().time()

        if decision == "approve":
            history.status = "Approved"
            if history.approval_order == 1:  # Manager
                try:
                    supervisor = Employee.objects.get(
                        department=leave_request.employee.department,
                        role__role_name__iexact="Supervisor",
                    )
                    leave_request.current_approver_role = "supervisor"
                    ApprovalHistory.objects.create(
                        request=leave_request,
                        approver=supervisor,
                        approval_order=2,
                        status="Pending",
                    )
                    messages.success(
                        request,
                        f"อนุมัติคำขอ ID: {leave_request.request_id} สำเร็จ ส่งต่อไปยัง Supervisor",
                    )

                    email_message_body = (
                        f"มีคำขอจากคุณ {leave_request.employee.name} รอการอนุมัติจากคุณ"
                    )
                    send_notification_email(
                        subject=f"คำขอ [{leave_request.request_id}] รอการอนุมัติจากคุณ",
                        message_body=email_message_body,
                        recipient=supervisor,
                        request_obj=leave_request,
                    )
                    # --- Send Line ---
                    line_message = (
                        f"สวัสดีคุณ {supervisor.name}\n\n"
                        f"มีคำขอจากคุณ {leave_request.employee.name} รอการอนุมัติจากคุณ\n\n"
                        f"---\n"
                        f"รายละเอียดคำขอ:\n"
                        f"  รหัสคำขอ: {leave_request.request_id}\n"
                        f"  พนักงาน: {leave_request.employee.name}\n"
                        f"  วันที่: {leave_request.leave_date.strftime('%d/%m/%Y')}\n"
                        f"  ระยะเวลา: {leave_request.get_leave_duration_display()}\n"
                        f"  เหตุผล: {leave_request.reason}\n"
                        f"---"
                    )
                    send_notification_line(line_message, supervisor)
                    # -----------------
                except Employee.DoesNotExist:
                    leave_request.status = "Rejected"
                    leave_request.current_approver_role = "completed"
                    messages.error(request, "ไม่พบ Supervisor ในแผนก คำขอจึงถูกยกเลิก")

            elif history.approval_order == 2:  # Supervisor
                hr_and_safety = Employee.objects.filter(
                    Q(role__role_name__iexact="hr")
                    | Q(role__role_name__iexact="safety")
                )
                if hr_and_safety.exists():
                    leave_request.current_approver_role = "hr_safety"
                    messages.success(
                        request,
                        f"อนุมัติคำขอ ID: {leave_request.request_id} สำเร็จ ส่งต่อไปยัง HR/Safety",
                    )
                    for approver in hr_and_safety:
                        ApprovalHistory.objects.create(
                            request=leave_request,
                            approver=approver,
                            approval_order=3,
                            status="Pending",
                        )
                        email_message_body = f"มีคำขอจากคุณ {leave_request.employee.name} รอการอนุมัติจากแผนกของท่าน"
                        send_notification_email(
                            subject=f"คำขอ [{leave_request.request_id}] รอการอนุมัติจาก HR/Safety",
                            message_body=email_message_body,
                            recipient=approver,
                            request_obj=leave_request,
                        )
                        # --- Send Line ---
                        line_message = (
                            f"สวัสดีคุณ {approver.name}\n\n"
                            f"มีคำขอจากคุณ {leave_request.employee.name} รอการอนุมัติจากแผนกของท่าน\n\n"
                            f"---\n"
                            f"รายละเอียดคำขอ:\n"
                            f"  รหัสคำขอ: {leave_request.request_id}\n"
                            f"  พนักงาน: {leave_request.employee.name}\n"
                            f"  วันที่: {leave_request.leave_date.strftime('%d/%m/%Y')}\n"
                            f"  ระยะเวลา: {leave_request.get_leave_duration_display()}\n"
                            f"  เหตุผล: {leave_request.reason}\n"
                            f"---"
                        )
                        send_notification_line(line_message, approver)
                        # -----------------
                else:
                    leave_request.status = "Rejected"
                    leave_request.current_approver_role = "completed"
                    messages.error(request, "ไม่พบตำแหน่ง HR หรือ Safety คำขอจึงถูกยกเลิก")

            elif history.approval_order == 3:  # HR or Safety
                leave_request.status = "Approved"
                leave_request.current_approver_role = "completed"
                ApprovalHistory.objects.filter(
                    request=leave_request, status="Pending"
                ).delete()
                messages.success(
                    request,
                    f"การอนุมัติสำหรับคำขอ ID: {leave_request.request_id} เสร็จสมบูรณ์",
                )
                send_notification_email(
                    subject=f"คำขอ [{leave_request.request_id}] ของคุณได้รับการอนุมัติแล้ว",
                    message_body="ยินดีด้วย! คำขอออกนอกสถานที่ของคุณได้รับการอนุมัติอย่างสมบูรณ์แล้ว",
                    recipient=leave_request.employee,
                    request_obj=leave_request,
                )
                # --- Send Line ---
                line_message = (
                    f"สวัสดีคุณ {leave_request.employee.name}\n\n"
                    f"ยินดีด้วย! คำขอออกนอกสถานที่ของคุณได้รับการอนุมัติแล้ว\n\n"
                    f"---\n"
                    f"รายละเอียดคำขอ:\n"
                    f"  รหัสคำขอ: {leave_request.request_id}\n"
                    f"  วันที่: {leave_request.leave_date.strftime('%d/%m/%Y')}\n"
                    f"  ระยะเวลา: {leave_request.get_leave_duration_display()}\n"
                    f"---"
                )
                send_notification_line(line_message, leave_request.employee)
                # -----------------

        elif decision == "reject":
            history.status = "Rejected"
            leave_request.status = "Rejected"
            leave_request.current_approver_role = "completed"
            messages.warning(request, f"คุณได้ปฏิเสธคำขอ ID: {leave_request.request_id}")
            email_message_body = f"คำขอออกนอกสถานที่ของคุณถูกปฏิเสธโดยผู้อนุมัติ เหตุผล: {comment}"
            send_notification_email(
                subject=f"คำขอ [{leave_request.request_id}] ของคุณถูกปฏิเสธ",
                message_body=email_message_body,
                recipient=leave_request.employee,
                request_obj=leave_request,
            )
            # --- Send Line ---
            line_message = (
                f"สวัสดีคุณ {leave_request.employee.name}\n\n"
                f"คำขอออกนอกสถานที่ของคุณถูกปฏิเสธ\n\n"
                f"---\n"
                f"รายละเอียดคำขอ:\n"
                f"  รหัสคำขอ: {leave_request.request_id}\n"
                f"  ผู้ปฏิเสธ: คุณ {history.approver.name}\n"
                f"  เหตุผล: {comment if comment else 'ไม่ได้ระบุ'}\n"
                f"---"
            )
            send_notification_line(line_message, leave_request.employee)
            # -----------------

        leave_request.save()
        history.save()
    return redirect("app:approval-inbox")

@login_required
def profile_edit_view(request):
    """
    View สำหรับให้พนักงานทั่วไปแก้ไขข้อมูลส่วนตัว (Email, Phone, Line ID)
    """
    try:
        # ดึง Employee object ของผู้ใช้ที่ล็อกอินอยู่
        employee = request.user.employee
    except Employee.DoesNotExist:
        messages.error(request, "ไม่พบโปรไฟล์พนักงานที่ผูกกับบัญชีของคุณ")
        return redirect("app:dashboard")

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "อัปเดตข้อมูลส่วนตัวเรียบร้อยแล้ว")
            return redirect("app:profile-edit")  # โหลดหน้าเดิม
        else:
            messages.error(request, "ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบและลองอีกครั้ง")
    else:
        # ส่ง instance ของ employee เข้าไป เพื่อให้ฟอร์มดึงข้อมูลปัจจุบันมาแสดง
        form = UserProfileForm(instance=employee)
    
    # Context ที่จำเป็นสำหรับ base.html (Navbar)
    # (จำเป็นต้องมีเพื่อให้เมนูแสดงผลถูกต้อง)
    try:
        is_approver = employee.role.role_name.lower() in ['manager', 'supervisor', 'hr', 'safety']
        approval_inbox_count = ApprovalHistory.objects.filter(approver=employee, status='Pending').count()
    except Exception:
        is_approver = False
        approval_inbox_count = 0

    context = {
        'form': form,
        'is_hr_or_admin': is_hr_or_admin(request.user),
        'is_security': is_security(request.user),
        'is_approver_or_admin': is_approver or is_hr_or_admin(request.user),
        'approval_inbox_count': approval_inbox_count,
    }
    return render(request, "app/profile_edit.html", context)

# ===== (เพิ่มใหม่) ส่วนของโปรไฟล์พนักงาน =====
@login_required
def profile_edit_view(request):
    """
    View สำหรับให้พนักงานทั่วไปแก้ไขข้อมูลส่วนตัว (Email, Phone, Line ID)
    """
    try:
        # ดึง Employee object ของผู้ใช้ที่ล็อกอินอยู่
        employee = request.user.employee
    except Employee.DoesNotExist:
        messages.error(request, "ไม่พบโปรไฟล์พนักงานที่ผูกกับบัญชีของคุณ")
        return redirect("app:dashboard")

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, "อัปเดตข้อมูลส่วนตัวเรียบร้อยแล้ว")
            return redirect("app:profile-edit")  # โหลดหน้าเดิม
        else:
            messages.error(request, "ข้อมูลไม่ถูกต้อง กรุณาตรวจสอบและลองอีกครั้ง")
    else:
        # ส่ง instance ของ employee เข้าไป เพื่อให้ฟอร์มดึงข้อมูลปัจจุบันมาแสดง
        form = UserProfileForm(instance=employee)
    
    # Context ที่จำเป็นสำหรับ base.html (Navbar)
    # (จำเป็นต้องมีเพื่อให้เมนูแสดงผลถูกต้อง)
    try:
        is_approver = employee.role.role_name.lower() in ['manager', 'supervisor', 'hr', 'safety']
        approval_inbox_count = ApprovalHistory.objects.filter(approver=employee, status='Pending').count()
    except Exception:
        is_approver = False
        approval_inbox_count = 0

    context = {
        'form': form,
        'is_hr_or_admin': is_hr_or_admin(request.user),
        'is_security': is_security(request.user),
        'is_approver_or_admin': is_approver or is_hr_or_admin(request.user),
        'approval_inbox_count': approval_inbox_count,
    }
    return render(request, "app/profile_edit.html", context)

# --- ส่วนของ รปภ. (Security Guard) ---
@login_required
@user_passes_test(is_security, login_url="/")
def security_dashboard(request):
    """
    View สำหรับ Security Dashboard
    (อัปเดต: เพิ่มการดึงข้อมูล Visitor Log)
    """
    today = timezone.now().date()

    recorded_request_ids = InOutHistory.objects.values_list("request_id", flat=True)
    ready_to_leave_requests = (
        LeaveRequest.objects.filter(leave_date=today, status="Approved")
        .exclude(request_id__in=recorded_request_ids)
        .order_by("employee__name")
    )

    already_out_list = InOutHistory.objects.filter(
        request__leave_date=today, status="OUT"
    ).order_by("time_out")

    # --- START: ส่วนที่เพิ่มเข้ามา ---
    # ดึงรายชื่อบุคคลภายนอกที่ยังอยู่ในพื้นที่ (ยังไม่ time_out)
    visitors_inside = VisitorLog.objects.filter(status="IN").order_by("-time_in")
    # --- END: ส่วนที่เพิ่มเข้ามา ---

    context = {
        "ready_to_leave_requests": ready_to_leave_requests,
        "already_out_list": already_out_list,
        "today_date": today,
        "is_security": True,
        "visitors_inside": visitors_inside,  # <-- ส่งข้อมูลใหม่ไปที่ Template
    }
    return render(request, "app/security_dashboard.html", context)


@login_required
@user_passes_test(is_security, login_url="/")
def record_time_out(request, request_id):
    if request.method == "POST":
        leave_request = get_object_or_404(LeaveRequest, request_id=request_id)
        InOutHistory.objects.create(
            request=leave_request,
            employee=leave_request.employee,
            guard=request.user.employee,
            time_out=timezone.now(),
            status="OUT",
        )
        messages.success(
            request, f'บันทึกเวลาออกสำหรับคุณ "{leave_request.employee.name}" เรียบร้อยแล้ว'
        )
    return redirect("app:security-dashboard")


# --- START: เพิ่ม 2 ฟังก์ชันใหม่สำหรับ Visitor Log ---


@login_required
@user_passes_test(is_security, login_url="/")
def visitor_log_in(request):
    """
    View สำหรับ รปภ. บันทึกข้อมูลบุคคลภายนอก (ขาเข้า)
    """
    if request.method == "POST":
        try:
            VisitorLog.objects.create(
                visitor_name=request.POST.get("visitor_name"),
                contact_person=request.POST.get("contact_person"),
                reason=request.POST.get("reason"),
                guard=request.user.employee,
                time_in=timezone.now(),
                status="IN",
            )
            messages.success(request, "บันทึกข้อมูลผู้มาติดต่อ (ขาเข้า) เรียบร้อยแล้ว")
        except Exception as e:
            messages.error(request, f"เกิดข้อผิดพลาดในการบันทึก: {e}")

    return redirect("app:security-dashboard")


@login_required
@user_passes_test(is_security, login_url="/")
def visitor_log_out(request, log_id):
    """
    View สำหรับ รปภ. บันทึกข้อมูลบุคคลภายนอก (ขาออก)
    """
    if request.method == "POST":
        try:
            visitor_log = get_object_or_404(VisitorLog, log_id=log_id)
            visitor_log.time_out = timezone.now()
            visitor_log.status = "OUT"
            visitor_log.save()
            messages.success(
                request, f'บันทึกเวลาออกสำหรับ "{visitor_log.visitor_name}" เรียบร้อยแล้ว'
            )
        except Exception as e:
            messages.error(request, f"เกิดข้อผิดพลาดในการบันทึก: {e}")

    return redirect("app:security-dashboard")


@login_required
@user_passes_test(is_security, login_url="/")
def record_time_in(request, history_id):
    if request.method == "POST":
        history = get_object_or_404(InOutHistory, history_id=history_id)
        history.time_in = timezone.now()
        history.status = "COMPLETED"

        if 'return_image' in request.FILES:
            history.return_image = request.FILES['return_image']

        history.save()
        messages.success(
            request, f'บันทึกเวลากลับเข้าสำหรับคุณ "{history.employee.name}" เรียบร้อยแล้ว'
        )
    return redirect("app:security-dashboard")

# --- ส่วนของรายงาน (HR/Admin) ---
@login_required
@user_passes_test(is_hr_or_admin, login_url="/")
def in_out_history_report(request):
    history_list = InOutHistory.objects.all().order_by("-time_out")
    search_query = request.GET.get("search_query", "")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")
    if search_query:
        history_list = history_list.filter(employee__name__icontains=search_query)
    if start_date:
        history_list = history_list.filter(time_out__date__gte=start_date)
    if end_date:
        history_list = history_list.filter(time_out__date__lte=end_date)
    context = {
        "history_list": history_list,
        "search_query": search_query,
        "start_date": start_date,
        "end_date": end_date,
        "is_hr_or_admin": True,
    }
    return render(request, "app/in_out_history_report.html", context)


@login_required
@user_passes_test(is_hr_or_admin, login_url="/")
def export_in_out_history_excel(request):
    history_list = InOutHistory.objects.all().order_by("-time_out")
    search_query = request.GET.get("search_query", "")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")

    if search_query:
        history_list = history_list.filter(employee__name__icontains=search_query)
    if start_date:
        history_list = history_list.filter(time_out__date__gte=start_date)
    if end_date:
        history_list = history_list.filter(time_out__date__lte=end_date)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "InOut History Report"

    headers = ["ชื่อพนักงาน", "แผนก", "วันที่", "เวลาออก", "เวลากลับ", "ผู้บันทึก (รปภ.)"]
    ws.append(headers)

    for history in history_list:
        time_in_str = (
            history.time_in.strftime("%H:%M:%S") if history.time_in else "ยังไม่กลับ"
        )
        row = [
            history.employee.name,
            history.employee.department.department_name,
            history.time_out.strftime("%d/%m/%Y"),
            history.time_out.strftime("%H:%M:%S"),
            time_in_str,
            history.guard.name,
        ]
        ws.append(row)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = (
        'attachment; filename="in_out_history_report.xlsx"'
    )
    wb.save(response)
    return response


# --- ส่วนของการจัดการพนักงาน (HR/Admin) ---


@login_required
@user_passes_test(is_hr_or_admin, login_url="/")
def employee_list_view(request):
    # --- START: ส่วนที่อัปเดต ---

    # 1. รับค่า GET parameters สำหรับการค้นหาและเรียงลำดับ
    search_query = request.GET.get("search_query", "")
    sort_by_param = request.GET.get("sort", "employee_id")  # ค่าเริ่มต้นเรียงตาม ID
    order_param = request.GET.get("order", "asc")  # ค่าเริ่มต้นเรียงจากน้อยไปมาก

    # 2. เริ่มต้น Queryset
    employees = Employee.objects.all()

    # 3. ใช้ Q object ในการกรองข้อมูล (ค้นหาจากหลาย field)
    if search_query:
        employees = employees.filter(
            Q(name__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(department__department_name__icontains=search_query)
            | Q(position__position_name__icontains=search_query)
        )

    # 4. กำหนดการเรียงลำดับ
    order_prefix = "-" if order_param == "desc" else ""
    employees = employees.order_by(f"{order_prefix}{sort_by_param}")

    # 5. ส่งค่ากลับไปที่ Template
    context = {
        "employees": employees,
        "search_query": search_query,
        "current_sort": sort_by_param,
        "current_order": order_param,
    }
    return render(request, "app/members_list.html", context)
    # --- END: ส่วนที่อัปเดต ---


@login_required
@user_passes_test(is_hr_or_admin, login_url='/')
def statistics_view(request):
    """
    View สำหรับแสดงผล Dashboard สรุปสถิติ (สำหรับ HR/Admin)
    """
    
    # --- START: เพิ่มโค้ดสำหรับ Navbar (ที่ขาดหายไป) ---
    # (จำเป็นต้องดึงข้อมูลเหล่านี้เพื่อให้เมนูใน base.html แสดงผลถูกต้อง)
    navbar_context = {}
    try:
        employee = request.user.employee
        pending_my_approval = ApprovalHistory.objects.filter(approver=employee, status='Pending')
        is_approver = employee.role.role_name.lower() in ['manager', 'supervisor', 'hr', 'safety']
        
        navbar_context = {
            'is_approver_or_admin': is_approver or is_hr_or_admin(request.user),
            'is_hr_or_admin': is_hr_or_admin(request.user),
            'is_security': is_security(request.user),
            'approval_inbox_count': pending_my_approval.count(),
        }
    except Employee.DoesNotExist:
        # กรณี Superuser ที่ไม่มีโปรไฟล์ Employee (แบบเดียวกับหน้า Dashboard)
        is_admin_or_superuser = request.user.is_superuser
        navbar_context = {
            'is_approver_or_admin': is_admin_or_superuser,
            'is_hr_or_admin': is_admin_or_superuser,
            'is_security': False,
            'approval_inbox_count': 0,
        }
    # --- END: เพิ่มโค้ดสำหรับ Navbar ---

    # 1. สถิติ: จำนวนคำขอแยกตามสถานะ (โค้ดเดิม)
    status_counts = LeaveRequest.objects.values('status') \
                                        .annotate(count=Count('status')) \
                                        .order_by('status')
    
    # 2. สถิติ: จำนวนคำขอแยกตามแผนก (โค้ดเดิม)
    department_counts = LeaveRequest.objects.values('employee__department__department_name') \
                                            .annotate(count=Count('request_id')) \
                                            .order_by('-count')

    # 3. สถิติ: จำนวนคำขอแยกตามระยะเวลา (โค้ดเดิม)
    duration_counts = LeaveRequest.objects.values('leave_duration') \
                                          .annotate(count=Count('leave_duration')) \
                                          .order_by('leave_duration')

    # 4. สถิติ: จำนวนคำขอรายเดือน (โค้ดเดิมที่แก้ไข Timezone แล้ว)
    requests_per_month = LeaveRequest.objects.annotate(
        request_date=Cast('request_datetime', output_field=DateField())
    ).annotate(
        month=TruncMonth('request_date')
    ).values('month') \
     .annotate(count=Count('request_id')) \
     .order_by('month')

    # 5. จัดเตรียมข้อมูลสำหรับ Chart.js (โค้ดเดิม)
    import json
    
    status_data = {
        'labels': [s['status'] for s in status_counts],
        'data': [s['count'] for s in status_counts],
    }
    
    department_data = {
        'labels': [d['employee__department__department_name'] for d in department_counts],
        'data': [d['count'] for d in department_counts],
    }
    
    duration_data = {
        'labels': [d['leave_duration'] for d in duration_counts],
        'data': [d['count'] for d in duration_counts],
    }

    month_labels = [m['month'].strftime('%Y-%m') for m in requests_per_month]
    month_data = [m['count'] for m in requests_per_month]

    context = {
        'status_data_json': json.dumps(status_data),
        'department_data_json': json.dumps(department_data),
        'duration_data_json': json.dumps(duration_data),
        'month_labels_json': json.dumps(month_labels),
        'month_data_json': json.dumps(month_data),
        'total_requests': LeaveRequest.objects.count(),
        'total_visitors': VisitorLog.objects.count(),
    }
    
    # --- START: เพิ่ม Navbar context เข้าไปใน context หลัก ---
    context.update(navbar_context)
    # --- END: เพิ่ม Navbar context ---
    
    return render(request, 'app/statistics.html', context)


@login_required
@user_passes_test(is_hr_or_admin, login_url="/")
def create_user_view(request):
    if request.method == "POST":
        form = EmployeeCreationForm(request.POST, request.FILES)
        if form.is_valid():
            employee = form.save()
            messages.success(request, f'สร้างพนักงาน "{employee.name}" เรียบร้อยแล้ว')
            return redirect("app:employee-list")
    else:
        form = EmployeeCreationForm()
    return render(request, "app/create_user.html", {"form": form})


@login_required
@user_passes_test(is_hr_or_admin, login_url="/")
def edit_employee_view(request, employee_id):
    employee = get_object_or_404(Employee, employee_id=employee_id)
    if request.method == "POST":
        form = EmployeeUpdateForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, f'อัปเดตข้อมูลของ "{employee.name}" เรียบร้อยแล้ว')
            return redirect("app:employee-list")
    else:
        form = EmployeeUpdateForm(instance=employee)
    return render(request, "app/edit_employee.html", {"form": form})


@login_required
@user_passes_test(is_hr_or_admin, login_url="/")
def delete_employee_view(request, employee_id):
    if request.method == "POST":
        employee = get_object_or_404(Employee, employee_id=employee_id)
        user_to_delete = employee.user
        employee_name = employee.name
        if request.user == user_to_delete:
            messages.error(request, "คุณไม่สามารถลบบัญชีของตัวเองได้")
            return redirect("app:employee-list")
        if user_to_delete.is_superuser:
            messages.error(request, "ไม่สามารถลบ Superuser ได้")
            return redirect("app:employee-list")
        user_to_delete.delete()
        messages.success(request, f'ลบพนักงาน "{employee_name}" ออกจากระบบเรียบร้อยแล้ว')
    return redirect("app:employee-list")


# --- ฟังก์ชันสำหรับทดสอบอีเมล ---
@login_required
@user_passes_test(is_superuser)  # จำกัดให้ Superuser เท่านั้นที่เข้าได้
def test_email_view(request, request_id):
    """
    View สำหรับทดสอบการแสดงผลของ Template อีเมล
    """
    leave_request = get_object_or_404(LeaveRequest, pk=request_id)
    # จำลองการส่งหา Manager
    recipient = Employee.objects.filter(
        department=leave_request.employee.department, role__role_name__iexact="Manager"
    ).first()

    context = {
        "recipient_name": recipient.name if recipient else "ไม่มีผู้รับ",
        "message_body": "นี่คือข้อความทดสอบสำหรับอีเมลแจ้งเตือน",
        "request_obj": leave_request,
    }
    return render(request, "app/test_email.html", context)


# ระบุตำแหน่งไฟล์ Config
CONFIG_FILE_PATH = os.path.join(settings.BASE_DIR, "site_config.json")


def get_config_data():
    """ฟังก์ชันช่วยอ่านค่าจาก JSON (ใช้ซ้ำได้)"""
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # ถ้าไฟล์ไม่มี หรือเสีย ให้ใช้ค่าเริ่มต้น
        return {
            "brand_name": "eLeave",
            "footer_text": "&copy; 2025 ระบบขออนุญาตออกนอกสถานที่",
            "color_primary": "#3498db",
            "color_success": "#198754",
            "color_warning": "#f39c12",
            "color_danger": "#e74c3c",
        }


@login_required
@user_passes_test(is_hr_or_admin, login_url="/")
def site_settings_view(request):
    if request.method == "POST":
        form = SiteConfigurationForm(request.POST)
        if form.is_valid():
            new_config = form.cleaned_data
            try:
                # เขียนข้อมูลใหม่ทับลงไฟล์ JSON
                with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                    json.dump(new_config, f, indent=4, ensure_ascii=False)
                messages.success(request, "บันทึกการตั้งค่าเว็บไซต์เรียบร้อยแล้ว")
            except IOError as e:
                messages.error(request, f"เกิดข้อผิดพลาดในการบันทึกไฟล์: {e}")
            return redirect("app:site-settings")
    else:
        # อ่านค่าปัจจุบันจากไฟล์มาแสดงในฟอร์ม
        current_config = get_config_data()
        form = SiteConfigurationForm(initial=current_config)

    context = {"form": form}
    return render(request, "app/site_settings.html", context)
