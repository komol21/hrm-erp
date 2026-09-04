from django.contrib import admin
from .models import LeaveType, LeaveRequest


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_days_per_year', 'description')
    search_fields = ('name',)


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status', 'application_date')
    search_fields = ('employee__first_name', 'employee__last_name')
    list_filter = ('status', 'leave_type')
