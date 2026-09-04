"""
Google Gemini AI service for HR AI Assistant.
Interacts with the Google Gemini REST API (gemini-1.5-flash) with dynamic company context injection.
Includes an intelligent local HR simulation fallback for offline development and testing.
"""

import json
import logging
import requests
from datetime import datetime
from django.conf import settings
from django.utils import timezone

from apps.attendance.models import AttendancePolicy
from apps.leave_management.models import LeaveType
from apps.organization.models import Department

logger = logging.getLogger(__name__)


def build_system_context(user):
    """
    Build structured company and user context to inject into Gemini's system instructions.
    Gives the AI assistant exact knowledge of company policies, departments, and user identity.
    """
    now = timezone.localtime()
    today_str = now.strftime('%A, %B %d, %Y')
    time_str = now.strftime('%I:%M %p')

    # 1. Company Attendance Policy
    try:
        policy = AttendancePolicy.get_active_policy()
        policy_info = (
            f"- Work Hours: {policy.work_start_time.strftime('%I:%M %p')} to {policy.work_end_time.strftime('%I:%M %p')}\n"
            f"- Late Grace Period: {policy.grace_period_minutes} minutes\n"
            f"- Standard Working Hours: {policy.standard_working_hours} hours/day\n"
            f"- Overtime Threshold: after {policy.overtime_threshold_hours} hours/day\n"
            f"- Policy Notes: {policy.notes}"
        )
    except Exception:
        policy_info = "- Standard Hours: 09:00 AM to 05:00 PM, 15 minutes grace period, 8.0 hours/day."

    # 2. Company Leave Types & Quotas
    try:
        leave_types = LeaveType.objects.all()
        leave_info_list = [f"- {lt.name}: {lt.max_days_per_year} days/year ({lt.description or 'Standard'})" for lt in leave_types]
        leave_info = "\n".join(leave_info_list) if leave_info_list else "- Annual Leave: 15 days, Sick Leave: 10 days, Casual Leave: 10 days"
    except Exception:
        leave_info = "- Annual Leave: 15 days, Sick Leave: 10 days, Casual Leave: 10 days"

    # 3. Departments
    try:
        depts = Department.objects.values_list('name', flat=True)
        depts_str = ", ".join(depts) if depts else "Engineering, Human Resources, Finance, Operations"
    except Exception:
        depts_str = "Engineering, Human Resources, Finance, Operations"

    # 4. User Role & Details
    user_roles = [r.name for r in user.roles.all()] if hasattr(user, 'roles') else []
    primary_role = user_roles[0] if user_roles else ('Admin' if user.is_superuser else 'Employee')
    emp = user.get_employee() if hasattr(user, 'get_employee') else None
    emp_name = emp.full_name if emp else user.get_full_name() or user.username
    emp_dept = emp.department.name if emp and emp.department else 'General'

    return f"""You are "TalentCore AI", an expert, helpful, and highly articulate HR AI Assistant & Co-pilot embedded inside an enterprise HRM ERP system.
Your mission is to assist employees, HR managers, and administrators with Human Resource tasks, company policy guidance, drafting formal HR documents, and talent acquisition advice.

CURRENT DATE & TIME:
- Today: {today_str}, {time_str} (Asia/Dhaka)

CURRENT USER CONTEXT:
- Name: {emp_name}
- System Role: {primary_role}
- Department: {emp_dept}

COMPANY POLICIES & CONTEXT:
1. Attendance & Work Timing Policy:
{policy_info}

2. Available Leave Types & Annual Entitlements:
{leave_info}

3. Organization Departments:
- {depts_str}

BEHAVIORAL & RESPONSE GUIDELINES:
1. Always be professional, empathetic, clear, and structured in your answers.
2. Use GitHub Flavored Markdown (bullet points, bold text, headings, and code/quote blocks) for readability.
3. When asked to draft documents (Offer Letters, Job Descriptions, Warning Letters, Announcement Emails, Policy Memos):
   - Produce complete, polished, and ready-to-use templates with placeholders like [Candidate Name], [Salary], [Start Date].
4. When asked about leave, attendance, or office hours, accurately reference the company policies listed above.
5. If the user asks about sensitive employee personal data or salaries of other employees, politely explain that such confidential information cannot be disclosed without authorization.
6. Provide concise, high-value answers without unnecessary fluff.
"""


