from datetime import date, datetime, time, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import Attendance, AttendancePolicy
from .forms import AttendanceForm, HRCommentForm
from apps.accounts.permissions import hr_required, role_required
from apps.organization.models import Department


@login_required
@hr_required
def attendance_list(request):
    """List all attendance records (Admin/HR)."""
    search = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    status_filter = request.GET.get('status', '')
    department_filter = request.GET.get('department', '')

    records = Attendance.objects.select_related('employee', 'employee__department').all()

    if search:
        records = records.filter(
            employee__first_name__icontains=search
        ) | records.filter(
            employee__last_name__icontains=search
        )
    if date_from:
        records = records.filter(date__gte=date_from)
    if date_to:
        records = records.filter(date__lte=date_to)
    if status_filter:
        records = records.filter(status=status_filter)
    if department_filter:
        records = records.filter(employee__department_id=department_filter)

    paginator = Paginator(records, 15)
    page = request.GET.get('page')
    records = paginator.get_page(page)

    return render(request, 'attendance/attendance_list.html', {
        'records': records,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
        'selected_status': status_filter,
        'selected_department': department_filter,
        'status_choices': Attendance.STATUS_CHOICES,
        'departments': Department.objects.all(),
        'page_title': 'Attendance Records',
    })


@login_required
@hr_required
def attendance_create(request):
    """Create attendance record (Admin/HR)."""
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance record created successfully.')
            return redirect('attendance:attendance_list')
    else:
        form = AttendanceForm()
    return render(request, 'attendance/attendance_form.html', {
        'form': form,
        'page_title': 'Create Attendance Record',
        'is_edit': False,
    })


@login_required
@hr_required
def attendance_edit(request, pk):
    """Edit attendance record (Admin/HR)."""
    record = get_object_or_404(Attendance, pk=pk)
    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance record updated successfully.')
            return redirect('attendance:attendance_list')
    else:
        form = AttendanceForm(instance=record)
    return render(request, 'attendance/attendance_form.html', {
        'form': form,
        'page_title': 'Edit Attendance Record',
        'is_edit': True,
    })


@login_required
@hr_required
def attendance_delete(request, pk):
    """Delete attendance record (Admin/HR)."""
    record = get_object_or_404(Attendance, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, 'Attendance record deleted successfully.')
        return redirect('attendance:attendance_list')
    return render(request, 'components/confirm_delete.html', {
        'object': record,
        'object_name': f'{record.employee} - {record.date}',
        'page_title': 'Delete Attendance Record',
        'cancel_url': 'attendance:attendance_list',
    })


@login_required
@hr_required
def hr_add_comment(request, pk):
    """HR/Admin can add or update a comment on an attendance record."""
    record = get_object_or_404(
        Attendance.objects.select_related('employee'),
        pk=pk
    )
    if request.method == 'POST':
        form = HRCommentForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, f'Comment saved for {record.employee.full_name} ({record.date}).')
            return redirect('attendance:attendance_list')
    else:
        form = HRCommentForm(instance=record)

    return render(request, 'attendance/hr_comment_form.html', {
        'form': form,
        'record': record,
        'page_title': 'HR Comment',
    })


def _get_policy():
    """Helper: return the active AttendancePolicy."""
    return AttendancePolicy.get_active_policy()


@login_required
@role_required('Admin', 'HR', 'Employee')
def check_in(request):
    """Employee self-service check-in."""
    employee = request.user.get_employee()
    if not employee:
        messages.warning(request, 'No employee profile linked to your account.')
        return redirect('dashboard:redirect')

    today = timezone.localdate()
    existing = Attendance.objects.filter(employee=employee, date=today).first()

    if existing and existing.check_in:
        messages.info(request, 'You have already checked in today.')
        return redirect('attendance:my_attendance')

    if request.method == 'POST':
        now = timezone.localtime().time()
        policy = _get_policy()

        # Determine late threshold from policy
        start_time = policy.work_start_time
        grace = policy.grace_period_minutes
        late_threshold_dt = datetime.combine(today, start_time) + timedelta(minutes=grace)
        late_threshold = late_threshold_dt.time()

        if existing:
            existing.check_in = now
            existing.status = 'present'
            if now > late_threshold:
                existing.status = 'late'
                delta = datetime.combine(today, now) - datetime.combine(today, start_time)
                existing.late_minutes = int(delta.total_seconds() / 60)
            existing.save()
        else:
            status = 'present'
            late_minutes = 0
            if now > late_threshold:
                status = 'late'
                delta = datetime.combine(today, now) - datetime.combine(today, start_time)
                late_minutes = int(delta.total_seconds() / 60)
            Attendance.objects.create(
                employee=employee,
                date=today,
                check_in=now,
                status=status,
                late_minutes=late_minutes,
            )
        messages.success(request, f'Checked in at {now.strftime("%I:%M %p")}.')
        return redirect('attendance:my_attendance')

    return render(request, 'attendance/checkin.html', {
        'page_title': 'Check In',
        'action': 'check_in',
        'today': today,
        'existing': existing,
    })


