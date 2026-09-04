"""
Firebase Authentication views.

Handles server-side verification of Firebase ID tokens and
auto-creation/login of Django users for Google Sign-In.
"""

import json
from datetime import date

from django.contrib.auth import login
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .firebase_auth import verify_firebase_token
from .models import User, Role, UserRole
from apps.employees.models import Employee


@csrf_exempt
@require_POST
def firebase_google_login(request):
    """
    Receive a Firebase ID token from the client, verify it,
    and log the user into the Django session.

    If no Django user exists for the Google email, one is auto-created
    with a linked Employee profile and the default 'Employee' role —
    mirroring the standard registration flow.

    Request body (JSON):
        { "id_token": "<firebase-id-token>" }

    Response (JSON):
        Success: { "success": true, "redirect": "/dashboard/" }
        Error:   { "success": false, "error": "..." }
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse(
            {'success': False, 'error': 'Invalid request body.'},
            status=400,
        )

    id_token = body.get('id_token', '').strip()
    if not id_token:
        return JsonResponse(
            {'success': False, 'error': 'Missing id_token.'},
            status=400,
        )

    # Verify the Firebase ID token server-side
    decoded = verify_firebase_token(id_token)
    if decoded is None:
        return JsonResponse(
            {'success': False, 'error': 'Invalid or expired Firebase token.'},
            status=401,
        )

    email = decoded.get('email', '').lower().strip()
    if not email:
        return JsonResponse(
            {'success': False, 'error': 'Google account has no email address.'},
            status=400,
        )

    name = decoded.get('name', '')
    picture = decoded.get('picture', '')
    firebase_uid = decoded.get('uid', '')

    # Split display name into first/last
    name_parts = name.split(' ', 1) if name else ['']
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ''

    # Look up existing user by email
    user = User.objects.filter(email__iexact=email).first()

    if user is None:
        # Auto-create user — mirrors register_view logic
        # Generate a unique username from the email prefix
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.objects.filter(username__iexact=username).exists():
            username = f'{base_username}{counter}'
            counter += 1

        # Create Employee profile
        emp = Employee.objects.create(
            first_name=first_name or username,
            last_name=last_name or 'User',
            email=email,
            hire_date=date.today(),
            status='active',
            basic_salary=50000.00,
        )

        # Create User
        user = User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            employee=emp,
        )
        # Set an unusable password (Google-only auth)
        user.set_unusable_password()
        user.save()

        # Assign default Employee role
        employee_role, _ = Role.objects.get_or_create(
            name='Employee',
            defaults={'description': 'Standard employee self-service account.'},
        )
        UserRole.objects.create(user=user, role=employee_role)

    # Log the user into the Django session
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    
    from django.contrib import messages
    messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')

    return JsonResponse({
        'success': True,
        'redirect': '/dashboard/',
    })
