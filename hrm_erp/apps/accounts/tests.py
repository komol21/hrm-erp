from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.accounts.models import Role, UserRole
from apps.employees.models import Employee
from apps.leave_management.models import LeaveType

User = get_user_model()


class HRMAuthorizationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # 1. Create Roles
        self.admin_role = Role.objects.create(name='Admin', description='Admin role')
        self.hr_role = Role.objects.create(name='HR', description='HR role')
        self.employee_role = Role.objects.create(name='Employee', description='Employee role')
        
        # 2. Create Employee Profiles
        self.emp1 = Employee.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@workplace.local',
            hire_date='2026-01-01',
            basic_salary=50000
        )
        self.emp2 = Employee.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@workplace.local',
            hire_date='2026-01-01',
            basic_salary=60000
        )

        # 3. Create User accounts
        self.admin_user = User.objects.create_user(
            username='admin_user',
            password='password123',
            email='admin@workplace.local'
        )
        UserRole.objects.create(user=self.admin_user, role=self.admin_role)

        self.hr_emp = Employee.objects.create(
            first_name='HR',
            last_name='Manager',
            email='hr@workplace.local',
            hire_date='2026-01-01',
            basic_salary=70000
        )
        self.hr_user = User.objects.create_user(
            username='hr_user',
            password='password123',
            email='hr@workplace.local',
            employee=self.hr_emp
        )
        UserRole.objects.create(user=self.hr_user, role=self.hr_role)

        self.emp1_user = User.objects.create_user(
            username='emp1_user',
            password='password123',
            email='john@workplace.local',
            employee=self.emp1
        )
        UserRole.objects.create(user=self.emp1_user, role=self.employee_role)

        self.emp2_user = User.objects.create_user(
            username='emp2_user',
            password='password123',
            email='jane@workplace.local',
            employee=self.emp2
        )
        UserRole.objects.create(user=self.emp2_user, role=self.employee_role)

    def test_user_roles(self):
        """Test User role helper methods resolve correctly."""
        self.assertTrue(self.admin_user.is_admin())
        self.assertFalse(self.admin_user.is_hr())
        self.assertFalse(self.admin_user.is_employee_role())

        self.assertTrue(self.hr_user.is_hr())
        self.assertTrue(self.emp1_user.is_employee_role())

    def test_unauthenticated_redirect(self):
        """Test unauthenticated requests are redirected to login."""
        response = self.client.get(reverse('employees:employee_list'))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('employees:employee_list')}")

    def test_employee_unauthorized_access(self):
        """Test Employee-role user cannot access HR-only pages (returns 403)."""
        self.client.login(username='emp1_user', password='password123')
        
        # Accessing employee CRUD listing (employee list is gated for standalone Employee users who must be redirected to self profile)
        response = self.client.get(reverse('employees:employee_list'))
        self.assertEqual(response.status_code, 302) # Redirect to my_profile
        
        # Accessing employee creation page (HR required) should fail with 403 (PermissionDenied)
        response = self.client.get(reverse('employees:employee_create'))
        self.assertEqual(response.status_code, 403)
        
        # Accessing payroll list (HR required) should return 403
        response = self.client.get(reverse('payroll:payroll_list'))
        self.assertEqual(response.status_code, 403)

    def test_employee_data_isolation(self):
        """Test Employee-role user cannot view details of other employees."""
        self.client.login(username='emp1_user', password='password123')
        
        # View own employee details (Allowed)
        response = self.client.get(reverse('employees:employee_detail', args=[self.emp1.id]))
        self.assertEqual(response.status_code, 200)

        # View other employee details (PermissionDenied - 403)
        response = self.client.get(reverse('employees:employee_detail', args=[self.emp2.id]))
        self.assertEqual(response.status_code, 403)

    def test_hr_authorized_access(self):
        """Test HR Manager role can view CRUD screens without denial."""
        self.client.login(username='hr_user', password='password123')
        
        response = self.client.get(reverse('employees:employee_list'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('employees:employee_create'))
        self.assertEqual(response.status_code, 200)

    def test_leave_type_permissions(self):
        """Test Employee can view leave types but cannot create, edit, or delete them."""
        leave_type = LeaveType.objects.create(name='Annual Leave', max_days_per_year=15)

        # 1. Employee login
        self.client.login(username='emp1_user', password='password123')

        # Employee CAN view leave type list
        response = self.client.get(reverse('leave:type_list'))
        self.assertEqual(response.status_code, 200)

        # Employee CANNOT view/submit create leave type form
        response = self.client.get(reverse('leave:type_create'))
        self.assertEqual(response.status_code, 403)

        # Employee CANNOT view/submit edit leave type form
        response = self.client.get(reverse('leave:type_edit', args=[leave_type.id]))
        self.assertEqual(response.status_code, 403)

        # Employee CANNOT delete leave type
        response = self.client.get(reverse('leave:type_delete', args=[leave_type.id]))
        self.assertEqual(response.status_code, 403)

        # 2. HR login
        self.client.login(username='hr_user', password='password123')

        # HR CAN access leave type create, edit, and delete
        response = self.client.get(reverse('leave:type_create'))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('leave:type_edit', args=[leave_type.id]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('leave:type_delete', args=[leave_type.id]))
        self.assertEqual(response.status_code, 200)

    def test_hr_cannot_generate_own_payslip(self):
        """Test HR Manager cannot generate their own payment slip or edit their own payroll record."""
        self.client.login(username='hr_user', password='password123')

        # 1. Opening payroll_create form excludes HR's own employee record from choices
        response = self.client.get(reverse('payroll:payroll_create'))
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertNotIn(self.hr_emp, form.fields['employee'].queryset)

        # 2. Passing HR's own employee ID via query param redirects with error
        response = self.client.get(f"{reverse('payroll:payroll_create')}?employee={self.hr_emp.id}")
        self.assertRedirects(response, reverse('payroll:payroll_list'))

        # 3. Submitting POST with HR's own employee ID fails choice validation
        response = self.client.post(reverse('payroll:payroll_create'), {
            'employee': self.hr_emp.id,
            'month': '2026-08',
            'basic_salary': '70000',
            'allowances': '0',
            'deductions': '0',
            'payment_status': 'pending',
        })
        self.assertFormError(response.context['form'], 'employee', 'Select a valid choice. That choice is not one of the available choices.')

        # 4. Generating payslip for another employee works and displays target employee's name
        response = self.client.post(reverse('payroll:payroll_create'), {
            'employee': self.emp1.id,
            'month': '2026-08',
            'basic_salary': '50000',
            'allowances': '1000',
            'deductions': '500',
            'payment_status': 'pending',
        }, follow=True)
        self.assertContains(response, f'Payroll record created successfully for {self.emp1.full_name}.')

    def test_admin_profile_update(self):
        """Test Admin can view and update their own profile."""
        self.client.login(username='admin_user', password='password123')

        # Admin can view profile
        response = self.client.get(reverse('employees:my_profile'))
        self.assertEqual(response.status_code, 200)

        # Admin can view edit profile page
        response = self.client.get(reverse('employees:edit_my_profile'))
        self.assertEqual(response.status_code, 200)

        # Admin can submit update
        response = self.client.post(reverse('employees:edit_my_profile'), {
            'first_name': 'Super',
            'last_name': 'Admin',
            'phone': '+1999888777',
            'address': 'Headquarters Suite 101',
            'gender': 'male',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your profile has been updated successfully.')

        # Verify employee and user object are updated
        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.first_name, 'Super')
        self.assertEqual(self.admin_user.last_name, 'Admin')
        self.assertEqual(self.admin_user.employee.phone, '+1999888777')
        self.assertEqual(self.admin_user.employee.address, 'Headquarters Suite 101')

    def test_signup_defaults_to_employee_role(self):
        """Test public registration strictly assigns Employee role and cannot self-assign Admin or HR."""
        response = self.client.post(reverse('accounts:register'), {
            'username': 'new_candidate',
            'email': 'candidate@workplace.local',
            'first_name': 'Candidate',
            'last_name': 'User',
            'password': 'StrongPassword123!',
            'password_confirm': 'StrongPassword123!',
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        # Retrieve new user
        new_user = User.objects.get(username='new_candidate')
        self.assertTrue(new_user.is_employee_role())
        self.assertFalse(new_user.is_hr())
        self.assertFalse(new_user.is_admin())
        self.assertIsNotNone(new_user.employee)

    def test_role_request_workflow_approve(self):
        """Test Employee can request HR role and Admin can approve it."""
        from apps.accounts.models import RoleRequest

        # 1. Employee submits role request
        self.client.login(username='emp1_user', password='password123')
        response = self.client.post(reverse('accounts:my_role_requests'), {
            'requested_role': self.hr_role.id,
            'reason': 'Transferred to People Operations department.',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'privileges has been submitted for Admin review.')

        # Verify RoleRequest created
        role_req = RoleRequest.objects.get(user=self.emp1_user, requested_role=self.hr_role)
        self.assertEqual(role_req.status, 'pending')

        # 2. Non-admin cannot review/approve (403)
        self.client.login(username='emp2_user', password='password123')
        response = self.client.get(reverse('accounts:admin_role_request_list'))
        self.assertEqual(response.status_code, 403)

        # 3. Admin logs in and reviews the request
        self.client.login(username='admin_user', password='password123')
        response = self.client.get(reverse('accounts:admin_role_request_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'emp1_user')

        # Admin approves the request
        response = self.client.post(reverse('accounts:admin_role_request_review', args=[role_req.id]), {
            'action': 'approve',
            'admin_remarks': 'Approved per executive transfer order.',
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify RoleRequest status is approved
        role_req.refresh_from_db()
        self.assertEqual(role_req.status, 'approved')
        self.assertEqual(role_req.reviewed_by, self.admin_user)
        self.assertEqual(role_req.admin_remarks, 'Approved per executive transfer order.')

        # Verify emp1_user is now HR role
        self.emp1_user.refresh_from_db()
        self.assertTrue(self.emp1_user.is_hr())

    def test_role_request_workflow_reject(self):
        """Test Admin can reject a role request with remarks."""
        from apps.accounts.models import RoleRequest

        # 1. Employee submits role request for Admin
        self.client.login(username='emp2_user', password='password123')
        self.client.post(reverse('accounts:my_role_requests'), {
            'requested_role': self.admin_role.id,
            'reason': 'Need system access.',
        })
        role_req = RoleRequest.objects.get(user=self.emp2_user, requested_role=self.admin_role)

        # 2. Admin rejects request
        self.client.login(username='admin_user', password='password123')
        response = self.client.post(reverse('accounts:admin_role_request_review', args=[role_req.id]), {
            'action': 'reject',
            'admin_remarks': 'Administrative access requires senior management clearance.',
        }, follow=True)
        self.assertEqual(response.status_code, 200)

        self.emp2_user.refresh_from_db()
        self.assertFalse(self.emp2_user.is_admin())
        self.assertTrue(self.emp2_user.is_employee_role())

    def test_email_login_and_validation(self):
        """Test logging in with email address (e.g. gmail/yahoo) and email format validation."""
        # Create user with gmail address
        gmail_user = User.objects.create_user(
            username='gmail_user',
            password='secretpassword123',
            email='testuser@gmail.com'
        )
        UserRole.objects.create(user=gmail_user, role=self.employee_role)

        # Login using email address instead of username
        login_res = self.client.post(reverse('accounts:login'), {
            'username': 'testuser@gmail.com',
            'password': 'secretpassword123',
        })
        self.assertEqual(login_res.status_code, 302)

        # Logout user before testing public sign-up form validation
        self.client.logout()

        # Registration with invalid email format should fail
        reg_fail = self.client.post(reverse('accounts:register'), {
            'username': 'invalid_email_user',
            'email': 'not_an_email',
            'password': 'password123',
            'password_confirm': 'password123',
        })
        self.assertEqual(reg_fail.status_code, 200)
        self.assertFormError(reg_fail.context['form'], 'email', 'Enter a valid email address.')



        # Registration with valid yahoo.com email should succeed
        reg_success = self.client.post(reverse('accounts:register'), {
            'username': 'yahoo_user',
            'email': 'myuser@yahoo.com',
            'first_name': 'Yahoo',
            'last_name': 'User',
            'password': 'password123',
            'password_confirm': 'password123',
        })
        self.assertEqual(reg_success.status_code, 302)
        self.assertTrue(User.objects.filter(email='myuser@yahoo.com').exists())

    def test_forgot_password_workflow(self):
        """Test complete Forgot Password workflow via email reset link."""
        from django.core import mail

        # 1. Request password reset with registered email address
        response = self.client.post(reverse('accounts:forgot_password'), {
            'email': 'admin@workplace.local'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:forgot_password_done'))

        # Verify reset email was sent to console backend
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('admin@workplace.local', mail.outbox[0].to)
        self.assertIn('Password Reset Request', mail.outbox[0].subject)

        # Extract dev reset link from session
        reset_link_dev = self.client.session.get('reset_link_dev')
        self.assertIsNotNone(reset_link_dev)

        # 2. Access password reset confirm page via link
        confirm_get = self.client.get(reset_link_dev)
        self.assertEqual(confirm_get.status_code, 200)
        self.assertTrue(confirm_get.context['validlink'])

        # 3. Submit new password
        confirm_post = self.client.post(reset_link_dev, {
            'new_password': 'newbrandpassword123',
            'new_password_confirm': 'newbrandpassword123',
        })
        self.assertEqual(confirm_post.status_code, 302)

        # 4. Login with newly set password
        login_res = self.client.post(reverse('accounts:login'), {
            'username': 'admin_user',
            'password': 'newbrandpassword123',
        })
        self.assertEqual(login_res.status_code, 302)




