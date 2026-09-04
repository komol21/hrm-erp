"""
Context processors to inject role information into all templates.
"""


def role_context(request):
    """
    Adds role flags to template context:
    - is_admin, is_hr, is_employee_role
    - user_roles (list of role names)
    - linked_employee (Employee object or None)
    - pending_role_requests_count (int, for admins)
    """
    if request.user.is_authenticated:
        is_adm = getattr(request.user, '_is_admin', request.user.is_admin())
        pending_count = 0
        if is_adm:
            from .models import RoleRequest
            pending_count = RoleRequest.objects.filter(status='pending').count()

        return {
            'is_admin': is_adm,
            'is_hr': getattr(request.user, '_is_hr', request.user.is_hr()),
            'is_employee_role': getattr(request.user, '_is_employee_role', request.user.is_employee_role()),
            'user_roles': getattr(request.user, 'role_names', request.user.get_role_names()),
            'linked_employee': request.user.get_employee(),
            'pending_role_requests_count': pending_count,
        }
    return {
        'is_admin': False,
        'is_hr': False,
        'is_employee_role': False,
        'user_roles': [],
        'linked_employee': None,
        'pending_role_requests_count': 0,
    }

