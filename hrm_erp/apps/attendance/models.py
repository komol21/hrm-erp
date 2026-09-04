from django.db import models
from apps.employees.models import Employee


class AttendancePolicy(models.Model):
    """Configurable attendance policy rules (Admin & HR managed)."""
    title = models.CharField(max_length=150, default="Standard Company Attendance Policy")
    work_start_time = models.TimeField(default="09:00:00", help_text="Standard office start time")
    work_end_time = models.TimeField(default="17:00:00", help_text="Standard office end time")
    grace_period_minutes = models.IntegerField(default=15, help_text="Grace period before marked as late (minutes)")
    standard_working_hours = models.DecimalField(max_digits=4, decimal_places=2, default=8.0, help_text="Standard required working hours per day")
    overtime_threshold_hours = models.DecimalField(max_digits=4, decimal_places=2, default=8.0, help_text="Working hours threshold after which overtime is counted")
    break_duration = models.IntegerField(default=60, help_text="Break duration in minutes")
    require_location = models.BooleanField(default=False, help_text="Require IP or location check-in")
    notes = models.TextField(blank=True, default="Standard working policy applied across all branches.")

    class Meta:
        db_table = 'attendance_policies'

    def __str__(self):
        return self.title

    @classmethod
    def get_active_policy(cls):
        """Return the active attendance policy, creating a default one if needed."""
        policy, _ = cls.objects.get_or_create(
            id=1,
            defaults={'title': 'Standard Company Attendance Policy'}
        )
        return policy


class Attendance(models.Model):
    """Daily attendance record per employee."""
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('on_leave', 'On Leave'),
        ('early_leave', 'Early Leave'),
        ('incomplete', 'Incomplete'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='present'
    )
    working_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Calculated from check-in and check-out times'
    )
    late_minutes = models.IntegerField(
        default=0,
        help_text='Minutes late beyond scheduled start'
    )
    overtime_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Hours worked beyond standard workday'
    )
    notes = models.TextField(blank=True, default='')
    hr_comment = models.TextField(
        blank=True,
        default='',
        help_text='HR remark — visible to the employee but only editable by HR/Admin'
    )

    class Meta:
        db_table = 'attendances'
        unique_together = ('employee', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} - {self.date} ({self.status})"

    def calculate_working_hours(self):
        """Calculate working hours from check-in and check-out times."""
        if self.check_in and self.check_out:
            from datetime import datetime, timedelta
            check_in_dt = datetime.combine(self.date, self.check_in)
            check_out_dt = datetime.combine(self.date, self.check_out)
            if check_out_dt < check_in_dt:
                check_out_dt += timedelta(days=1)
            diff = check_out_dt - check_in_dt
            hours = diff.total_seconds() / 3600
            return round(hours, 2)
        return 0

    def save(self, *args, **kwargs):
        """Auto-calculate working hours and overtime using AttendancePolicy."""
        self.working_hours = self.calculate_working_hours()

        # Use policy for overtime threshold
        try:
            policy = AttendancePolicy.get_active_policy()
            overtime_threshold = float(policy.overtime_threshold_hours)
        except Exception:
            overtime_threshold = 8.0

        if self.working_hours > overtime_threshold:
            self.overtime_hours = round(float(self.working_hours) - overtime_threshold, 2)
        else:
            self.overtime_hours = 0

        # Auto-set incomplete only for past dates when check_in exists but no check_out.
        # For today, employees actively working should retain their 'present' or 'late' status.
        from django.utils import timezone
        today = timezone.localdate()
        if self.date:
            if self.date < today and self.check_in and not self.check_out and self.status not in ('absent', 'on_leave'):
                self.status = 'incomplete'
            elif self.date == today and self.status == 'incomplete' and self.check_in:
                self.status = 'late' if (self.late_minutes and self.late_minutes > 0) else 'present'

        super().save(*args, **kwargs)
