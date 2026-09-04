# ERP HRM Module — Task Tracker

## Phase 1 — Django Foundation & Environment Setup
- [x] Create virtual environment & install dependencies
- [x] Create Django project (`config/`) and 6 apps
- [x] Configure settings.py (apps, DB, static, media, auth)
- [x] Create .env, .gitignore, urls.py, wsgi/asgi

## Phase 2 — Models & Migrations
- [x] `accounts` models (User, Role, Permission, RolePermission, UserRole)
- [x] `organization` models (Department, Designation, Branch)
- [x] `employees` models (Employee)
- [x] `attendance` models (Attendance)
- [x] `leave_management` models (LeaveType, LeaveRequest)
- [x] `payroll` models (Payroll)
- [x] Run migrations successfully

## Phase 3 — Authentication
- [x] Login/logout views & forms
- [x] Login template (glassmorphism)
- [x] Seed admin management command
- [x] Role-based dashboard redirect

## Phase 4 — Authorization
- [x] permissions.py (has_role, decorators, mixins)
- [x] Context processors (role flags in templates)
- [x] Middleware (attach role info to request)

## Phase 5 — Base UI
- [x] base.html master template
- [x] Components (navbar, sidebar, messages, pagination, empty_state)
- [x] style.css (design system, glassmorphism)
- [x] responsive.css
- [x] theme.css (light/dark)
- [x] JS (theme-toggle, sidebar)

## Phase 6 — Organization Module
- [x] Department CRUD (views, forms, templates)
- [x] Designation CRUD (views, forms, templates)
- [x] Branch CRUD (views, forms, templates)

## Phase 7 — Employee Module
- [x] Employee list (search, filter)
- [x] Employee create/edit with photo upload
- [x] Employee detail view
- [x] Role-based access (own profile for Employee role)

## Phase 8 — Attendance Module
- [x] Check-in / check-out (self-service)
- [x] Attendance list with date filtering
- [x] Working hours / late / overtime calculation
- [x] Role-based access

## Phase 9 — Leave Module
- [x] Leave type management
- [x] Leave request submission
- [x] Review/approve/reject workflow
- [x] Employee history (own leaves only)

## Phase 10 — Payroll Module
- [x] Payroll CRUD with net salary calc
- [x] Employee self-service (view own payslips)
- [x] Filter by month/employee

## Phase 11 — Dashboards
- [x] Admin dashboard (system-wide stats)
- [x] HR dashboard (HR-wide stats)
- [x] Employee dashboard (own data + quick check-in)

## Phase 12 — Users/Roles/Permissions Management
- [x] User CRUD (Admin only)
- [x] Role/Permission management

## Phase 13 — Security & Testing
- [x] CSRF verification
- [x] Form validation
- [x] File upload validation
- [x] Data-isolation tests
- [x] Final runserver verification
