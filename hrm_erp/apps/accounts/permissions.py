"""
Role-based authorization utilities.
Provides decorators, mixins, and helpers for role-based access control.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def role_required(*role_names):
    """
    Decorator for function-based views.
    Requires the user to have at least one of the specified roles.

    Usage:
        @role_required('Admin', 'HR')
        def some_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if not any(request.user.has_role(role) for role in role_names):
                messages.error(request, 'You do not have permission to access this page.')
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view_func):
    """Shortcut decorator: Admin only."""
    return role_required('Admin')(view_func)


def hr_required(view_func):
    """Shortcut decorator: Admin or HR."""
    return role_required('Admin', 'HR')(view_func)


def employee_required(view_func):
    """Shortcut decorator: any authenticated user with a role."""
    return role_required('Admin', 'HR', 'Employee')(view_func)


class RoleRequiredMixin:
    """
    CBV mixin for role-based access control.

    Usage:
        class MyView(RoleRequiredMixin, ListView):
            required_roles = ['Admin', 'HR']
    """
    required_roles = []

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if self.required_roles and not any(
            request.user.has_role(role) for role in self.required_roles
        ):
            messages.error(request, 'You do not have permission to access this page.')
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin(RoleRequiredMixin):
    """Admin only."""
    required_roles = ['Admin']


class HRRequiredMixin(RoleRequiredMixin):
    """Admin or HR."""
    required_roles = ['Admin', 'HR']


class EmployeeRequiredMixin(RoleRequiredMixin):
    """Any authenticated role."""
    required_roles = ['Admin', 'HR', 'Employee']


def get_employee_for_user(user):
    """
    Safely get the Employee record linked to a user.
    Returns None if no employee is linked.
    """
    if user and user.is_authenticated:
        return user.get_employee()
    return None
