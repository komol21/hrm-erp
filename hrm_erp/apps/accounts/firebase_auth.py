"""
Firebase token verification utilities.

Verifies Firebase ID tokens returned by the client-side Firebase SDK.
Uses Google's public certificate verification (google.oauth2.id_token)
and Firebase Identity Toolkit API so that authentication works seamlessly
without requiring a local service account key file, while still supporting
firebase-admin service account keys if provided.
"""

import logging
import requests
from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

logger = logging.getLogger(__name__)

FIREBASE_PROJECT_ID = 'talent-core-1b5f7'
FIREBASE_API_KEY = 'AIzaSyBNRCU8kT_vVYmvZ2_-wWbKRwhsjGurgSM'

_request_adapter = None


def _get_request_adapter():
    global _request_adapter
    if _request_adapter is None:
        _request_adapter = google_requests.Request()
    return _request_adapter


def verify_firebase_token(id_token):
    """
    Verify a Firebase ID token and return decoded claims.

    Tries multiple verification strategies in order:
    1. Direct public certificate verification via google.oauth2.id_token (fast, offline-cached, no credentials needed)
    2. Google Identity Toolkit REST API (accounts:lookup with API key)
    3. firebase_admin SDK (if service account key is configured)

    Returns:
        dict or None: Decoded user info with keys:
                      'uid', 'email', 'name', 'picture'
    """
    if not id_token or not isinstance(id_token, str):
        return None

    # Strategy 1: Google OAuth2 ID Token verification (verifies JWT signature against Google public certs)
    try:
        req = _get_request_adapter()
        claims = google_id_token.verify_firebase_token(
            id_token,
            req,
            audience=FIREBASE_PROJECT_ID,
        )
        if claims and claims.get('user_id'):
            return {
                'uid': claims.get('user_id') or claims.get('sub', ''),
                'email': claims.get('email', ''),
                'name': claims.get('name', ''),
                'picture': claims.get('picture', ''),
                'claims': claims,
            }
    except Exception as e:
        logger.info('google_id_token verification skipped: %s', e)

    # Strategy 2: Google Identity Toolkit REST API
    try:
        url = f'https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={FIREBASE_API_KEY}'
        resp = requests.post(url, json={'idToken': id_token}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            users = data.get('users', [])
            if users:
                u = users[0]
                return {
                    'uid': u.get('localId', ''),
                    'email': u.get('email', ''),
                    'name': u.get('displayName', ''),
                    'picture': u.get('photoUrl', ''),
                    'claims': u,
                }
        else:
            logger.warning('Identity Toolkit lookup returned %s: %s', resp.status_code, resp.text)
    except Exception as e:
        logger.warning('Identity Toolkit lookup failed: %s', e)

    # Strategy 3: firebase_admin SDK fallback
    try:
        import firebase_admin
        from firebase_admin import auth
        if firebase_admin._apps:
            decoded = auth.verify_id_token(id_token)
            return {
                'uid': decoded.get('uid', ''),
                'email': decoded.get('email', ''),
                'name': decoded.get('name', ''),
                'picture': decoded.get('picture', ''),
                'claims': decoded,
            }
    except Exception as e:
        logger.warning('firebase_admin verify_id_token failed: %s', e)

    logger.error('All Firebase token verification strategies failed.')
    return None
