from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from .models import User, Role, UserRole, Permission, RolePermission, RoleRequest
from .forms import (
    LoginForm, RegisterForm, UserForm, UserEditForm, RoleForm,
    RoleRequestForm, RoleRequestReviewForm, ForgotPasswordForm,
    ResetPasswordConfirmForm
)
from .permissions import admin_required, hr_required
from apps.employees.models import Employee


@ensure_csrf_cookie
def login_view(request):
    """Handle user login supporting both username and email address."""
    if request.user.is_authenticated:
        return redirect('dashboard:redirect')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data['username'].strip()
            password = form.cleaned_data['password']

            # Resolve email to username if an email address was entered
            if '@' in username_or_email:
                user_match = User.objects.filter(email__iexact=username_or_email).first()
                username = user_match.username if user_match else username_or_email
            else:
                username = username_or_email

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                return redirect('dashboard:redirect')
            else:
                messages.error(request, 'Invalid username/email or password.')
    else:
        form = LoginForm()

    return render(request, 'auth/login.html', {'form': form})



@ensure_csrf_cookie
def register_view(request):
    """
    Handle public user sign up / registration.
    Security policy: All public registrations are strictly assigned the 'Employee' role.
    HR or Admin privileges must be requested and approved by an Admin.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:redirect')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            
            # Create a matching employee profile for newly registered users
            first_name = form.cleaned_data.get('first_name', '')
            last_name = form.cleaned_data.get('last_name', '')
            email = form.cleaned_data.get('email', '')
            
            from datetime import date
            emp = Employee.objects.create(
                first_name=first_name or user.username,
                last_name=last_name or 'User',
                email=email or f"{user.username}@hrm.local",
                hire_date=date.today(),
                status='active',
                basic_salary=50000.00
            )
            user.employee = emp
            user.save()

            # Strictly assign standard Employee role by default
            employee_role, _ = Role.objects.get_or_create(
                name='Employee',
                defaults={'description': 'Standard employee self-service account.'}
            )
            UserRole.objects.create(user=user, role=employee_role)

            # Require user to sign in manually after registration
            messages.success(
                request,
                f'Account created successfully for {user.username} as an Employee! Please sign in with your credentials.'
            )
            return redirect('accounts:login')
    else:
        form = RegisterForm()

    return render(request, 'auth/register.html', {'form': form})


@ensure_csrf_cookie
def forgot_password_view(request):
    """Handle password reset request via registered email address."""
    if request.user.is_authenticated:
        return redirect('dashboard:redirect')

    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email__iexact=email).first()
            if user:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_url = request.build_absolute_uri(
                    reverse('accounts:reset_password_confirm', kwargs={'uidb64': uid, 'token': token})
                )
                subject = 'HRM ERP Portal - Password Reset Request'
                message = (
                    f"Hello {user.get_full_name() or user.username},\n\n"
                    f"You requested a password reset for your HRM ERP account.\n\n"
                    f"Please click the link below to set a new password:\n{reset_url}\n\n"
                    f"If you did not request this change, please ignore this email.\n\n"
                    f"Best regards,\nHRM ERP Support Team"
                )
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                except Exception:
                    pass

                request.session['reset_email'] = email
                request.session['reset_link_dev'] = reset_url
                return redirect('accounts:forgot_password_done')
    else:
        form = ForgotPasswordForm()

    return render(request, 'auth/forgot_password.html', {'form': form})


def forgot_password_done_view(request):
    """Confirmation view after submitting password reset request."""
    email = request.session.get('reset_email', '')
    reset_link_dev = request.session.get('reset_link_dev', '')
    return render(request, 'auth/forgot_password_done.html', {
        'email': email,
        'reset_link_dev': reset_link_dev
    })


@ensure_csrf_cookie
def reset_password_confirm_view(request, uidb64, token):
    """Confirm password reset link and allow user to set a new password."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        validlink = True
        if request.method == 'POST':
            form = ResetPasswordConfirmForm(request.POST)
            if form.is_valid():
                new_password = form.cleaned_data['new_password']
                user.set_password(new_password)
                user.save()
                messages.success(request, 'Your password has been reset successfully! Please sign in with your new password.')
                return redirect('accounts:login')
        else:
            form = ResetPasswordConfirmForm()
    else:
        validlink = False
        form = None

    return render(request, 'auth/reset_password_confirm.html', {
        'form': form,
        'validlink': validlink
    })


@login_required
def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')

    return redirect('accounts:login')


# ─── User Management (Admin only) ─────────────────────────────────────────────

