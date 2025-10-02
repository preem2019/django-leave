# app/admin.py
from django.contrib import admin
from .models import Department, Position, Role, Employee, Complain, ApprovalHistory, InOutHistory

# 1. การตั้งค่าสำหรับโมเดลที่ไม่ซับซ้อน
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


# 2. การตั้งค่าสำหรับโมเดลหลัก (Employee)
# --------------------------------------------
# Inlines: แสดงข้อมูลที่เกี่ยวข้องในหน้า Employee
class ComplainInline(admin.TabularInline):
    model = Complain
    extra = 0  # ไม่แสดงฟอร์มเปล่าสำหรับเพิ่มข้อมูลใหม่
    fields = ('request_date', 'reason', 'status')
    readonly_fields = ('request_date', 'reason', 'status')
    can_delete = False

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'name', 'department', 'position', 'role')
    list_filter = ('department', 'position', 'role')
    search_fields = ('name', 'email', 'phone')
    
    # จัดกลุ่มฟิลด์ในหน้าแก้ไข
    fieldsets = (
        ('ข้อมูลส่วนตัว', {
            'fields': ('name', 'phone', 'email')
        }),
        ('ข้อมูลการทำงาน', {
            'fields': ('department', 'position', 'role')
        }),
    )
    
    # แสดงรายการคำขอของพนักงานคนนี้
    inlines = [ComplainInline]


# 3. การตั้งค่าสำหรับโมเดลคำขอ (Complain)
# --------------------------------------------
# Inlines: แสดงประวัติการอนุมัติในหน้า Complain
class ApprovalHistoryInline(admin.TabularInline):
    model = ApprovalHistory
    extra = 1

@admin.register(Complain)
class ComplainAdmin(admin.ModelAdmin):
    list_display = ('request_id', 'employee', 'request_date', 'status')
    list_filter = ('status', 'request_date')
    search_fields = ('employee__name', 'reason')
    
    fieldsets = (
        ('ข้อมูลคำขอ', {
            'fields': ('employee', 'request_date', 'request_time', 'reason', 'attachment')
        }),
        ('สถานะ', {
            'fields': ('status',)
        }),
    )
    
    # แสดงประวัติการอนุมัติของคำขอนี้
    inlines = [ApprovalHistoryInline]


# 4. การตั้งค่าสำหรับโมเดลประวัติ (Histories)
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