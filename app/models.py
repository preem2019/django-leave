# app/models.py
from django.db import models

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
    position_level = models.IntegerField()

    def __str__(self):
        return self.position_name

# ตารางที่ 3-14: บทบาท (Roles)
class Role(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(max_length=255)

    def __str__(self):
        return self.role_name

# ตารางที่ 3-7: พนักงาน (Employees)
class Employee(models.Model):
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

# ตารางที่ 3-10: คำขออนุญาต (Complains/Requests)
class Complain(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    
    request_id = models.AutoField(primary_key=True)
    request_date = models.DateField()
    request_time = models.TimeField()
    reason = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    attachment = models.CharField(max_length=255, null=True, blank=True)
    # ความสัมพันธ์ (Foreign Key)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, db_column='employee_id')

    def __str__(self):
        return f"Request ID: {self.request_id} by {self.employee.name}"

# ตารางที่ 3-11: ประวัติการอนุมัติ (ApprovalHistories)
class ApprovalHistory(models.Model):
    STATUS_CHOICES = [
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Pending', 'Pending'),
    ]

    history_id = models.AutoField(primary_key=True)
    approval_order = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    approval_date = models.DateField(null=True, blank=True)
    approval_time = models.TimeField(null=True, blank=True)
    comment = models.TextField(null=True, blank=True)
    # ความสัมพันธ์ (Foreign Keys)
    request = models.ForeignKey(Complain, on_delete=models.CASCADE, db_column='request_id')
    approver = models.ForeignKey(Employee, on_delete=models.CASCADE, db_column='approver_id')

    def __str__(self):
        return f"History for Request ID: {self.request.request_id}"

# ตารางที่ 3-12: ประวัติการเข้า-ออก (InOutHistories)
class InOutHistory(models.Model):
    history_id = models.AutoField(primary_key=True)
    time_in = models.DateTimeField(null=True, blank=True)
    time_out = models.DateTimeField(null=True, blank=True)
    # ความสัมพันธ์ (Foreign Keys)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_histories', db_column='employee_id')
    request = models.ForeignKey(Complain, on_delete=models.CASCADE, db_column='request_id')
    # --- จุดที่เปลี่ยนแปลง ---
    # เปลี่ยน 'guard' ให้ชี้ไปที่ Employee และจำกัดให้เลือกได้เฉพาะคนที่มี Role ที่ต้องการ
    # (สมมติว่าคุณจะสร้าง Role ที่มีชื่อว่า 'Security Guard' ในฐานข้อมูล)
    guard = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='guard_histories',
        db_column='guard_id',
        limit_choices_to={'role__role_name': 'Security Guard'} # <-- จำกัดการเลือก
    )

    def __str__(self):
        return f"InOut for {self.employee.name} on {self.request.request_date}"