def generate_gemini_response(user, user_message, chat_history=None):
    """
    Generate response from Google Gemini API with fallback simulation.

    Args:
        user: The Django User making the request.
        user_message: The prompt string.
        chat_history: Optional list of dicts: [{'role': 'user'|'assistant', 'content': '...'}]

    Returns:
        dict: {
            'reply': str,
            'is_simulation': bool,
            'model': str
        }
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '') or ''
    model = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash') or 'gemini-1.5-flash'

    system_instruction = build_system_context(user)

    # If API key is not configured, use local simulation
    if not api_key or api_key.strip() in ('your_gemini_api_key_here', 'your_api_key_here', ''):
        logger.info("GEMINI_API_KEY not configured. Falling back to local HR simulation.")
        return _generate_simulation_response(user, user_message)

    # Format history for Gemini API
    # Gemini accepts roles 'user' and 'model'
    contents = []
    if chat_history:
        for msg in chat_history[-8:]:  # Keep last 8 turns for token efficiency
            role = 'model' if msg.get('role') in ('assistant', 'model') else 'user'
            text = msg.get('content', '').strip()
            if text:
                contents.append({
                    'role': role,
                    'parts': [{'text': text}]
                })

    # Add current user message
    contents.append({
        'role': 'user',
        'parts': [{'text': user_message}]
    })

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        'systemInstruction': {
            'parts': [{'text': system_instruction}]
        },
        'contents': contents,
        'generationConfig': {
            'temperature': 0.4,
            'maxOutputTokens': 2048,
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        if response.status_code == 200:
            data = response.json()
            candidates = data.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                if parts:
                    reply_text = parts[0].get('text', '')
                    return {
                        'reply': reply_text,
                        'is_simulation': False,
                        'model': model
                    }
            return {
                'reply': "I received an empty response from Gemini. Please rephrase your question.",
                'is_simulation': False,
                'model': model
            }
        else:
            logger.warning("Gemini API error %s: %s", response.status_code, response.text)
            return _generate_simulation_response(user, user_message)

    except Exception as err:
        logger.error("Failed to connect to Google Gemini API: %s", err)
        return _generate_simulation_response(user, user_message)


def _generate_simulation_response(user, message):
    """
    Intelligent heuristic fallback response generator when Gemini API key is offline or in test environments.
    """
    msg_lower = message.lower()
    emp = user.get_employee() if hasattr(user, 'get_employee') else None
    name = emp.full_name if emp else user.get_full_name() or user.username

    # 1. Leave Policy Query
    if any(k in msg_lower for k in ['leave', 'vacation', 'sick leave', 'annual leave', 'chuti', 'day off']):
        try:
            leave_types = LeaveType.objects.all()
            leave_bullets = "\n".join([f"- **{lt.name}**: {lt.max_days_per_year} days per calendar year" for lt in leave_types])
        except Exception:
            leave_bullets = "- **Annual Leave**: 15 days\n- **Sick Leave**: 10 days\n- **Casual Leave**: 10 days"

        reply = f"""Hello **{name}**, here is our company's active leave entitlement summary:

### 🌴 Company Leave Policy
{leave_bullets}

#### Key Guidelines:
1. **Application**: Apply at least **2 days in advance** for planned leaves via the **Leave Management** module.
2. **Medical Leaves**: Requires a valid doctor's prescription if exceeding 2 consecutive days.
3. **Approval**: Leaves are reviewed by your designated HR Manager or Line Manager.

Would you like me to help you draft a leave application or check anything else?"""

    # 2. Attendance & Office Timing
    elif any(k in msg_lower for k in ['attendance', 'timing', 'office hour', 'work hour', 'overtime', 'late', 'grace']):
        try:
            policy = AttendancePolicy.get_active_policy()
            start = policy.work_start_time.strftime('%I:%M %p')
            end = policy.work_end_time.strftime('%I:%M %p')
            grace = policy.grace_period_minutes
            ot = policy.overtime_threshold_hours
        except Exception:
            start, end, grace, ot = '09:00 AM', '05:00 PM', 15, 8.0

        reply = f"""Hello **{name}**, here are our company's standard working and attendance regulations:

### ⏱️ Office Hours & Attendance Policy
- **Standard Working Hours**: **{start}** to **{end}** (Monday to Friday).
- **Grace Period**: Up to **{grace} minutes** after {start}. Check-ins after this are logged as **Late Arrival**.
- **Overtime Calculation**: Any recorded work exceeding **{ot} hours/day** is automatically computed into monthly overtime pay.
- **Check-in / Check-out**: You can clock in directly from the **Self Service > My Attendance** portal.

Let me know if you need assistance submitting an attendance correction or comment!"""

    # 3. Draft Job Description
    elif any(k in msg_lower for k in ['job description', 'jd', 'hire', 'vacancy', 'job opening']):
        role_match = "Software Engineer"
        for candidate_role in ["python developer", "django developer", "hr manager", "accountant", "product manager", "frontend developer", "full stack"]:
            if candidate_role in msg_lower:
                role_match = candidate_role.title()
                break

        reply = f"""Here is a professionally structured Job Description template for a **{role_match}**:

