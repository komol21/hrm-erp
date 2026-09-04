from django.db import models
from apps.employees.models import Employee


class Payroll(models.Model):
    """Monthly payroll record per employee."""
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='payrolls'
    )
    month = models.CharField(
        max_length=7,
        help_text='Format: YYYY-MM (e.g. 2026-08)'
    )
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Auto-calculated: basic_salary + allowances - deductions'
    )
    payment_date = models.DateField(null=True, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    notes = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'payrolls'
        unique_together = ('employee', 'month')
        ordering = ['-month']

    def __str__(self):
        return f"{self.employee} - {self.month} ({self.payment_status})"

    def save(self, *args, **kwargs):
        """Auto-calculate net salary on save."""
        self.net_salary = self.basic_salary + self.allowances - self.deductions
        super().save(*args, **kwargs)
