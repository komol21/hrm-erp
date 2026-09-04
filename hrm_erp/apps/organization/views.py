from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Department, Designation, Branch
from .forms import DepartmentForm, DesignationForm, BranchForm
from apps.accounts.permissions import hr_required, role_required


# ─── Department CRUD ──────────────────────────────────────────────────────────

@login_required
@role_required('Admin', 'HR', 'Employee')
def department_list(request):
    """List all departments."""
    departments = Department.objects.all()
    return render(request, 'organization/department_list.html', {
        'departments': departments,
        'page_title': 'Departments',
    })


@login_required
@hr_required
def department_create(request):
    """Create a new department (Admin/HR)."""
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department created successfully.')
            return redirect('organization:department_list')
    else:
        form = DepartmentForm()
    return render(request, 'organization/department_form.html', {
        'form': form,
        'page_title': 'Create Department',
        'is_edit': False,
    })


@login_required
@hr_required
def department_edit(request, pk):
    """Edit a department (Admin/HR)."""
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department updated successfully.')
            return redirect('organization:department_list')
    else:
        form = DepartmentForm(instance=department)
    return render(request, 'organization/department_form.html', {
        'form': form,
        'page_title': f'Edit Department: {department.name}',
        'is_edit': True,
    })


@login_required
@hr_required
def department_delete(request, pk):
    """Delete a department (Admin/HR)."""
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        department.delete()
        messages.success(request, 'Department deleted successfully.')
        return redirect('organization:department_list')
    return render(request, 'components/confirm_delete.html', {
        'object': department,
        'object_name': department.name,
        'page_title': f'Delete Department: {department.name}',
        'cancel_url': 'organization:department_list',
    })


# ─── Designation CRUD ─────────────────────────────────────────────────────────

@login_required
@role_required('Admin', 'HR', 'Employee')
def designation_list(request):
    """List all designations."""
    designations = Designation.objects.all()
    return render(request, 'organization/designation_list.html', {
        'designations': designations,
        'page_title': 'Designations',
    })


@login_required
@hr_required
def designation_create(request):
    """Create a new designation (Admin/HR)."""
    if request.method == 'POST':
        form = DesignationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Designation created successfully.')
            return redirect('organization:designation_list')
    else:
        form = DesignationForm()
    return render(request, 'organization/designation_form.html', {
        'form': form,
        'page_title': 'Create Designation',
        'is_edit': False,
    })


@login_required
@hr_required
def designation_edit(request, pk):
    """Edit a designation (Admin/HR)."""
    designation = get_object_or_404(Designation, pk=pk)
    if request.method == 'POST':
        form = DesignationForm(request.POST, instance=designation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Designation updated successfully.')
            return redirect('organization:designation_list')
    else:
        form = DesignationForm(instance=designation)
    return render(request, 'organization/designation_form.html', {
        'form': form,
        'page_title': f'Edit Designation: {designation.title}',
        'is_edit': True,
    })


@login_required
@hr_required
def designation_delete(request, pk):
    """Delete a designation (Admin/HR)."""
    designation = get_object_or_404(Designation, pk=pk)
    if request.method == 'POST':
        designation.delete()
        messages.success(request, 'Designation deleted successfully.')
        return redirect('organization:designation_list')
    return render(request, 'components/confirm_delete.html', {
        'object': designation,
        'object_name': designation.title,
        'page_title': f'Delete Designation: {designation.title}',
        'cancel_url': 'organization:designation_list',
    })


# ─── Branch CRUD ──────────────────────────────────────────────────────────────

@login_required
@role_required('Admin', 'HR', 'Employee')
def branch_list(request):
    """List all branches."""
    branches = Branch.objects.all()
    return render(request, 'organization/branch_list.html', {
        'branches': branches,
        'page_title': 'Branches',
    })


@login_required
@hr_required
def branch_create(request):
    """Create a new branch (Admin/HR)."""
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Branch created successfully.')
            return redirect('organization:branch_list')
    else:
        form = BranchForm()
    return render(request, 'organization/branch_form.html', {
        'form': form,
        'page_title': 'Create Branch',
        'is_edit': False,
    })


@login_required
@hr_required
def branch_edit(request, pk):
    """Edit a branch (Admin/HR)."""
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        form = BranchForm(request.POST, instance=branch)
        if form.is_valid():
            form.save()
            messages.success(request, 'Branch updated successfully.')
            return redirect('organization:branch_list')
    else:
        form = BranchForm(instance=branch)
    return render(request, 'organization/branch_form.html', {
        'form': form,
        'page_title': f'Edit Branch: {branch.name}',
        'is_edit': True,
    })


@login_required
@hr_required
def branch_delete(request, pk):
    """Delete a branch (Admin/HR)."""
    branch = get_object_or_404(Branch, pk=pk)
    if request.method == 'POST':
        branch.delete()
        messages.success(request, 'Branch deleted successfully.')
        return redirect('organization:branch_list')
    return render(request, 'components/confirm_delete.html', {
        'object': branch,
        'object_name': branch.name,
        'page_title': f'Delete Branch: {branch.name}',
        'cancel_url': 'organization:branch_list',
    })
