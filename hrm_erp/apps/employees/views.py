from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from .models import Employee
from .forms import EmployeeForm, EmployeeSelfUpdateForm
from apps.accounts.permissions import hr_required, role_required


@login_required
@role_required('Admin', 'HR', 'Employee')
def employee_list(request):
    """List employees. Employee role only sees their own profile link."""
    # Employee-role users should go to their own profile
    if request.user.is_employee_role() and not request.user.is_admin() and not request.user.is_hr():
        return redirect('employees:my_profile')

    search = request.GET.get('search', '')
    department = request.GET.get('department', '')
    status = request.GET.get('status', '')
    branch = request.GET.get('branch', '')

    employees = Employee.objects.select_related('department', 'designation', 'branch').all()

    if search:
        employees = employees.filter(
            first_name__icontains=search
        ) | employees.filter(
            last_name__icontains=search
        ) | employees.filter(
            email__icontains=search
        )
    if department:
        employees = employees.filter(department_id=department)
    if status:
        employees = employees.filter(status=status)
    if branch:
        employees = employees.filter(branch_id=branch)

    paginator = Paginator(employees, 10)
    page = request.GET.get('page')
    employees = paginator.get_page(page)

    from apps.organization.models import Department, Branch
    return render(request, 'employees/employee_list.html', {
        'employees': employees,
        'search': search,
        'departments': Department.objects.all(),
        'branches': Branch.objects.all(),
        'selected_department': department,
        'selected_status': status,
        'selected_branch': branch,
        'status_choices': Employee.STATUS_CHOICES,
        'page_title': 'Employees',
    })


