# app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# ตารางที่ 3-8: แผนก (Departments)
class Department(models.Model):
    department_id = models.AutoField(primary_key=True)
    department_name = models.CharField(max_length=255)

    def __str__(self):
        return self.department_name

# ตารางที่ 3-9: ตำแหน่ง (Positions)
class Position(models.Model):
    position_id = models.AutoField(primary_key=True)
    position_name = models.CharField(max_length=255)
    # เราสามารถใช้ level ในการระบุลำดับขั้น เช่น 1=Manager, 2=Supervisor
    position_level = models.IntegerField() 

    def __str__(self):
        return self.position_name

# ตารางที่ 3-14: บทบาท (Roles)
class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    # ควรมี Role: Employee, Manager, Supervisor, HR, Safety
    role_name = models.CharField(max_length=255)

    def __str__(self):
        return self.role_name

# ตารางที่ 3-7: พนักงาน (Employees)
# ขยายความสามารถโดยการเชื่อมกับ User Model ของ Django
class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    employee_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, null=True, blank=True)
    email = models.CharField(max_length=255, null=True, blank=True)
    # ความสัมพันธ์ (Foreign Keys)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, db_column='department_id')
    position = models.ForeignKey(Position, on_delete=models.CASCADE, db_column='position_id')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, db_column='role_id')

    def __str__(self):
        return self.name

# ตารางที่ 3-10: คำขออนุญาต (เปลี่ยนจาก Complain)
class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'รออนุมัติ'),
        ('Approved', 'อนุมัติแล้ว'),
        ('Rejected', 'ถูกปฏิเสธ'),
    ]
    APPROVER_CHOICES = [
        ('manager', 'รออนุมัติจากผู้จัดการ'),
        ('supervisor', 'รออนุมัติจากหัวหน้างาน'),
        ('hr_safety', 'รออนุมัติจาก HR/Safety'),
        ('completed', 'เสร็จสิ้น'),
    ]
    DURATION_CHOICES = [
        ('3_hours', '3 ชั่วโมง'),
        ('half_day', 'ครึ่งวัน'),
        ('full_day', 'เต็มวัน'),
    ]

    request_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, db_column='employee_id')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    current_approver_role = models.CharField(max_length=20, choices=APPROVER_CHOICES, default='manager')
    reason = models.TextField(null=True, blank=True)
    
    # *** CHANGED: Replaced auto_now_add with default to fix migration issue ***
    request_datetime = models.DateTimeField(default=timezone.now)

    leave_date = models.DateField(default=timezone.now)
    leave_duration = models.CharField(max_length=10, choices=DURATION_CHOICES, default='3_hours')

    def __str__(self):
        return f"Request ID: {self.request_id} by {self.employee.name}"


# ตารางที่ 3-11: ประวัติการอนุมัติ
class ApprovalHistory(models.Model):
    STATUS_CHOICES = [
        ('Approved', 'อนุมัติ'),
        ('Rejected', 'ปฏิเสธ'),
        ('Pending', 'รอการดำเนินการ'),
    ]

    history_id = models.AutoField(primary_key=True)
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, db_column='request_id')
    approver = models.ForeignKey(Employee, on_delete=models.CASCADE, db_column='approver_id')
    approval_order = models.IntegerField() # ลำดับขั้น 1=Manager, 2=Supervisor, 3=HR/Safety
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    approval_date = models.DateField(null=True, blank=True)
    approval_time = models.TimeField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"History for Request ID: {self.request.request_id} by {self.approver.name}"

# (Optional) ตารางประวัติการเข้า-ออก
class InOutHistory(models.Model):
    history_id = models.AutoField(primary_key=True)
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, db_column='request_id')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_histories', db_column='employee_id')
    time_out = models.DateTimeField(null=True, blank=True)
    time_in = models.DateTimeField(null=True, blank=True)
    guard = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='guard_histories',
        db_column='guard_id',
        limit_choices_to={'role__role_name': 'Safety'} 
    )

    def __str__(self):
        return f"InOut for {self.employee.name} on request {self.request.request_id}"