@login_required
@role_required('Admin', 'HR', 'Employee')
def check_out(request):
    """Employee self-service check-out."""
    employee = request.user.get_employee()
    if not employee:
        messages.warning(request, 'No employee profile linked to your account.')
        return redirect('dashboard:redirect')

    today = timezone.localdate()
    existing = Attendance.objects.filter(employee=employee, date=today).first()

    if not existing or not existing.check_in:
        messages.warning(request, 'You need to check in first.')
        return redirect('attendance:check_in')

    if existing.check_out:
        messages.info(request, 'You have already checked out today.')
        return redirect('attendance:my_attendance')

    if request.method == 'POST':
        now = timezone.localtime().time()
        policy = _get_policy()

        existing.check_out = now

        # Detect early leave — checked out before policy end time
        if now < policy.work_end_time and existing.status != 'late':
            existing.status = 'early_leave'
        elif existing.status in ('incomplete', 'early_leave') and now >= policy.work_end_time:
            # Revert to present/late if worked full schedule
            if existing.late_minutes > 0:
                existing.status = 'late'
            else:
                existing.status = 'present'

        existing.save()  # Triggers working_hours + overtime calculation
        messages.success(
            request,
            f'Checked out at {now.strftime("%I:%M %p")}. Working hours: {existing.working_hours}h'
        )
        return redirect('attendance:my_attendance')

    return render(request, 'attendance/checkin.html', {
        'page_title': 'Check Out',
        'action': 'check_out',
        'today': today,
        'existing': existing,
    })


@login_required
@role_required('Admin', 'HR', 'Employee')
def my_attendance(request):
    """Employee self-service: view own attendance records."""
    employee = request.user.get_employee()
    if not employee:
        messages.warning(request, 'No employee profile linked to your account.')
        return redirect('dashboard:redirect')

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    records = Attendance.objects.filter(employee=employee)

    if date_from:
        records = records.filter(date__gte=date_from)
    if date_to:
        records = records.filter(date__lte=date_to)

    # Today's record
    today_record = Attendance.objects.filter(employee=employee, date=date.today()).first()

    paginator = Paginator(records, 15)
    page = request.GET.get('page')
    records = paginator.get_page(page)

    return render(request, 'attendance/my_attendance.html', {
        'records': records,
        'today_record': today_record,
        'date_from': date_from,
        'date_to': date_to,
        'page_title': 'My Attendance',
    })


# ─── Attendance Policy Management (Admin & HR) ───────────────────────────────

@login_required
@role_required('Admin', 'HR', 'Employee')
def attendance_policy_detail(request):
    """View attendance policy. Employees can view read-only rules."""
    policy = AttendancePolicy.get_active_policy()
    return render(request, 'attendance/policy_detail.html', {
        'policy': policy,
        'is_hr_or_admin': request.user.is_admin() or request.user.is_hr(),
        'page_title': 'Attendance Policy',
    })


@login_required
@hr_required
def attendance_policy_edit(request):
    """Configure/update attendance policy (Admin & HR only)."""
    from .forms import AttendancePolicyForm
    policy = AttendancePolicy.get_active_policy()

    if request.method == 'POST':
        form = AttendancePolicyForm(request.POST, instance=policy)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance policy updated successfully.')
            return redirect('attendance:attendance_policy_detail')
    else:
        form = AttendancePolicyForm(instance=policy)

    return render(request, 'attendance/policy_form.html', {
        'form': form,
        'policy': policy,
        'page_title': 'Configure Attendance Policy',
    })
