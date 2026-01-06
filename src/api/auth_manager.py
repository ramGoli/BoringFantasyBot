"""
OAuth authentication manager for Yahoo Fantasy Sports API.
Handles token management, refresh, and secure storage.
"""

import os
import json
import time
import base64
import webbrowser
from typing import Optional, Dict, Any
from pathlib import Path
from urllib.parse import urlencode, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import requests
from requests.auth import HTTPBasicAuth

from ..config.settings import get_config


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP server to handle OAuth callback."""
    
    def __init__(self, *args, auth_code_queue=None, **kwargs):
        self.auth_code_queue = auth_code_queue
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle OAuth callback."""
        query_components = parse_qs(self.path.split('?')[1])
        auth_code = query_components.get('code', [None])[0]
        
        if auth_code:
            self.auth_code_queue.put(auth_code)
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Authentication successful! You can close this window.")
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Authentication failed!")
    
    def log_message(self, format, *args):
        """Suppress logging."""
        pass


class YahooAuthManager:
    """Manages OAuth authentication with Yahoo Fantasy Sports API."""
    
    def __init__(self):
        self.config = get_config()
        self.token_file = Path("tokens.json")
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[float] = None
        
        # Yahoo OAuth endpoints
        self.auth_url = "https://api.login.yahoo.com/oauth2/request_auth"
        self.token_url = "https://api.login.yahoo.com/oauth2/get_token"
        
        # Load existing tokens if available
        self._load_tokens()
    
    def _load_tokens(self):
        """Load tokens from file if they exist."""
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                    self.access_token = token_data.get('access_token')
                    self.refresh_token = token_data.get('refresh_token')
                    self.token_expires_at = token_data.get('expires_at')
            except (json.JSONDecodeError, KeyError):
                # Invalid token file, will need to re-authenticate
                pass
    
    def _save_tokens(self):
        """Save tokens to file."""
        token_data = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires_at': self.token_expires_at
        }
        with open(self.token_file, 'w') as f:
            json.dump(token_data, f)
    
    def _is_token_valid(self) -> bool:
        """Check if current access token is valid."""
        if not self.access_token or not self.token_expires_at:
            return False
        return time.time() < self.token_expires_at - 60  # Buffer of 60 seconds
    
    def authenticate(self) -> bool:
        """Perform initial OAuth authentication."""
        if self._is_token_valid():
            return True
        
        if self.refresh_token:
            return self._refresh_token()
        
        return self._perform_initial_auth()
    
    def _perform_initial_auth(self) -> bool:
        """Perform initial OAuth flow."""
        import queue
        
        # Generate state parameter for security
        state = os.urandom(16).hex()
        
        # Build authorization URL using Postman's OAuth callback service
        auth_params = {
            'client_id': self.config.yahoo_api.client_id,
            'redirect_uri': 'https://oauth.pstmn.io/v1/callback',
            'response_type': 'code',
            'language': 'en-us'
        }
        
        auth_url = f"{self.auth_url}?{urlencode(auth_params)}"
        
        # Open browser for user authorization
        print(f"Opening browser for Yahoo OAuth authentication...")
        print(f"Authorization URL: {auth_url}")
        webbrowser.open(auth_url)
        
        try:
            # Manual code entry for public client
            print("\nAfter authorizing in your browser, Yahoo will show you a verification code.")
            print("Please copy that code and paste it here:")
            auth_code = input("Enter verification code: ").strip()
            
            if not auth_code:
                print("No verification code provided")
                return False
            
            # Exchange authorization code for tokens
            return self._exchange_code_for_tokens(auth_code)
            
        except queue.Empty:
            print("Authentication timeout. Please try again.")
            return False
    
    def _exchange_code_for_tokens(self, auth_code: str) -> bool:
        """Exchange authorization code for access and refresh tokens."""
        token_data = {
            'client_id': self.config.yahoo_api.client_id,
            'client_secret': self.config.yahoo_api.client_secret,
            'redirect_uri': 'https://oauth.pstmn.io/v1/callback',
            'code': auth_code,
            'grant_type': 'authorization_code'
        }
        
        # Create Basic Auth header as shown in Stack Overflow example
        auth_header = base64.b64encode(
            f"{self.config.yahoo_api.client_id}:{self.config.yahoo_api.client_secret}".encode('utf-8')
        ).decode('utf-8')
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36'
        }
        
        try:
            response = requests.post(self.token_url, data=token_data, headers=headers)
            response.raise_for_status()
            
            token_response = response.json()
            
            self.access_token = token_response['access_token']
            self.refresh_token = token_response['refresh_token']
            self.token_expires_at = time.time() + token_response['expires_in']
            
            self._save_tokens()
            return True
            
        except requests.RequestException as e:
            print(f"Error exchanging code for tokens: {e}")
            return False
    
    def _refresh_token(self) -> bool:
        """Refresh the access token using refresh token."""
        if not self.refresh_token:
            return False
        
        token_data = {
            'redirect_uri': 'https://oauth.pstmn.io/v1/callback',
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }
        
        # Create Basic Auth header as shown in Stack Overflow example
        auth_header = base64.b64encode(
            f"{self.config.yahoo_api.client_id}:{self.config.yahoo_api.client_secret}".encode('utf-8')
        ).decode('utf-8')
        
        headers = {
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36'
        }
        
        try:
            response = requests.post(self.token_url, data=token_data, headers=headers)
            response.raise_for_status()
            
            token_response = response.json()
            
            self.access_token = token_response['access_token']
            if 'refresh_token' in token_response:
                self.refresh_token = token_response['refresh_token']
            self.token_expires_at = time.time() + token_response['expires_in']
            
            self._save_tokens()
            return True
            
        except requests.RequestException as e:
            print(f"Error refreshing token: {e}")
            # Clear invalid tokens
            self.access_token = None
            self.refresh_token = None
            self.token_expires_at = None
            if self.token_file.exists():
                self.token_file.unlink()
            return False
    
    def get_authenticated_session(self) -> Optional[requests.Session]:
        """Get an authenticated requests session."""
        if not self.authenticate():
            return None
        
        session = requests.Session()
        session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'User-Agent': 'FantasyFootballBot/1.0'
        })
        
        return session
    
    def get_access_token(self) -> Optional[str]:
        """Get current access token, refreshing if necessary."""
        if not self.authenticate():
            return None
        return self.access_token
    
    def logout(self):
        """Clear stored tokens."""
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        if self.token_file.exists():
            self.token_file.unlink()
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self._is_token_valid()


# Global auth manager instance
auth_manager = YahooAuthManager()
