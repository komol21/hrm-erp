from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import LeaveType, LeaveRequest
from .forms import LeaveTypeForm, LeaveRequestForm, LeaveReviewForm
from apps.accounts.permissions import hr_required, role_required


# ─── Leave Types (Read: All Users, Modify: HR/Admin) ─────────────────────────

@login_required
@role_required('Admin', 'HR', 'Employee')
def leave_type_list(request):
    """List all leave types."""
    types = LeaveType.objects.all()
    return render(request, 'leave_management/type_list.html', {
        'types': types,
        'page_title': 'Leave Types',
    })


@login_required
@hr_required
def leave_type_create(request):
    """Create new leave type (Admin/HR only)."""
    if request.method == 'POST':
        form = LeaveTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Leave type created successfully.')
            return redirect('leave:type_list')
    else:
        form = LeaveTypeForm()
    return render(request, 'leave_management/type_form.html', {
        'form': form,
        'page_title': 'Create Leave Type',
        'is_edit': False,
    })


@login_required
@hr_required
def leave_type_edit(request, pk):
    """Edit leave type (Admin/HR only)."""
    ltype = get_object_or_404(LeaveType, pk=pk)
    if request.method == 'POST':
        form = LeaveTypeForm(request.POST, instance=ltype)
        if form.is_valid():
            form.save()
            messages.success(request, 'Leave type updated successfully.')
            return redirect('leave:type_list')
    else:
        form = LeaveTypeForm(instance=ltype)
    return render(request, 'leave_management/type_form.html', {
        'form': form,
        'page_title': f'Edit Leave Type: {ltype.name}',
        'is_edit': True,
    })


@login_required
@hr_required
def leave_type_delete(request, pk):
    """Delete leave type (Admin/HR only)."""
    ltype = get_object_or_404(LeaveType, pk=pk)
    if request.method == 'POST':
        ltype.delete()
        messages.success(request, 'Leave type deleted successfully.')
        return redirect('leave:type_list')
    return render(request, 'components/confirm_delete.html', {
        'object': ltype,
        'object_name': ltype.name,
        'page_title': f'Delete Leave Type: {ltype.name}',
        'cancel_url': 'leave:type_list',
    })


# ─── Leave Requests ───────────────────────────────────────────────────────────

@login_required
@role_required('Admin', 'HR', 'Employee')
def leave_request_list(request):
    """List leave requests. Admin/HR sees all; Employee is redirected or blocked (sees own via my_leaves)."""
    if request.user.is_employee_role() and not request.user.is_admin() and not request.user.is_hr():
        return redirect('leave:my_leaves')

    status_filter = request.GET.get('status', '')
    employee_search = request.GET.get('search', '')

    requests_qs = LeaveRequest.objects.select_related('employee', 'leave_type').all()

    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)
    if employee_search:
        requests_qs = requests_qs.filter(
            employee__first_name__icontains=employee_search
        ) | requests_qs.filter(
            employee__last_name__icontains=employee_search
        )

    paginator = Paginator(requests_qs, 15)
    page = request.GET.get('page')
    requests_page = paginator.get_page(page)

    return render(request, 'leave_management/request_list.html', {
        'requests': requests_page,
        'selected_status': status_filter,
        'search': employee_search,
        'status_choices': LeaveRequest.STATUS_CHOICES,
        'page_title': 'Leave Requests',
    })


@login_required
@role_required('Admin', 'HR', 'Employee')
def leave_request_create(request):
    """Submit a leave request (Employee self-service / HR)."""
    employee = request.user.get_employee()
    if not employee:
        messages.warning(request, 'No employee profile linked to your account. Cannot request leave.')
        return redirect('dashboard:redirect')

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            lreq = form.save(commit=False)
            lreq.employee = employee
            lreq.status = 'pending'
            lreq.save()
            messages.success(request, 'Leave request submitted successfully.')
            return redirect('leave:my_leaves')
    else:
        form = LeaveRequestForm()
    return render(request, 'leave_management/request_form.html', {
        'form': form,
        'page_title': 'Apply for Leave',
    })


@login_required
@role_required('Admin', 'HR', 'Employee')
def leave_request_detail(request, pk):
    """Detail view of a leave request."""
    lreq = get_object_or_404(LeaveRequest.objects.select_related('employee', 'leave_type', 'approved_by'), pk=pk)

    # Data isolation
    if request.user.is_employee_role() and not request.user.is_admin() and not request.user.is_hr():
        if lreq.employee != request.user.get_employee():
            raise PermissionDenied

    return render(request, 'leave_management/request_detail.html', {
        'request_item': lreq,
        'page_title': f'Leave Request: {lreq.employee.full_name}',
    })


@login_required
@hr_required
def leave_request_review(request, pk):
    """Approve/reject leave request (Admin/HR)."""
    lreq = get_object_or_404(LeaveRequest.objects.select_related('employee', 'leave_type'), pk=pk)

    if request.method == 'POST':
        form = LeaveReviewForm(request.POST, instance=lreq)
        if form.is_valid():
            lreq = form.save(commit=False)
            lreq.approved_by = request.user
            lreq.approved_date = timezone.now()
            lreq.save()
            messages.success(request, f'Leave request for {lreq.employee.full_name} has been {lreq.status}.')
            return redirect('leave:request_list')
    else:
        form = LeaveReviewForm(instance=lreq)

    return render(request, 'leave_management/request_review.html', {
        'form': form,
        'request_item': lreq,
        'page_title': f'Review Leave Request: {lreq.employee.full_name}',
    })


@login_required
@role_required('Admin', 'HR', 'Employee')
def my_leaves(request):
    """View own leave request history (Employee self-service)."""
    employee = request.user.get_employee()
    if not employee:
        messages.warning(request, 'No employee profile linked to your account.')
        return redirect('dashboard:redirect')

    requests_qs = LeaveRequest.objects.filter(employee=employee).select_related('leave_type').order_by('-application_date')

    paginator = Paginator(requests_qs, 10)
    page = request.GET.get('page')
    requests_page = paginator.get_page(page)

    return render(request, 'leave_management/my_leaves.html', {
        'requests': requests_page,
        'page_title': 'My Leave History',
    })
