from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.models import Role, Permission, RolePermission, UserRole
from apps.employees.models import Employee
from apps.organization.models import Department, Designation, Branch
from apps.leave_management.models import LeaveType

User = get_user_model()


class Command(BaseCommand):
    help = 'Seeds standard roles, permissions, role-permissions, demo employee profiles, and demo users for Admin, HR, and Employee.'

    def handle(self, *args, **options):
        # 1. Create Roles
        roles_data = [
            ('Admin', 'System-wide administrator with full CRUD access to all modules.'),
            ('HR', 'Human Resource Manager with access to employees, attendance, leave, payroll, organization.'),
            ('Employee', 'Standard employee with access to self-service check-in/out, leave requests, payroll history, and personal profile.'),
        ]

        roles = {}
        for name, desc in roles_data:
            role, created = Role.objects.get_or_create(name=name, defaults={'description': desc})
            roles[name] = role
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created Role: {name}'))

        # 2. Create Permissions
        permissions_data = [
            ('View System Dashboard', 'view_system_dashboard'),
            ('View HR Dashboard', 'view_hr_dashboard'),
            ('View Personal Dashboard', 'view_personal_dashboard'),
            ('Manage Organization', 'manage_organization'),
            ('View Organization', 'view_organization'),
            ('Manage Employees', 'manage_employees'),
            ('View Own Profile', 'view_own_profile'),
            ('Manage Attendance', 'manage_attendance'),
            ('View Own Attendance', 'view_own_attendance'),
            ('Manage Leave Requests', 'manage_leave'),
            ('Apply for Leave', 'apply_leave'),
            ('Manage Payroll', 'manage_payroll'),
            ('View Own Payroll', 'view_own_payroll'),
            ('Manage Users & Roles', 'manage_users'),
        ]

        perms = {}
        for name, codename in permissions_data:
            perm, created = Permission.objects.get_or_create(name=name, defaults={'codename': codename})
            perms[codename] = perm

        # 3. Associate Permissions with Roles
        role_permissions_mapping = {
            'Admin': [
                'view_system_dashboard', 'view_hr_dashboard', 'view_personal_dashboard',
                'manage_organization', 'view_organization', 'manage_employees', 'view_own_profile',
                'manage_attendance', 'view_own_attendance', 'manage_leave', 'apply_leave',
                'manage_payroll', 'view_own_payroll', 'manage_users'
            ],
            'HR': [
                'view_hr_dashboard', 'view_personal_dashboard',
                'manage_organization', 'view_organization', 'manage_employees', 'view_own_profile',
                'manage_attendance', 'view_own_attendance', 'manage_leave', 'apply_leave',
                'manage_payroll', 'view_own_payroll'
            ],
            'Employee': [
                'view_personal_dashboard', 'view_organization', 'view_own_profile',
                'view_own_attendance', 'apply_leave', 'view_own_payroll'
            ]
        }

        for role_name, perm_codenames in role_permissions_mapping.items():
            role = roles[role_name]
            for codename in perm_codenames:
                perm = perms[codename]
                RolePermission.objects.get_or_create(role=role, permission=perm)

        # 4. Create Organization defaults (Dept, Desig, Branch)
        dept, _ = Department.objects.get_or_create(name='Human Resources', defaults={'description': 'HR Department'})
        eng_dept, _ = Department.objects.get_or_create(name='Engineering', defaults={'description': 'Software Engineering'})
        
        desig_hr, _ = Designation.objects.get_or_create(title='HR Specialist', defaults={'description': 'HR Specialist'})
        desig_eng, _ = Designation.objects.get_or_create(title='Software Engineer', defaults={'description': 'Senior Developer'})

        branch, _ = Branch.objects.get_or_create(name='Headquarters', defaults={'address': 'Main HQ, City Center'})

        # 4.1 Create Standard Leave Types
        leave_types = [
            ('Casual Leave', 14, 'Paid time off for personal matters or short vacations.'),
            ('Sick Leave', 10, 'Paid leave for medical treatment, recovery, or illness.'),
            ('Annual Leave', 20, 'Yearly paid leave for rest and vacation.'),
            ('Maternity / Paternity Leave', 90, 'Paid parental leave for newborn care.'),
            ('Unpaid Leave', 30, 'Leave without pay when paid leave balance is exhausted.')
        ]
        for name, days, desc in leave_types:
            LeaveType.objects.get_or_create(name=name, defaults={'max_days_per_year': days, 'description': desc})

        # 5. Create Demo Employee Profiles
        admin_emp, _ = Employee.objects.get_or_create(
            email='admin@hrm-erp.local',
            defaults={
                'first_name': 'System',
                'last_name': 'Administrator',
                'phone': '+1000000000',
                'hire_date': '2026-01-01',
                'department': dept,
                'designation': desig_hr,
                'branch': branch,
                'status': 'active',
                'basic_salary': 100000.00
            }
        )

        hr_emp, _ = Employee.objects.get_or_create(
            email='hr@hrm-erp.local',
            defaults={
                'first_name': 'Sarah',
                'last_name': 'Jenkins',
                'phone': '+1234567890',
                'hire_date': '2026-01-15',
                'department': dept,
                'designation': desig_hr,
                'branch': branch,
                'status': 'active',
                'basic_salary': 75000.00
            }
        )

        dev_emp, _ = Employee.objects.get_or_create(
            email='employee@hrm-erp.local',
            defaults={
                'first_name': 'Alex',
                'last_name': 'Morgan',
                'phone': '+1987654321',
                'hire_date': '2026-02-01',
                'department': eng_dept,
                'designation': desig_eng,
                'branch': branch,
                'status': 'active',
                'basic_salary': 65000.00
            }
        )

        # 6. Create 3 Role Demo Accounts (Admin, HR, Employee)
        users_to_seed = [
            ('admin', 'admin@hrm-erp.local', 'admin123', 'Admin', 'System', 'Administrator', admin_emp, True),
            ('hr_manager', 'hr@hrm-erp.local', 'hr123', 'HR', 'Sarah', 'Jenkins', hr_emp, False),
            ('employee', 'employee@hrm-erp.local', 'emp123', 'Employee', 'Alex', 'Morgan', dev_emp, False),
        ]

        for username, email, password, role_name, fname, lname, emp_obj, is_super in users_to_seed:
            user = User.objects.filter(username=username).first()
            if not user:
                if is_super:
                    user = User.objects.create_superuser(
                        username=username, email=email, password=password,
                        first_name=fname, last_name=lname, employee=emp_obj
                    )
                else:
                    user = User.objects.create_user(
                        username=username, email=email, password=password,
                        first_name=fname, last_name=lname, employee=emp_obj
                    )
                UserRole.objects.create(user=user, role=roles[role_name])
                self.stdout.write(self.style.SUCCESS(f'Created Demo {role_name} User: "{username}" / "{password}"'))
            else:
                user.employee = emp_obj
                user.save()
                UserRole.objects.get_or_create(user=user, role=roles[role_name])
                self.stdout.write(self.style.WARNING(f'User "{username}" updated.'))