@login_required
@hr_required
def employee_create(request):
    """Create a new employee (Admin/HR) and automatically provision a User login account."""
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            emp = form.save()

            # Auto-provision or link a User login account for this employee
            from apps.accounts.models import User, Role, UserRole
            user = User.objects.filter(email__iexact=emp.email).first()
            if user is None:
                base_username = emp.email.split('@')[0]
                username = base_username
                counter = 1
                while User.objects.filter(username__iexact=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

                temp_password = "Employee@123"
                user = User.objects.create(
                    username=username,
                    email=emp.email,
                    first_name=emp.first_name,
                    last_name=emp.last_name,
                    employee=emp,
                )
                user.set_password(temp_password)
                user.save()

                employee_role, _ = Role.objects.get_or_create(
                    name='Employee',
                    defaults={'description': 'Standard employee self-service account.'}
                )
                UserRole.objects.create(user=user, role=employee_role)
                messages.success(
                    request,
                    f'Employee "{emp.full_name}" created successfully! Login account "{username}" provisioned (Default Password: {temp_password}).'
                )
            else:
                if user.employee != emp:
                    user.employee = emp
                    user.save()
                messages.success(
                    request,
                    f'Employee "{emp.full_name}" created successfully and linked to existing user "{user.username}".'
                )
            return redirect('employees:employee_list')
    else:
        form = EmployeeForm()
    return render(request, 'employees/employee_form.html', {
        'form': form,
        'page_title': 'Add Employee',
        'is_edit': False,
    })


@login_required
@hr_required
def employee_bulk_import(request):
    """
    Bulk import employees and auto-create User login accounts from a CSV file.
    Also serves sample CSV download if ?sample=csv is passed.
    """
    import csv
    import io
    from datetime import date, datetime
    from django.http import HttpResponse
    from apps.organization.models import Department, Designation, Branch
    from apps.accounts.models import User, Role, UserRole

    if request.GET.get('sample') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="hrm_employees_template.csv"'
        writer = csv.writer(response)
        writer.writerow([
            'first_name', 'last_name', 'email', 'phone', 'gender',
            'hire_date', 'department', 'designation', 'branch', 'basic_salary', 'role'
        ])
        writer.writerow([
            'Alex', 'Morgan', 'alex.morgan@example.com', '+1234567890', 'male',
            date.today().strftime('%Y-%m-%d'), 'Engineering', 'Software Engineer', 'Headquarters', '65000', 'Employee'
        ])
        writer.writerow([
            'Sophia', 'Chen', 'sophia.chen@example.com', '+1987654321', 'female',
            date.today().strftime('%Y-%m-%d'), 'Human Resources', 'HR Specialist', 'Headquarters', '58000', 'HR'
        ])
        return response

    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, 'Please select a CSV file to upload.')
            return redirect('employees:employee_bulk_import')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Invalid file format. Please upload a .csv file.')
            return redirect('employees:employee_bulk_import')

        try:
            decoded_file = csv_file.read().decode('utf-8-sig')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            created_count = 0
            updated_count = 0
            error_list = []

            for row_idx, row in enumerate(reader, start=2):
                email = row.get('email', '').strip().lower()
                first_name = row.get('first_name', '').strip()
                last_name = row.get('last_name', '').strip()

                if not email or not first_name:
                    error_list.append(f"Row {row_idx}: Missing required fields (first_name or email).")
                    continue

                phone = row.get('phone', '').strip()
                gender = row.get('gender', '').strip().lower()
                if gender not in ['male', 'female', 'other']:
                    gender = ''

                hire_date_str = row.get('hire_date', '').strip()
                hire_date_val = date.today()
                if hire_date_str:
                    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y'):
                        try:
                            hire_date_val = datetime.strptime(hire_date_str, fmt).date()
                            break
                        except ValueError:
                            pass

                # Department
                dept_name = row.get('department', '').strip()
                dept = None
                if dept_name:
                    dept, _ = Department.objects.get_or_create(name=dept_name)

                # Designation
                desig_title = row.get('designation', '').strip()
                desig = None
                if desig_title:
                    desig, _ = Designation.objects.get_or_create(title=desig_title)

                # Branch
                branch_name = row.get('branch', '').strip()
                branch = None
                if branch_name:
                    branch, _ = Branch.objects.get_or_create(name=branch_name)

                # Basic Salary
                salary_str = row.get('basic_salary', '').strip()
                try:
                    basic_salary = float(salary_str) if salary_str else 50000.00
                except ValueError:
                    basic_salary = 50000.00

                # Create or update Employee
                emp, created = Employee.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name or 'User',
                        'phone': phone,
                        'gender': gender,
                        'hire_date': hire_date_val,
                        'department': dept,
                        'designation': desig,
                        'branch': branch,
                        'basic_salary': basic_salary,
                        'status': 'active',
                    }
                )
                if not created:
                    emp.first_name = first_name
                    if last_name:
                        emp.last_name = last_name
                    if dept:
                        emp.department = dept
                    if desig:
                        emp.designation = desig
                    if branch:
                        emp.branch = branch
                    if basic_salary:
                        emp.basic_salary = basic_salary
                    emp.save()
                    updated_count += 1
                else:
                    created_count += 1

                # Provision User account
                user = User.objects.filter(email__iexact=email).first()
                role_name = row.get('role', '').strip().capitalize()
                if role_name not in ['Admin', 'HR', 'Employee']:
                    role_name = 'Employee'

                role_obj, _ = Role.objects.get_or_create(
                    name=role_name,
                    defaults={'description': f'{role_name} role'}
                )

                if user is None:
                    base_username = email.split('@')[0]
                    username = base_username
                    counter = 1
                    while User.objects.filter(username__iexact=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1

                    user = User.objects.create(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        employee=emp,
                    )
                    user.set_password('Employee@123')
                    user.save()
                    UserRole.objects.create(user=user, role=role_obj)
                else:
                    if user.employee != emp:
                        user.employee = emp
                        user.save()
                    if not user.user_roles.exists():
                        UserRole.objects.create(user=user, role=role_obj)

            messages.success(
                request,
                f'Bulk import successful! {created_count} employee(s) added, {updated_count} updated. Default password for new logins: "Employee@123".'
            )
            if error_list:
                for err in error_list[:5]:
                    messages.warning(request, err)

            return redirect('employees:employee_list')

        except Exception as e:
            messages.error(request, f'Failed to process CSV file: {str(e)}')
            return redirect('employees:employee_bulk_import')

    return render(request, 'employees/employee_bulk_import.html', {
        'page_title': 'Bulk Import Staff & Users',
    })


@login_required
@role_required('Admin', 'HR', 'Employee')
def employee_detail(request, pk):
    """View employee detail. Employee role can only view their own."""
    employee = get_object_or_404(
        Employee.objects.select_related('department', 'designation', 'branch'),
        pk=pk
    )
    # Data isolation: Employee-role users can only see their own record
    if request.user.is_employee_role() and not request.user.is_admin() and not request.user.is_hr():
        if request.user.employee_id != employee.pk:
            raise PermissionDenied

    return render(request, 'employees/employee_detail.html', {
        'employee': employee,
        'page_title': f'{employee.full_name}',
    })


@login_required
@hr_required
def employee_edit(request, pk):
    """Edit an employee (Admin/HR). Email is read-only."""
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, 'Employee updated successfully.')
            return redirect('employees:employee_detail', pk=employee.pk)
    else:
        form = EmployeeForm(instance=employee)
    return render(request, 'employees/employee_form.html', {
        'form': form,
        'page_title': f'Edit Employee: {employee.full_name}',
        'is_edit': True,
        'employee': employee,
    })