@login_required
@admin_required
def user_list(request):
    """List all users (Admin only)."""
    search = request.GET.get('search', '')
    users = User.objects.all().select_related('employee')
    if search:
        users = users.filter(username__icontains=search) | users.filter(email__icontains=search)

    paginator = Paginator(users, 10)
    page = request.GET.get('page')
    users = paginator.get_page(page)

    return render(request, 'accounts/user_list.html', {
        'users': users,
        'search': search,
        'page_title': 'User Management',
    })


@login_required
@admin_required
def user_create(request):
    """Create a new user (Admin only). Auto-creates an Employee profile if not selected."""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            
            # If no employee was explicitly selected, auto-create a matching Employee record
            if not user.employee:
                from datetime import date
                email = user.email or f"{user.username}@hrm.local"
                first_name = form.cleaned_data.get('first_name') or user.username
                last_name = form.cleaned_data.get('last_name') or 'User'
                
                emp, _ = Employee.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'hire_date': date.today(),
                        'status': 'active',
                        'basic_salary': 50000.00,
                    }
                )
                user.employee = emp

            user.save()
            # Assign role
            role_id = form.cleaned_data.get('role')
            if role_id:
                role = Role.objects.get(id=role_id)
                UserRole.objects.create(user=user, role=role)
            messages.success(request, f'User "{user.username}" created successfully with linked employee profile.')
            return redirect('accounts:user_list')
    else:
        form = UserForm()

    return render(request, 'accounts/user_form.html', {
        'form': form,
        'page_title': 'Create User',
        'is_edit': False,
    })


@login_required
@admin_required
def user_edit(request, pk):
    """Edit an existing user (Admin only)."""
    user = get_object_or_404(User, pk=pk)
    current_role = user.user_roles.first()

    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            # Update password if provided
            new_password = form.cleaned_data.get('new_password')
            if new_password:
                user.set_password(new_password)
                user.save()
            # Update role
            role_id = form.cleaned_data.get('role')
            if role_id:
                UserRole.objects.filter(user=user).delete()
                role = Role.objects.get(id=role_id)
                UserRole.objects.create(user=user, role=role)
            messages.success(request, f'User "{user.username}" updated successfully.')
            return redirect('accounts:user_list')
    else:
        initial = {}
        if current_role:
            initial['role'] = current_role.role_id
        form = UserEditForm(instance=user, initial=initial)

    return render(request, 'accounts/user_form.html', {
        'form': form,
        'page_title': f'Edit User: {user.username}',
        'is_edit': True,
        'edit_user': user,
    })


@login_required
@admin_required
def user_delete(request, pk):
    """Delete a user (Admin only)."""
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User "{username}" deleted successfully.')
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_confirm_delete.html', {
        'object': user,
        'page_title': f'Delete User: {user.username}',
        'cancel_url': 'accounts:user_list',
    })


# ─── Role Management (Admin only) ─────────────────────────────────────────────

@login_required
@admin_required
def role_list(request):
    """List all roles (Admin only)."""
    roles = Role.objects.all()
    return render(request, 'accounts/role_list.html', {
        'roles': roles,
        'page_title': 'Role Management',
    })


@login_required
@admin_required
def role_create(request):
    """Create a new role (Admin only)."""
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Role created successfully.')
            return redirect('accounts:role_list')
    else:
        form = RoleForm()

    return render(request, 'accounts/role_form.html', {
        'form': form,
        'page_title': 'Create Role',
        'is_edit': False,
    })


@login_required
@admin_required
def role_edit(request, pk):
    """Edit a role (Admin only)."""
    role = get_object_or_404(Role, pk=pk)
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            messages.success(request, 'Role updated successfully.')
            return redirect('accounts:role_list')
    else:
        form = RoleForm(instance=role)

    return render(request, 'accounts/role_form.html', {
        'form': form,
        'page_title': f'Edit Role: {role.name}',
        'is_edit': True,
    })


@login_required
@admin_required
def role_delete(request, pk):
    """Delete a role (Admin only)."""
    role = get_object_or_404(Role, pk=pk)
    if request.method == 'POST':
        role.delete()
        messages.success(request, 'Role deleted successfully.')
        return redirect('accounts:role_list')
    return render(request, 'accounts/user_confirm_delete.html', {
        'object': role,
        'page_title': f'Delete Role: {role.name}',
        'cancel_url': 'accounts:role_list',
    })


# ─── Role Elevation & Approval Workflow ───────────────────────────────────────

