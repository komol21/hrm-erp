from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from unittest.mock import patch, MagicMock

from .models import ChatSession, ChatMessage
from .services.gemini_service import build_system_context, generate_gemini_response
from apps.attendance.models import AttendancePolicy
from apps.leave_management.models import LeaveType

User = get_user_model()


class AssistantTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='test_hr_user',
            email='hr@talentcore.local',
            password='password123'
        )

        # Setup attendance policy & leave type for context tests
        self.policy = AttendancePolicy.get_active_policy()
        self.policy.grace_period_minutes = 20
        self.policy.save()

        self.leave_type = LeaveType.objects.create(
            name='Special Training Leave',
            max_days_per_year=5
        )

    def test_unauthenticated_access_redirects(self):
        """Test unauthenticated requests are redirected to login."""
        response = self.client.get(reverse('assistant:chat'))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_can_access_chat_view(self):
        """Test logged in user can access HR AI Assistant chat page."""
        self.client.login(username='test_hr_user', password='password123')
        response = self.client.get(reverse('assistant:chat'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TalentCore HR AI Copilot')

    def test_company_context_builder(self):
        """Test build_system_context incorporates company policies and user data."""
        context_str = build_system_context(self.user)
        self.assertIn('20 minutes', context_str)
        self.assertIn('Special Training Leave', context_str)
        self.assertIn('test_hr_user', context_str)

    def test_api_send_message_simulation_fallback(self):
        """Test message sending generates intelligent fallback response and persists messages."""
        self.client.login(username='test_hr_user', password='password123')

        response = self.client.post(
            reverse('assistant:api_send_message'),
            data={'message': 'What is our company leave policy?'},
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('Special Training Leave', data['reply'])
        self.assertTrue(data['is_simulation'])

        # Check database records
        session = ChatSession.objects.filter(user=self.user).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.messages.count(), 2)
        self.assertEqual(session.messages.filter(role='user').count(), 1)
        self.assertEqual(session.messages.filter(role='assistant').count(), 1)

    def test_api_clear_chat(self):
        """Test clearing chat history removes session messages."""
        self.client.login(username='test_hr_user', password='password123')

        session = ChatSession.objects.create(user=self.user)
        ChatMessage.objects.create(session=session, role='user', content='Hello')
        ChatMessage.objects.create(session=session, role='assistant', content='Hi')

        response = self.client.post(reverse('assistant:api_clear_chat'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ChatMessage.objects.filter(session=session).count(), 0)

    @patch('requests.post')
    def test_mock_gemini_api_call(self, mock_post):
        """Test calling Gemini REST API when key is configured."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{'text': 'Here is a custom response from Google Gemini 1.5 Flash.'}]
                }
            }]
        }
        mock_post.return_value = mock_response

        with self.settings(GEMINI_API_KEY='fake-gemini-test-key-12345'):
            res = generate_gemini_response(self.user, 'Explain our working hours')
            self.assertFalse(res['is_simulation'])
            self.assertIn('Google Gemini', res['reply'])
