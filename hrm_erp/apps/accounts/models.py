from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.Model):
    """User roles: Admin, HR, Employee."""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'roles'
        ordering = ['name']

    def __str__(self):
        return self.name


class Permission(models.Model):
    """Granular permissions assignable to roles."""
    name = models.CharField(max_length=100, unique=True)
    codename = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'permissions'
        ordering = ['name']

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """Junction table linking Role <-> Permission."""
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_permissions'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='role_permissions'
    )

    class Meta:
        db_table = 'role_permissions'
        unique_together = ('role', 'permission')

    def __str__(self):
        return f"{self.role.name} - {self.permission.name}"


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Optionally links to an Employee record via employee_id (nullable).
    """
    employee = models.OneToOneField(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_account'
    )

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.username

    def get_roles(self):
        """Return a queryset of Role objects for this user."""
        return Role.objects.filter(user_roles__user=self)

    def get_role_names(self):
        """Return a list of role names for this user."""
        return list(self.get_roles().values_list('name', flat=True))

    def has_role(self, role_name):
        """Check if user has a specific role by name."""
        return self.user_roles.filter(role__name=role_name).exists()

    def is_admin(self):
        """Check if user has Admin role."""
        return self.has_role('Admin')

    def is_hr(self):
        """Check if user has HR role."""
        return self.has_role('HR')

    def is_employee_role(self):
        """Check if user has Employee role."""
        return self.has_role('Employee')

    def get_employee(self):
        """Return the linked Employee record, or None."""
        return self.employee


class UserRole(models.Model):
    """Junction table linking User <-> Role."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_roles'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='user_roles'
    )

    class Meta:
        db_table = 'user_roles'
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"


class RoleRequest(models.Model):
    """
    Role elevation request submitted by an employee for HR or Admin privileges.
    Must be reviewed and approved by an existing Admin.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='role_requests'
    )
    requested_role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='elevation_requests'
    )
    reason = models.TextField(
        help_text='Business justification / reason for requested privileges'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    admin_remarks = models.TextField(
        blank=True,
        default='',
        help_text='Feedback or remarks from reviewing administrator'
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_role_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'role_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} -> {self.requested_role.name} ({self.status})"