@login_required
def my_role_requests(request):
    """
    Self-service view for employees to request elevated HR/Admin privileges,
    and view history/status of their previous requests.
    """
    user_requests = RoleRequest.objects.filter(user=request.user).select_related('requested_role', 'reviewed_by')
    has_pending = user_requests.filter(status='pending').exists()

    if request.method == 'POST':
        form = RoleRequestForm(request.POST)
        if form.is_valid():
            role_id = form.cleaned_data['requested_role']
            reason = form.cleaned_data['reason']
            target_role = get_object_or_404(Role, id=role_id)

            # Check if user already holds this role
            if request.user.has_role(target_role.name):
                messages.warning(request, f'You already have the "{target_role.name}" role.')
                return redirect('accounts:my_role_requests')

            # Check if a pending request for this role already exists
            if user_requests.filter(requested_role=target_role, status='pending').exists():
                messages.warning(request, f'You already have a pending request for the "{target_role.name}" role.')
                return redirect('accounts:my_role_requests')

            RoleRequest.objects.create(
                user=request.user,
                requested_role=target_role,
                reason=reason,
                status='pending'
            )
            messages.success(
                request,
                f'Your request for "{target_role.name}" privileges has been submitted for Admin review.'
            )
            return redirect('accounts:my_role_requests')
    else:
        form = RoleRequestForm()

    return render(request, 'accounts/my_role_requests.html', {
        'form': form,
        'user_requests': user_requests,
        'has_pending': has_pending,
        'page_title': 'Request Role Upgrade',
    })


@login_required
@admin_required
def admin_role_request_list(request):
    """
    Admin portal to list, filter, and review all employee role upgrade requests.
    """
    status_filter = request.GET.get('status', 'pending')
    search = request.GET.get('search', '')

    queryset = RoleRequest.objects.all().select_related('user', 'requested_role', 'reviewed_by')

    if status_filter and status_filter != 'all':
        queryset = queryset.filter(status=status_filter)

    if search:
        queryset = queryset.filter(
            user__username__icontains=search
        ) | queryset.filter(
            user__email__icontains=search
        ) | queryset.filter(
            user__first_name__icontains=search
        ) | queryset.filter(
            user__last_name__icontains=search
        )

    # Statistics counters
    counts = {
        'pending': RoleRequest.objects.filter(status='pending').count(),
        'approved': RoleRequest.objects.filter(status='approved').count(),
        'rejected': RoleRequest.objects.filter(status='rejected').count(),
        'all': RoleRequest.objects.count(),
    }

    paginator = Paginator(queryset, 10)
    page = request.GET.get('page')
    role_requests = paginator.get_page(page)

    return render(request, 'accounts/admin_role_requests.html', {
        'role_requests': role_requests,
        'counts': counts,
        'status_filter': status_filter,
        'search': search,
        'page_title': 'Role Upgrade Requests',
    })


@login_required
@admin_required
def admin_role_request_review(request, pk):
    """
    Admin action to inspect, verify, and approve or reject a role elevation request.
    Upon approval, updates the target user's role in the database.
    """
    role_req = get_object_or_404(
        RoleRequest.objects.select_related('user', 'requested_role', 'reviewed_by'),
        pk=pk
    )

    if request.method == 'POST':
        form = RoleRequestReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            admin_remarks = form.cleaned_data.get('admin_remarks', '')

            role_req.admin_remarks = admin_remarks
            role_req.reviewed_by = request.user
            role_req.reviewed_at = timezone.now()

            target_user = role_req.user
            requested_role = role_req.requested_role

            if action == 'approve':
                role_req.status = 'approved'
                role_req.save()

                # Assign the requested role to the target user (replacing previous roles or adding)
                UserRole.objects.filter(user=target_user).delete()
                UserRole.objects.create(user=target_user, role=requested_role)

                messages.success(
                    request,
                    f'Approved! User "{target_user.username}" has been granted "{requested_role.name}" privileges.'
                )
            else:
                role_req.status = 'rejected'
                role_req.save()

                messages.info(
                    request,
                    f'Role request for "{target_user.username}" was rejected.'
                )

            return redirect('accounts:admin_role_request_list')
    else:
        form = RoleRequestReviewForm(initial={
            'admin_remarks': role_req.admin_remarks,
            'action': 'approve' if role_req.status == 'pending' else role_req.status
        })

    return render(request, 'accounts/admin_role_request_review.html', {
        'role_req': role_req,
        'form': form,
        'page_title': f'Review Request: {role_req.user.username} -> {role_req.requested_role.name}',
    })

