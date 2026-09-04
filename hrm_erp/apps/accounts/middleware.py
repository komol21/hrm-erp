"""
Middleware to attach role information to request.user on every request.
"""


class RoleMiddleware:
    """
    Attaches role-related attributes to request.user:
    - request.user.role_names (list of role name strings)
    - request.user._is_admin (bool)
    - request.user._is_hr (bool)
    - request.user._is_employee_role (bool)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Cache role names on the user object for this request
            role_names = request.user.get_role_names()
            request.user.role_names = role_names
            request.user._is_admin = 'Admin' in role_names
            request.user._is_hr = 'HR' in role_names
            request.user._is_employee_role = 'Employee' in role_names
        else:
            request.user.role_names = []
            request.user._is_admin = False
            request.user._is_hr = False
            request.user._is_employee_role = False

        response = self.get_response(request)
        return response
