from django.contrib import admin
from .models import Attendance, AttendancePolicy


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'check_in', 'check_out', 'status', 'working_hours', 'hr_comment')
    search_fields = ('employee__first_name', 'employee__last_name')
    list_filter = ('status', 'date')


@admin.register(AttendancePolicy)
class AttendancePolicyAdmin(admin.ModelAdmin):
    list_display = ('title', 'work_start_time', 'work_end_time', 'grace_period_minutes', 'standard_working_hours', 'break_duration')