---

# Job Title: {role_match}
**Department:** Engineering / Operations  
**Employment Type:** Full-time  
**Location:** Dhaka, Bangladesh (On-site / Hybrid)

### 📌 Role Overview
We are seeking a talented and proactive **{role_match}** to join our fast-growing team. In this role, you will collaborate with cross-functional teams to build, scale, and maintain high-impact solutions.

### 🎯 Key Responsibilities
- Architect, build, and maintain robust and scalable applications.
- Collaborate with product managers, designers, and team members to translate business requirements into technical implementations.
- Write clean, well-tested, and maintainable code adhering to industry standards.
- Participate in code reviews and mentor junior engineering staff.

### 🛠️ Required Qualifications
- Bachelor's Degree in Computer Science, Software Engineering, or related discipline.
- 2–5 years of demonstrated relevant hands-on industry experience.
- Strong proficiency in modern frameworks and relational database design (PostgreSQL/MySQL).
- Familiarity with RESTful APIs, Git version control, and CI/CD pipelines.

### 🌟 What We Offer
- Competitive monthly compensation package with performance bonuses.
- Comprehensive health insurance and annual festival bonuses.
- Generous annual paid leave and collaborative work culture.

---

*Tip: You can copy and paste this directly into our **Recruitment > Create Job Vacancy** form!*"""

    # 4. Draft Offer Letter
    elif any(k in msg_lower for k in ['offer letter', 'appointment letter', 'job offer']):
        reply = f"""Here is a standard, formal **Job Offer Letter** template:

---

**Date:** {timezone.localtime().strftime('%B %d, %Y')}  

**To:**  
[Candidate Full Name]  
[Candidate Address / Email]  

**Subject: Offer of Employment — [Job Title]**

Dear [Candidate Name],

On behalf of TalentCore Enterprises, we are pleased to offer you the position of **[Job Title]** in the **[Department]** department.

### 📋 Key Employment Terms:
- **Designation:** [Job Title]
- **Reporting To:** [Hiring Manager / Line Manager]
- **Start Date:** [Commencement Date]
- **Gross Monthly Salary:** ৳[Salary Amount] (subject to standard statutory deductions)
- **Working Hours:** 09:00 AM to 05:00 PM, Sunday through Thursday.
- **Probationary Period:** 3 months from the date of joining.

Please review the attached employment agreement. To confirm your acceptance, kindly sign and return a copy of this letter by **[Expiry Date]**.

We look forward to welcoming you to our team!

Sincerely,  
**[Your Name / HR Department]**  
Human Resources Department  
TalentCore HRM ERP

---"""

    # 5. Interview Questions
    elif any(k in msg_lower for k in ['interview question', 'questions for', 'interview']):
        reply = f"""Here is a curated set of **Technical & Behavioral Interview Questions**:

### 1. Role-Specific Technical Questions
1. *“Can you explain your approach to designing scalable RESTful APIs with relational database backends?”*
2. *“How do you handle database migration and schema changes in a production environment with high traffic?”*
3. *“What strategy do you use for caching and optimizing database query performance?”*

### 2. Behavioral & Situational Questions (STAR Method)
1. *“Describe a situation where a project deadline was at risk. How did you prioritize tasks and communicate with stakeholders?”*
2. *“Can you share an experience where you had a technical disagreement with a team member and how you resolved it?”*
3. *“Tell us about a critical production bug you introduced or encountered and the step-by-step resolution process.”*

### 3. Culture Fit & Problem Solving
1. *“How do you stay updated with emerging technologies and best practices in your field?”*
2. *“What kind of team environment allows you to do your best work?”*

Feel free to ask me if you want questions tailored to a specific role!"""

    # 6. Default Fallback
    else:
        reply = f"""Hello **{name}**! I am your **TalentCore HR AI Copilot**.

I can assist you with:
- 📋 **Company Policies**: Inquire about leave entitlements, office hours, and overtime rules.
- 📝 **HR Document Generation**: Draft Job Descriptions, Offer Letters, Warning Notices, and Announcement emails.
- 🎯 **Recruitment & Hiring**: Generate role-specific interview questionnaires and screening criteria.
- 💼 **HR Workflow Guidance**: Explain self-service procedures for attendance corrections and leave applications.

How can I assist you today?"""

    return {
        'reply': reply,
        'is_simulation': True,
        'model': 'local-hr-copilot'
    }
