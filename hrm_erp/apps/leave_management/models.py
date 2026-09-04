from django.db import models
from django.conf import settings
from apps.employees.models import Employee


class LeaveType(models.Model):
    """Types of leave (e.g. Annual, Sick, Casual)."""
    name = models.CharField(max_length=100, unique=True)
    max_days_per_year = models.IntegerField(default=0)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'leave_types'
        ordering = ['name']

    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    """Employee leave requests with approval workflow."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves'
    )
    application_date = models.DateTimeField(auto_now_add=True)
    approved_date = models.DateTimeField(null=True, blank=True)
    manager_comment = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'leave_requests'
        ordering = ['-application_date']

    def __str__(self):
        return f"{self.employee} - {self.leave_type.name} ({self.status})"

    @property
    def total_days(self):
        """Calculate number of leave days."""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0
