from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from .models import Payroll
from .forms import PayrollForm
from apps.accounts.permissions import hr_required, role_required


@login_required
@hr_required
def payroll_list(request):
    """List all payrolls (Admin/HR)."""
    search = request.GET.get('search', '')
    month_filter = request.GET.get('month', '')
    status_filter = request.GET.get('status', '')

    payrolls = Payroll.objects.select_related('employee').all()

    if search:
        payrolls = payrolls.filter(
            employee__first_name__icontains=search
        ) | payrolls.filter(
            employee__last_name__icontains=search
        )
    if month_filter:
        payrolls = payrolls.filter(month=month_filter)
    if status_filter:
        payrolls = payrolls.filter(payment_status=status_filter)

    paginator = Paginator(payrolls, 15)
    page = request.GET.get('page')
    payrolls_page = paginator.get_page(page)

    return render(request, 'payroll/payroll_list.html', {
        'payrolls': payrolls_page,
        'search': search,
        'selected_month': month_filter,
        'selected_status': status_filter,
        'status_choices': Payroll.PAYMENT_STATUS_CHOICES,
        'page_title': 'Payroll Management',
    })


@login_required
@hr_required
def payroll_create(request):
    """Create a new payroll record (Admin/HR)."""
    # If HR attempts to pass their own employee ID via GET parameter, block and inform them.
    employee_id = request.GET.get('employee')
    if employee_id and request.user.is_hr() and not request.user.is_admin():
        hr_employee = request.user.get_employee()
        if hr_employee and str(hr_employee.id) == str(employee_id):
            messages.error(request, 'HR managers cannot generate their own payment slip.')
            return redirect('payroll:payroll_list')

    if request.method == 'POST':
        form = PayrollForm(request.POST, user=request.user)
        if form.is_valid():
            payroll = form.save()
            messages.success(request, f'Payroll record created successfully for {payroll.employee.full_name}.')
            return redirect('payroll:payroll_list')
    else:
        # Pre-fill basic salary if employee selected in query params
        initial = {}
        if employee_id:
            from apps.employees.models import Employee
            emp = get_object_or_404(Employee, pk=employee_id)
            initial['employee'] = emp.id
            initial['basic_salary'] = emp.basic_salary
        form = PayrollForm(initial=initial, user=request.user)

    return render(request, 'payroll/payroll_form.html', {
        'form': form,
        'page_title': 'Create Payroll Record',
        'is_edit': False,
    })


@login_required
@hr_required
def payroll_edit(request, pk):
    """Edit payroll record (Admin/HR)."""
    payroll = get_object_or_404(Payroll, pk=pk)

    # Prevent HR from editing their own payroll record
    if request.user.is_hr() and not request.user.is_admin():
        hr_employee = request.user.get_employee()
        if hr_employee and payroll.employee == hr_employee:
            messages.error(request, 'HR managers cannot edit their own payroll record.')
            raise PermissionDenied

    if request.method == 'POST':
        form = PayrollForm(request.POST, instance=payroll, user=request.user)
        if form.is_valid():
            payroll = form.save()
            messages.success(request, f'Payroll record updated successfully for {payroll.employee.full_name}.')
            return redirect('payroll:payroll_list')
    else:
        form = PayrollForm(instance=payroll, user=request.user)
    return render(request, 'payroll/payroll_form.html', {
        'form': form,
        'page_title': f'Edit Payroll: {payroll.employee.full_name} ({payroll.month})',
        'is_edit': True,
    })


@login_required
@hr_required
def payroll_delete(request, pk):
    """Delete payroll record (Admin/HR)."""
    payroll = get_object_or_404(Payroll, pk=pk)
    if request.method == 'POST':
        payroll.delete()
        messages.success(request, 'Payroll record deleted successfully.')
        return redirect('payroll:payroll_list')
    return render(request, 'components/confirm_delete.html', {
        'object': payroll,
        'object_name': f'{payroll.employee.full_name} - {payroll.month}',
        'page_title': 'Delete Payroll Record',
        'cancel_url': 'payroll:payroll_list',
    })


@login_required
@role_required('Admin', 'HR', 'Employee')
def payroll_detail(request, pk):
    """Payroll detail / payslip view."""
    payroll = get_object_or_404(Payroll.objects.select_related('employee', 'employee__department', 'employee__designation'), pk=pk)

    # Data isolation: Employee-role users can only see their own records
    if request.user.is_employee_role() and not request.user.is_admin() and not request.user.is_hr():
        if payroll.employee != request.user.get_employee():
            raise PermissionDenied

    return render(request, 'payroll/payroll_detail.html', {
        'payroll': payroll,
        'page_title': f'Payslip: {payroll.employee.full_name} ({payroll.month})',
    })


@login_required
@role_required('Admin', 'HR', 'Employee')
def my_payroll(request):
    """View own payslips (Employee self-service)."""
    employee = request.user.get_employee()
    if not employee:
        messages.warning(request, 'No employee profile linked to your account.')
        return redirect('dashboard:redirect')

    payrolls = Payroll.objects.filter(employee=employee).order_by('-month')

    paginator = Paginator(payrolls, 12)
    page = request.GET.get('page')
    payrolls_page = paginator.get_page(page)

    return render(request, 'payroll/my_payroll.html', {
        'payrolls': payrolls_page,
        'page_title': 'My Payslips',
    })
