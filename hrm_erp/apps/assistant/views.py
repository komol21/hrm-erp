import json
import logging
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.conf import settings

from .models import ChatSession, ChatMessage
from .services.gemini_service import generate_gemini_response

logger = logging.getLogger(__name__)


@login_required
def chat_page_view(request):
    """
    Main interactive HR AI Assistant page.
    Renders the chat interface with message history and quick prompt suggestions.
    """
    # Get or create the user's active session
    session = ChatSession.objects.filter(user=request.user).first()
    if not session:
        session = ChatSession.objects.create(
            user=request.user,
            title='HR Assistant Session'
        )

    messages = session.messages.all().order_by('created_at')[:40]
    model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash')
    has_api_key = bool(getattr(settings, 'GEMINI_API_KEY', '').strip())

    return render(request, 'assistant/chat.html', {
        'page_title': 'TalentCore HR AI Assistant',
        'session': session,
        'messages': messages,
        'model_name': model_name,
        'has_api_key': has_api_key,
    })


@login_required
@require_POST
def api_send_message(request):
    """
    AJAX endpoint to send a message to the HR AI Assistant.
    Expects JSON: { "message": "..." }
    """
    try:
        body = json.loads(request.body)
        user_message = body.get('message', '').strip()
    except (json.JSONDecodeError, ValueError):
        user_message = request.POST.get('message', '').strip()

    if not user_message:
        return JsonResponse({'success': False, 'error': 'Please enter a message.'}, status=400)

    # Fetch or create active session
    session = ChatSession.objects.filter(user=request.user).first()
    if not session:
        session = ChatSession.objects.create(user=request.user)

    # 1. Save user message to database
    ChatMessage.objects.create(
        session=session,
        role='user',
        content=user_message
    )

    # 2. Build short history context for multi-turn conversation
    history_records = session.messages.order_by('-created_at')[1:9]
    chat_history = [
        {'role': m.role, 'content': m.content}
        for m in reversed(list(history_records))
    ]

    # 3. Call Gemini service
    try:
        result = generate_gemini_response(
            user=request.user,
            user_message=user_message,
            chat_history=chat_history
        )
        reply_content = result.get('reply', '')
        is_simulation = result.get('is_simulation', False)
        model_used = result.get('model', 'gemini-1.5-flash')

        # 4. Save assistant response
        ChatMessage.objects.create(
            session=session,
            role='assistant',
            content=reply_content
        )

        return JsonResponse({
            'success': True,
            'reply': reply_content,
            'is_simulation': is_simulation,
            'model': model_used
        })

    except Exception as e:
        logger.error("Error in AI assistant message handler: %s", e, exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f"Failed to generate response: {str(e)}"
        }, status=500)


@login_required
@require_POST
def api_clear_chat(request):
    """Clear conversation history for the current user."""
    session = ChatSession.objects.filter(user=request.user).first()
    if session:
        session.messages.all().delete()
        session.delete()

    return JsonResponse({'success': True, 'message': 'Conversation history cleared.'})
