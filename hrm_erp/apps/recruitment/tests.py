import io
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

from apps.accounts.models import Role, UserRole
from apps.organization.models import Department
from apps.recruitment.models import (
    JobVacancy, Candidate, CandidateCV, CVAnalysis, MatchedSkill, MissingSkill
)
from apps.recruitment.services.cv_extractor import (
    validate_cv_file, sanitize_text, extract_cv_text, CVExtractionError
)
from apps.recruitment.services.ai_analyzer import (
    analyze_cv_with_ai, _generate_simulation_analysis
)

User = get_user_model()


class RecruitmentTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Create Roles
        self.admin_role = Role.objects.create(name='Admin', description='Admin')
        self.hr_role = Role.objects.create(name='HR', description='HR')
        self.employee_role = Role.objects.create(name='Employee', description='Employee')

        # 2. Create Users
        self.admin_user = User.objects.create_user(
            username='recruitment_admin',
            email='rec_admin@workplace.local',
            password='password123'
        )
        UserRole.objects.create(user=self.admin_user, role=self.admin_role)

        self.hr_user = User.objects.create_user(
            username='recruitment_hr',
            email='rec_hr@workplace.local',
            password='password123'
        )
        UserRole.objects.create(user=self.hr_user, role=self.hr_role)

        self.employee_user = User.objects.create_user(
            username='recruitment_emp',
            email='rec_emp@workplace.local',
            password='password123'
        )
        UserRole.objects.create(user=self.employee_user, role=self.employee_role)

        # 3. Create Department & Job Vacancy
        self.dept = Department.objects.create(name='Engineering', description='Tech team')
        self.vacancy = JobVacancy.objects.create(
            title='Senior Backend Engineer',
            department=self.dept,
            description='Build and maintain Django applications and microservices.',
            required_skills='Python, Django, PostgreSQL, REST APIs',
            preferred_skills='Docker, AWS, Kubernetes',
            required_experience_years=3,
            educational_requirements='B.Sc. in Computer Science',
            status='open',
            created_by=self.hr_user
        )

    def test_role_access_control(self):
        """Test HR and Admin can access recruitment pages, while Employees receive 403 Forbidden."""
        # Unauthenticated -> redirect to login
        res = self.client.get(reverse('recruitment:vacancy_list'))
        self.assertEqual(res.status_code, 302)

        # Employee -> 403 Forbidden
        self.client.login(username='recruitment_emp', password='password123')
        res = self.client.get(reverse('recruitment:vacancy_list'))
        self.assertEqual(res.status_code, 403)
        res_cv = self.client.get(reverse('recruitment:cv_analysis'))
        self.assertEqual(res_cv.status_code, 403)

        # HR -> 200 OK
        self.client.login(username='recruitment_hr', password='password123')
        res_hr = self.client.get(reverse('recruitment:vacancy_list'))
        self.assertEqual(res_hr.status_code, 200)
        res_hr_cv = self.client.get(reverse('recruitment:cv_analysis'))
        self.assertEqual(res_hr_cv.status_code, 200)

        # Admin -> 200 OK
        self.client.login(username='recruitment_admin', password='password123')
        res_admin = self.client.get(reverse('recruitment:vacancy_list'))
        self.assertEqual(res_admin.status_code, 200)

    def test_job_vacancy_crud(self):
        """Test Job Vacancy creation, editing, and deletion."""
        self.client.login(username='recruitment_hr', password='password123')

        # Create
        res = self.client.post(reverse('recruitment:vacancy_create'), {
            'title': 'Frontend React Developer',
            'department': self.dept.id,
            'description': 'Develop user interfaces with React and TailwindCSS.',
            'required_skills': 'JavaScript, React, CSS, HTML5',
            'preferred_skills': 'TypeScript, Next.js',
            'required_experience_years': 2,
            'educational_requirements': 'Bachelor Degree',
            'status': 'open',
        })
        self.assertEqual(res.status_code, 302)
        created = JobVacancy.objects.get(title='Frontend React Developer')
        self.assertEqual(created.required_experience_years, 2)

        # Edit
        res_edit = self.client.post(reverse('recruitment:vacancy_edit', args=[created.id]), {
            'title': 'Lead React Developer',
            'department': self.dept.id,
            'description': 'Lead UI team.',
            'required_skills': 'JavaScript, React, TypeScript',
            'preferred_skills': 'Next.js',
            'required_experience_years': 4,
            'educational_requirements': 'Bachelor Degree',
            'status': 'open',
        })
        self.assertEqual(res_edit.status_code, 302)
        created.refresh_from_db()
        self.assertEqual(created.title, 'Lead React Developer')
        self.assertEqual(created.required_experience_years, 4)

        # Delete
        res_del = self.client.post(reverse('recruitment:vacancy_delete', args=[created.id]))
        self.assertEqual(res_del.status_code, 302)
        self.assertFalse(JobVacancy.objects.filter(id=created.id).exists())

    def test_cv_file_validation_and_sanitization(self):
        """Test file size and extension restrictions, and text sanitization."""
        # Disallowed extension
        bad_file = SimpleUploadedFile("resume.exe", b"binary content", content_type="application/octet-stream")
        with self.assertRaises(CVExtractionError):
            validate_cv_file(bad_file)

        # Sanitization
        raw_text = "Software Engineer\x00\x08 with Python\n\n\n\nand Django skills."
        clean = sanitize_text(raw_text)
        self.assertNotIn("\x00", clean)
        self.assertIn("Python", clean)

    def test_ai_simulation_analyzer(self):
        """Test heuristic AI simulation analyzer output matches required schema."""
        cv_text = """
        Alex Morgan - Software Developer
        Experience: 4 years working with Python, Django, PostgreSQL, and REST APIs.
        Education: B.Sc. in Computer Science.
        Skills: Python, Django, PostgreSQL, REST APIs, Git.
        """
        analysis_data = _generate_simulation_analysis(self.vacancy, cv_text)

        self.assertIn("match_score", analysis_data)
        self.assertIn("recommendation", analysis_data)
        self.assertIn("matched_skills", analysis_data)
        self.assertIn("missing_skills", analysis_data)
        self.assertIn("experience", analysis_data)
        self.assertIn("education", analysis_data)
        self.assertIn("strengths", analysis_data)
        self.assertIn("missing_requirements", analysis_data)

        # Verify matched skills
        matched_names = [m["skill"] for m in analysis_data["matched_skills"]]
        self.assertIn("Python", matched_names)
        self.assertIn("Django", matched_names)
        self.assertTrue(analysis_data["match_score"] >= 50)

    def test_api_cv_analysis_endpoint(self):
        """Test POST /api/hr/cv-analysis/ endpoint processes uploads and saves analysis records."""
        self.client.login(username='recruitment_hr', password='password123')

        # Create a sample PDF file in memory
        pdf_file = SimpleUploadedFile(
            "alex_resume.pdf",
            b"%PDF-1.4 sample pdf content with text for testing",
            content_type="application/pdf"
        )

        # Mock the extract_cv_text to return sample text
        from unittest.mock import patch
        with patch('apps.recruitment.views.extract_cv_text') as mock_extract:
            mock_extract.return_value = "Experienced Python & Django developer with 4 years building APIs and PostgreSQL databases."

            response = self.client.post('/api/hr/cv-analysis/', {
                'job_vacancy': self.vacancy.id,
                'candidate_name': 'Alex Morgan',
                'candidate_email': 'alex.morgan@example.com',
                'cv_file': pdf_file
            })

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data['success'])
            self.assertEqual(data['job_title'], self.vacancy.title)
            self.assertEqual(data['candidate_name'], 'Alex Morgan')
            self.assertIn('result', data)

            # Verify database persistence
            analysis_id = data['analysis_id']
            analysis_obj = CVAnalysis.objects.get(id=analysis_id)
            self.assertEqual(analysis_obj.candidate_cv.job_vacancy, self.vacancy)
            self.assertEqual(analysis_obj.candidate_cv.candidate.name, 'Alex Morgan')
            self.assertTrue(analysis_obj.matched_skills.exists())

    def test_analysis_detail_and_history_views(self):
        """Test detail report and history list views."""
        self.client.login(username='recruitment_hr', password='password123')

        # Create sample analysis in database
        candidate = Candidate.objects.create(name='Taylor Swift', email='taylor@example.com')
        cv = CandidateCV.objects.create(
            candidate=candidate,
            job_vacancy=self.vacancy,
            cv_file='cv_uploads/sample.pdf',
            file_name='sample.pdf',
            extracted_text='Python Django developer'
        )
        analysis = CVAnalysis.objects.create(
            candidate_cv=cv,
            match_score=88,
            recommendation='Strong Match',
            experience_relevant_years=4,
            experience_meets_requirement=True,
            education_qualification='B.Sc. in Computer Science',
            education_meets_requirement=True,
            strengths=['Solid Django knowledge'],
            missing_requirements=[]
        )
        MatchedSkill.objects.create(analysis=analysis, skill='Python', level='Strong')
        MissingSkill.objects.create(analysis=analysis, skill='Docker')

        # Detail view
        res_detail = self.client.get(reverse('recruitment:analysis_detail', args=[analysis.id]))
        self.assertEqual(res_detail.status_code, 200)
        self.assertContains(res_detail, '88%')
        self.assertContains(res_detail, 'Strong Match')
        self.assertContains(res_detail, 'Python')

        # History view
        res_history = self.client.get(reverse('recruitment:analysis_history'))
        self.assertEqual(res_history.status_code, 200)
        self.assertContains(res_history, 'Taylor Swift')

    def test_batch_cv_analysis_endpoint(self):
        """Test POST /api/hr/cv-analysis/batch/ analyzes multiple CV files at once."""
        self.client.login(username='recruitment_hr', password='password123')

        file1 = SimpleUploadedFile("alice_smith_cv.pdf", b"%PDF-1.4 alice content", content_type="application/pdf")
        file2 = SimpleUploadedFile("bob_jones_resume.docx", b"PK\x03\x04 bob docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        from unittest.mock import patch
        with patch('apps.recruitment.views.extract_cv_text') as mock_extract:
            mock_extract.side_effect = [
                "Alice Smith. Email: alice@example.com. Senior Python Django Engineer with 5 years experience.",
                "Bob Jones. Email: bob@example.com. Junior web developer with HTML and CSS."
            ]

            response = self.client.post('/api/hr/cv-analysis/batch/', {
                'job_vacancy': self.vacancy.id,
                'cv_files': [file1, file2]
            })

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data['success'])
            self.assertEqual(data['total_processed'], 2)
            self.assertEqual(len(data['results']), 2)
            # Ranked from highest to lowest score
            self.assertTrue(data['results'][0]['match_score'] >= data['results'][1]['match_score'])

    def test_extract_candidate_name_and_email(self):
        """Test auto-extracting candidate name from filename and email from text."""
        from apps.recruitment.services.cv_extractor import (
            extract_candidate_name_from_filename,
            extract_candidate_email_from_text,
        )
        self.assertEqual(extract_candidate_name_from_filename("john_doe_resume_2026.pdf"), "John Doe")
        self.assertEqual(extract_candidate_name_from_filename("sarah-khan-cv.docx"), "Sarah Khan")
        self.assertEqual(extract_candidate_email_from_text("Contact: test.candidate@gmail.com for inquiries"), "test.candidate@gmail.com")
