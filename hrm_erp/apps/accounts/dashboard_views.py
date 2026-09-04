"""Dashboard views — route to role-specific dashboards with live DB stats."""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Sum, Q
from datetime import date

from apps.employees.models import Employee
from apps.organization.models import Department, Branch
from apps.attendance.models import Attendance
from apps.leave_management.models import LeaveRequest
from apps.payroll.models import Payroll
from .permissions import role_required


@login_required
def dashboard_redirect(request):
    """Redirect user to the appropriate role-based dashboard."""
    if request.user.has_role('Admin'):
        return redirect('dashboard:admin')
    elif request.user.has_role('HR'):
        return redirect('dashboard:hr')
    elif request.user.has_role('Employee'):
        return redirect('dashboard:employee')
    else:
        return redirect('accounts:login')


from django.http import JsonResponse


def get_today_attendance_stats():
    """Calculate accurate real-time attendance counts for today."""
    today = timezone.localdate()
    active_employees = Employee.objects.filter(status='active')
    total_active = active_employees.count()

    # Employees on approved leave covering today
    leave_employee_ids = set(
        LeaveRequest.objects.filter(
            status='approved',
            start_date__lte=today,
            end_date__gte=today
        ).values_list('employee_id', flat=True)
    )
    # Explicit on_leave attendance records
    att_on_leave_ids = set(
        Attendance.objects.filter(date=today, status='on_leave').values_list('employee_id', flat=True)
    )
    all_on_leave_ids = leave_employee_ids | att_on_leave_ids
    today_on_leave = len(all_on_leave_ids)

    # Today's attendances
    today_records = Attendance.objects.filter(date=today)

    # Late arrivals: explicit late status or recorded late minutes
    today_late = today_records.filter(
        Q(status='late') | Q(late_minutes__gt=0)
    ).count()

    # Present: on time (present, early_leave, or active check_in without late minutes)
    today_present = today_records.filter(
        Q(status__in=['present', 'early_leave']) | Q(status='incomplete', check_in__isnull=False)
    ).exclude(Q(status='late') | Q(late_minutes__gt=0)).count()

    # Active employees who checked in today
    attended_employee_ids = set(
        today_records.filter(check_in__isnull=False).values_list('employee_id', flat=True)
    )

    # Absent: active employees who have neither checked in nor are on approved leave
    unaccounted_absent = max(0, total_active - len(attended_employee_ids | all_on_leave_ids))
    explicit_absent = today_records.filter(status='absent').count()
    today_absent = max(unaccounted_absent, explicit_absent)

    return {
        'today_present': today_present,
        'today_late': today_late,
        'today_absent': today_absent,
        'today_on_leave': today_on_leave,
        'total_active': total_active,
    }


@login_required
@role_required('Admin', 'HR')
def attendance_realtime_api(request):
    """Real-time JSON endpoint for live dashboard attendance polling."""
    return JsonResponse(get_today_attendance_stats())


@login_required
@role_required('Admin')
def admin_dashboard(request):
    """Admin dashboard — system-wide stats."""
    today = timezone.localdate()
    current_month = today.strftime('%Y-%m')
    att_stats = get_today_attendance_stats()

    context = {
        'page_title': 'Admin Dashboard',
        'total_employees': Employee.objects.filter(status='active').count(),
        'total_departments': Department.objects.count(),
        'total_branches': Branch.objects.count(),
        # Today's attendance (real-time)
        'today_present': att_stats['today_present'],
        'today_absent': att_stats['today_absent'],
        'today_late': att_stats['today_late'],
        'today_on_leave': att_stats['today_on_leave'],
        # Leave
        'pending_leaves': LeaveRequest.objects.filter(status='pending').count(),
        # Payroll
        'monthly_payroll_total': Payroll.objects.filter(month=current_month).aggregate(
            total=Sum('net_salary')
        )['total'] or 0,
        'pending_payrolls': Payroll.objects.filter(payment_status='pending').count(),
        # Recent leave requests
        'recent_leaves': LeaveRequest.objects.select_related(
            'employee', 'leave_type'
        ).order_by('-application_date')[:5],
        # Recent employees
        'recent_employees': Employee.objects.order_by('-hire_date')[:5],
        # Employees by department
        'dept_distribution': Department.objects.annotate(
            emp_count=Count('employees')
        ).filter(emp_count__gt=0).order_by('-emp_count')[:6],
    }
    return render(request, 'dashboard/admin.html', context)


@login_required
@role_required('HR')
def hr_dashboard(request):
    """HR dashboard — HR-wide stats."""
    today = timezone.localdate()
    current_month = today.strftime('%Y-%m')
    att_stats = get_today_attendance_stats()

    context = {
        'page_title': 'HR Dashboard',
        'total_employees': Employee.objects.filter(status='active').count(),
        'total_departments': Department.objects.count(),
        # Today's attendance (real-time)
        'today_present': att_stats['today_present'],
        'today_absent': att_stats['today_absent'],
        'today_late': att_stats['today_late'],
        'today_on_leave': att_stats['today_on_leave'],
        # Leave
        'pending_leaves': LeaveRequest.objects.filter(status='pending').count(),
        'recent_leaves': LeaveRequest.objects.select_related(
            'employee', 'leave_type'
        ).filter(status='pending').order_by('-application_date')[:5],
        # Payroll
        'monthly_payroll_total': Payroll.objects.filter(month=current_month).aggregate(
            total=Sum('net_salary')
        )['total'] or 0,
        # Employee status breakdown
        'active_employees': Employee.objects.filter(status='active').count(),
        'inactive_employees': Employee.objects.filter(status='inactive').count(),
        'terminated_employees': Employee.objects.filter(status='terminated').count(),
        # Department distribution
        'dept_distribution': Department.objects.annotate(
            emp_count=Count('employees')
        ).filter(emp_count__gt=0).order_by('-emp_count')[:6],
    }
    return render(request, 'dashboard/hr.html', context)


@login_required
@role_required('Employee')
def employee_dashboard(request):
    """Employee dashboard — own data only."""
    today = date.today()
    current_month = today.strftime('%Y-%m')
    employee = request.user.get_employee()

    context = {
        'page_title': 'Employee Dashboard',
        'employee': employee,
    }

    if employee:
        # Attendance this month
        month_attendance = Attendance.objects.filter(
            employee=employee,
            date__year=today.year,
            date__month=today.month
        )
        context.update({
            'month_present': month_attendance.filter(status='present').count(),
            'month_absent': month_attendance.filter(status='absent').count(),
            'month_late': month_attendance.filter(status='late').count(),
            'month_on_leave': month_attendance.filter(status='on_leave').count(),
            # Today's attendance
            'today_attendance': Attendance.objects.filter(
                employee=employee, date=today
            ).first(),
            # Leave requests
            'pending_leaves': LeaveRequest.objects.filter(
                employee=employee, status='pending'
            ).count(),
            'recent_leaves': LeaveRequest.objects.filter(
                employee=employee
            ).select_related('leave_type').order_by('-application_date')[:5],
            # Latest payslip
            'latest_payslip': Payroll.objects.filter(
                employee=employee
            ).order_by('-month').first(),
        })

    return render(request, 'dashboard/employee.html', context)