@login_required
@hr_required
def employee_delete(request, pk):
    """Delete an employee (Admin/HR)."""
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        employee.delete()
        messages.success(request, 'Employee deleted successfully.')
        return redirect('employees:employee_list')
    return render(request, 'components/confirm_delete.html', {
        'object': employee,
        'object_name': employee.full_name,
        'page_title': f'Delete Employee: {employee.full_name}',
        'cancel_url': 'employees:employee_list',
    })


def _get_or_create_user_employee(user):
    """Ensure user has a linked Employee profile."""
    employee = user.get_employee()
    if not employee:
        from datetime import date
        from apps.organization.models import Department, Designation, Branch
        dept = Department.objects.first()
        desig = Designation.objects.first()
        branch = Branch.objects.first()
        employee = Employee.objects.create(
            first_name=user.first_name or user.username.capitalize(),
            last_name=user.last_name or ('Admin' if user.is_admin() else 'User'),
            email=user.email or f"{user.username}@hrm.local",
            department=dept,
            designation=desig,
            branch=branch,
            hire_date=date.today(),
            status='active',
            basic_salary=100000.00 if user.is_admin() else 50000.00
        )
        user.employee = employee
        user.save(update_fields=['employee'])
    return employee


@login_required
@role_required('Admin', 'HR', 'Employee')
def my_profile(request):
    """View own profile for Admin, HR, or Employee."""
    employee = _get_or_create_user_employee(request.user)
    return render(request, 'employees/employee_detail.html', {
        'employee': employee,
        'page_title': 'My Profile',
        'is_own_profile': True,
    })


@login_required
@role_required('Admin', 'HR', 'Employee')
def edit_my_profile(request):
    """Self-service profile update: Employees, HR, and Admins can update their personal profile."""
    employee = _get_or_create_user_employee(request.user)

    if request.method == 'POST':
        form = EmployeeSelfUpdateForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            emp = form.save()
            # Keep User first_name and last_name in sync with Employee profile
            user = request.user
            updated_fields = []
            if emp.first_name and user.first_name != emp.first_name:
                user.first_name = emp.first_name
                updated_fields.append('first_name')
            if emp.last_name and user.last_name != emp.last_name:
                user.last_name = emp.last_name
                updated_fields.append('last_name')
            if updated_fields:
                user.save(update_fields=updated_fields)

            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('employees:my_profile')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = EmployeeSelfUpdateForm(instance=employee)

    return render(request, 'employees/self_profile_form.html', {
        'form': form,
        'employee': employee,
        'page_title': 'Edit My Profile',
    })


