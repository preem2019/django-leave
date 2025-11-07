# app/admin.py
from django.contrib import admin
from .models import Department, Position, Role, Employee, LeaveRequest, ApprovalHistory, InOutHistory

# 1. การตั้งค่าสำหรับโมเดลพื้นฐาน (ไม่มีการเปลี่ยนแปลง)
# --------------------------------------------
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('department_id', 'department_name')
    search_fields = ('department_name',)

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('position_id', 'position_name', 'position_level')
    search_fields = ('position_name',)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('role_id', 'role_name')
    search_fields = ('role_name',)


# 2. การตั้งค่าสำหรับโมเดล Employee (ปรับปรุง)
# --------------------------------------------
# Inline: แสดงคำขอของพนักงานในหน้า Employee
class LeaveRequestInline(admin.TabularInline):
    model = LeaveRequest
    extra = 0
    # *** CHANGED: Updated field names to match new model ***
    fields = ('leave_date', 'leave_duration', 'reason', 'status')
    readonly_fields = ('leave_date', 'leave_duration', 'reason', 'status')
    can_delete = False
    verbose_name = "ประวัติคำขอ"
    verbose_name_plural = "ประวัติคำขอทั้งหมด"


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'name', 'department', 'position', 'role', 'user') # Added 'user'
    list_filter = ('department', 'position', 'role')
    search_fields = ('name', 'email', 'phone', 'user__username') # Added search by username
    
    fieldsets = (
        # Added section to easily link user accounts
        ('บัญชีผู้ใช้ (สำหรับ Login)', {
            'fields': ('user',)
        }),
        ('ข้อมูลส่วนตัว', {
            'fields': ('name', 'phone', 'email')
        }),
        ('ข้อมูลการทำงาน', {
            'fields': ('department', 'position', 'role')
        }),
        
    )
    
    inlines = [LeaveRequestInline] # Use the updated inline class


# 3. การตั้งค่าสำหรับโมเดล LeaveRequest (ปรับปรุง)
# --------------------------------------------
# Inline: แสดงประวัติการอนุมัติในหน้า LeaveRequest
class ApprovalHistoryInline(admin.TabularInline):
    model = ApprovalHistory
    extra = 0
    # Make all fields readonly as they are system-generated
    readonly_fields = ('approver', 'approval_order', 'status', 'approval_date', 'approval_time', 'comment')
    can_delete = False


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    # *** CHANGED: Updated field names to match new model ***
    list_display = ('request_id', 'employee', 'leave_date', 'leave_duration', 'status')
    list_filter = ('status', 'leave_date', 'leave_duration')
    search_fields = ('employee__name', 'reason')
    
    fieldsets = (
        ('ข้อมูลคำขอ', {
            'fields': ('employee', 'leave_date', 'leave_duration', 'reason')
        }),
        ('สถานะและการอนุมัติ', {
            'fields': ('status', 'current_approver_role')
        }),
        ('ข้อมูลระบบ', {
            'fields': ('request_datetime',),
        })
    )
    
    readonly_fields = ('request_datetime',)
    inlines = [ApprovalHistoryInline]


# 4. การตั้งค่าสำหรับโมเดลประวัติ (ไม่มีการเปลี่ยนแปลง)
# --------------------------------------------
@admin.register(ApprovalHistory)
class ApprovalHistoryAdmin(admin.ModelAdmin):
    list_display = ('history_id', 'request', 'approver', 'status', 'approval_date')
    list_filter = ('status', 'approval_date')
    search_fields = ('request__employee__name', 'approver__name')

@admin.register(InOutHistory)
class InOutHistoryAdmin(admin.ModelAdmin):
    list_display = ('history_id', 'employee', 'time_in', 'time_out', 'guard')
    list_filter = ('time_in', 'time_out')
    search_fields = ('employee__name', 'guard__name')

