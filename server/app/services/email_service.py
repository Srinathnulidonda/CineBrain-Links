# server/app/services/email_service.py

"""
Email service using Brevo SMTP and API with enhanced deliverability.
Adapted from CineBrain's production email service.
"""

import smtplib
import socket
import logging
import threading
import time
import uuid
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlparse

import requests
import redis
from flask import current_app, render_template_string

logger = logging.getLogger(__name__)


# ============================================
# EMAIL TEMPLATES FOR CINBRAINLINKS
# ============================================

TEMPLATES = {
    "welcome": {
        "subject": "Welcome to CinBrainLinks! 🔗",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }
        .wrapper { max-width: 600px; margin: 0 auto; padding: 20px; }
        .container { background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; }
        .header h1 { margin: 0; font-size: 28px; font-weight: 600; }
        .header p { margin: 10px 0 0; opacity: 0.9; font-size: 16px; }
        .content { padding: 40px 30px; }
        .content h2 { color: #333; margin-top: 0; }
        .feature-list { list-style: none; padding: 0; margin: 25px 0; }
        .feature-list li { padding: 12px 0; padding-left: 35px; position: relative; border-bottom: 1px solid #eee; }
        .feature-list li:last-child { border-bottom: none; }
        .feature-list li::before { content: "✓"; position: absolute; left: 0; color: #667eea; font-weight: bold; font-size: 18px; }
        .button { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important; padding: 14px 35px; text-decoration: none; border-radius: 8px; margin: 25px 0; font-weight: 600; font-size: 16px; }
        .button:hover { opacity: 0.9; }
        .footer { text-align: center; padding: 25px; color: #888; font-size: 12px; background: #f9f9f9; }
        .footer a { color: #667eea; text-decoration: none; }
        .social-links { margin: 15px 0; }
        .social-links a { margin: 0 10px; color: #667eea; text-decoration: none; }
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="container">
            <div class="header">
                <h1>🔗 CinBrainLinks</h1>
                <p>Your Branded URL Shortener</p>
            </div>
            <div class="content">
                <h2>Welcome aboard, {{ user_name }}! 🎉</h2>
                <p>Thank you for joining <strong>CinBrainLinks</strong>! We're excited to have you on board.</p>
                <p>With CinBrainLinks, you can:</p>
                <ul class="feature-list">
                    <li><strong>Create short, branded links</strong> - Make your URLs memorable</li>
                    <li><strong>Track click analytics</strong> - See who's clicking your links</li>
                    <li><strong>Custom slugs</strong> - Use your own custom short URLs</li>
                    <li><strong>Set expiration dates</strong> - Control how long links stay active</li>
                    <li><strong>Manage everything</strong> - Enable, disable, or delete links anytime</li>
                </ul>
                <p style="text-align: center;">
                    <a href="{{ dashboard_url }}" class="button">Go to Dashboard →</a>
                </p>
                <p>If you have any questions, feel free to reach out to our support team.</p>
                <p>Happy linking! 🚀</p>
                <p><strong>The CinBrainLinks Team</strong></p>
            </div>
            <div class="footer">
                <p>© {{ year }} CinBrainLinks. All rights reserved.</p>
                <p>You received this email because you signed up for CinBrainLinks.</p>
            </div>
        </div>
    </div>
</body>
</html>
        """,
        "text": """
Welcome to CinBrainLinks! 🔗

Hi {{ user_name }},

Thank you for joining CinBrainLinks! We're excited to have you on board.

With CinBrainLinks, you can:
✓ Create short, branded links - Make your URLs memorable
✓ Track click analytics - See who's clicking your links
✓ Custom slugs - Use your own custom short URLs
✓ Set expiration dates - Control how long links stay active
✓ Manage everything - Enable, disable, or delete links anytime

Ready to get started? Visit your dashboard: {{ dashboard_url }}

If you have any questions, feel free to reach out to our support team.

Happy linking! 🚀

The CinBrainLinks Team

---
© {{ year }} CinBrainLinks. All rights reserved.
        """
    },
    
    "password_reset": {
        "subject": "Reset Your CinBrainLinks Password 🔐",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }
        .wrapper { max-width: 600px; margin: 0 auto; padding: 20px; }
        .container { background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 40px 30px; text-align: center; }
        .header h1 { margin: 0; font-size: 28px; font-weight: 600; }
        .content { padding: 40px 30px; }
        .button { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important; padding: 14px 35px; text-decoration: none; border-radius: 8px; margin: 25px 0; font-weight: 600; font-size: 16px; }
        .warning { background: #fff3cd; border: 1px solid #ffc107; padding: 15px 20px; border-radius: 8px; margin: 20px 0; }
        .warning strong { color: #856404; }
        .security-note { background: #e8f4fd; border-left: 4px solid #667eea; padding: 15px 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }
        .footer { text-align: center; padding: 25px; color: #888; font-size: 12px; background: #f9f9f9; }
        .code-box { background: #f8f9fa; border: 2px dashed #ddd; padding: 15px; text-align: center; font-family: monospace; font-size: 14px; margin: 15px 0; border-radius: 8px; word-break: break-all; }
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="container">
            <div class="header">
                <h1>🔐 Password Reset</h1>
            </div>
            <div class="content">
                <p>Hi {{ user_name }},</p>
                <p>We received a request to reset your CinBrainLinks password. Click the button below to set a new password:</p>
                <p style="text-align: center;">
                    <a href="{{ reset_url }}" class="button">Reset Password →</a>
                </p>
                <div class="warning">
                    <strong>⏰ Important:</strong> This link will expire in <strong>1 hour</strong> for security reasons.
                </div>
                <p>If the button doesn't work, copy and paste this link into your browser:</p>
                <div class="code-box">{{ reset_url }}</div>
                <div class="security-note">
                    <strong>🔒 Security Notice:</strong>
                    <ul style="margin: 10px 0 0; padding-left: 20px;">
                        <li>If you didn't request this password reset, you can safely ignore this email</li>
                        <li>Your password will remain unchanged</li>
                        <li>This link can only be used once</li>
                    </ul>
                </div>
                <p>Request details:</p>
                <ul>
                    <li><strong>Time:</strong> {{ request_time }}</li>
                    <li><strong>IP Address:</strong> {{ ip_address }}</li>
                    <li><strong>Device:</strong> {{ device_info }}</li>
                </ul>
                <p><strong>The CinBrainLinks Team</strong></p>
            </div>
            <div class="footer">
                <p>© {{ year }} CinBrainLinks. All rights reserved.</p>
                <p>This is an automated security email from CinBrainLinks.</p>
            </div>
        </div>
    </div>
</body>
</html>
        """,
        "text": """
Password Reset Request 🔐

Hi {{ user_name }},

We received a request to reset your CinBrainLinks password.

Click the link below to set a new password:
{{ reset_url }}

⏰ IMPORTANT: This link will expire in 1 hour for security reasons.

🔒 SECURITY NOTICE:
- If you didn't request this password reset, you can safely ignore this email
- Your password will remain unchanged
- This link can only be used once

Request details:
- Time: {{ request_time }}
- IP Address: {{ ip_address }}
- Device: {{ device_info }}

The CinBrainLinks Team

---
© {{ year }} CinBrainLinks. All rights reserved.
        """
    },
    
    "link_expiration_alert": {
        "subject": "⏰ Your CinBrainLinks Link is Expiring Soon",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }
        .wrapper { max-width: 600px; margin: 0 auto; padding: 20px; }
        .container { background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
        .header { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 40px 30px; text-align: center; }
        .header h1 { margin: 0; font-size: 28px; font-weight: 600; }
        .content { padding: 40px 30px; }
        .link-box { background: #f8f9fa; border: 1px solid #e9ecef; padding: 20px; border-radius: 10px; margin: 20px 0; }
        .link-box .label { color: #6c757d; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
        .link-box .value { font-size: 16px; font-weight: 600; color: #333; word-break: break-all; }
        .stats { display: flex; justify-content: space-around; margin: 20px 0; text-align: center; }
        .stat-item { padding: 15px; }
        .stat-value { font-size: 24px; font-weight: bold; color: #667eea; }
        .stat-label { font-size: 12px; color: #6c757d; text-transform: uppercase; }
        .button { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important; padding: 14px 35px; text-decoration: none; border-radius: 8px; margin: 20px 0; font-weight: 600; }
        .warning { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }
        .footer { text-align: center; padding: 25px; color: #888; font-size: 12px; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="container">
            <div class="header">
                <h1>⏰ Link Expiring Soon</h1>
            </div>
            <div class="content">
                <p>Hi {{ user_name }},</p>
                <p>One of your CinBrainLinks is about to expire:</p>
                
                <div class="link-box">
                    <div style="margin-bottom: 15px;">
                        <div class="label">Short URL</div>
                        <div class="value">{{ short_url }}</div>
                    </div>
                    <div style="margin-bottom: 15px;">
                        <div class="label">Original URL</div>
                        <div class="value">{{ original_url }}</div>
                    </div>
                    <div>
                        <div class="label">Expires</div>
                        <div class="value" style="color: #dc3545;">{{ expires_at }}</div>
                    </div>
                </div>
                
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-value">{{ click_count }}</div>
                        <div class="stat-label">Total Clicks</div>
                    </div>
                </div>
                
                <div class="warning">
                    <strong>⚠️ Action Required:</strong> If you want to keep this link active, please extend its expiration date from your dashboard before it expires.
                </div>
                
                <p style="text-align: center;">
                    <a href="{{ dashboard_url }}" class="button">Manage Link →</a>
                </p>
                
                <p><strong>The CinBrainLinks Team</strong></p>
            </div>
            <div class="footer">
                <p>© {{ year }} CinBrainLinks. All rights reserved.</p>
                <p>You're receiving this because you have expiring links in your account.</p>
            </div>
        </div>
    </div>
</body>
</html>
        """,
        "text": """
⏰ Link Expiring Soon

Hi {{ user_name }},

One of your CinBrainLinks is about to expire:

SHORT URL: {{ short_url }}
ORIGINAL URL: {{ original_url }}
EXPIRES: {{ expires_at }}
TOTAL CLICKS: {{ click_count }}

⚠️ ACTION REQUIRED:
If you want to keep this link active, please extend its expiration date from your dashboard before it expires.

Manage your link: {{ dashboard_url }}

The CinBrainLinks Team

---
© {{ year }} CinBrainLinks. All rights reserved.
        """
    },
    
    "link_expired": {
        "subject": "Your CinBrainLinks Link Has Expired",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }
        .wrapper { max-width: 600px; margin: 0 auto; padding: 20px; }
        .container { background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); }
        .header { background: linear-gradient(135deg, #6c757d 0%, #495057 100%); color: white; padding: 40px 30px; text-align: center; }
        .header h1 { margin: 0; font-size: 28px; font-weight: 600; }
        .content { padding: 40px 30px; }
        .link-box { background: #f8f9fa; border: 1px solid #e9ecef; padding: 20px; border-radius: 10px; margin: 20px 0; opacity: 0.8; }
        .link-box .label { color: #6c757d; font-size: 12px; text-transform: uppercase; }
        .link-box .value { font-size: 16px; color: #6c757d; text-decoration: line-through; }
        .button { display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white !important; padding: 14px 35px; text-decoration: none; border-radius: 8px; margin: 20px 0; font-weight: 600; }
        .footer { text-align: center; padding: 25px; color: #888; font-size: 12px; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="wrapper">
        <div class="container">
            <div class="header">
                <h1>Link Expired</h1>
            </div>
            <div class="content">
                <p>Hi {{ user_name }},</p>
                <p>Your CinBrainLinks link has expired and is no longer active:</p>
                
                <div class="link-box">
                    <div style="margin-bottom: 10px;">
                        <div class="label">Short URL (Expired)</div>
                        <div class="value">{{ short_url }}</div>
                    </div>
                    <div>
                        <div class="label">Expired On</div>
                        <div class="value" style="text-decoration: none;">{{ expires_at }}</div>
                    </div>
                </div>
                
                <p>Don't worry! You can create a new link with the same destination or reactivate this one by updating the expiration date.</p>
                
                <p style="text-align: center;">
                    <a href="{{ dashboard_url }}" class="button">Go to Dashboard →</a>
                </p>
                
                <p><strong>The CinBrainLinks Team</strong></p>
            </div>
            <div class="footer">
                <p>© {{ year }} CinBrainLinks. All rights reserved.</p>
            </div>
        </div>
    </div>
</body>
</html>
        """,
        "text": """
Link Expired

Hi {{ user_name }},

Your CinBrainLinks link has expired and is no longer active:

SHORT URL (Expired): {{ short_url }}
EXPIRED ON: {{ expires_at }}

Don't worry! You can create a new link with the same destination or reactivate this one by updating the expiration date.

Go to Dashboard: {{ dashboard_url }}

The CinBrainLinks Team

---
© {{ year }} CinBrainLinks. All rights reserved.
        """
    }
}


class BrevoEmailService:
    """
    Email service using Brevo SMTP and API with enhanced deliverability.
    Supports both SMTP and API methods with automatic fallback.
    """

    _instance = None
    _redis_client = None

    def __new__(cls):
        """Singleton pattern to ensure single email service instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize email service with configuration from Flask app."""
        if self._initialized:
            return
            
        self._initialized = True
        
        # Configuration from Flask app
        self.smtp_server = current_app.config.get("BREVO_SMTP_SERVER", "smtp-relay.brevo.com")
        self.smtp_port = current_app.config.get("BREVO_SMTP_PORT", 587)
        self.smtp_username = current_app.config.get("BREVO_SMTP_USERNAME")
        self.smtp_password = current_app.config.get("BREVO_SMTP_PASSWORD")
        self.api_key = current_app.config.get("BREVO_API_KEY")
        
        self.sender_email = current_app.config.get("BREVO_SENDER_EMAIL", "noreply@cinbrainlinks.com")
        self.sender_name = current_app.config.get("BREVO_SENDER_NAME", "CinBrainLinks")
        self.reply_to_email = current_app.config.get("REPLY_TO_EMAIL", self.sender_email)
        
        self.frontend_url = current_app.config.get("FRONTEND_URL", "http://cinebrainlinks.vercel.app")
        self.base_url = current_app.config.get("BASE_URL", "http://localhost:5000")
        self.environment = current_app.config.get("FLASK_ENV", "development")
        
        # API Configuration
        self.api_base_url = "https://api.brevo.com/v3"
        
        # Service status
        self.email_enabled = False
        self.smtp_enabled = False
        self.api_enabled = False
        self.is_configured = False
        
        # Initialize Redis connection
        self._init_redis()
        
        # Initialize email service based on environment
        self._initialize_email_service()
        
        if self.email_enabled:
            self._start_email_worker()
            logger.info("✅ Brevo email worker initialized successfully")
            self._log_sender_info()
        else:
            logger.warning("⚠️ Email service disabled - no valid configuration found")

    def _init_redis(self):
        """Initialize Redis connection for email queue."""
        try:
            redis_url = current_app.config.get("REDIS_URL")
            if not redis_url:
                logger.warning("Redis URL not configured for email service")
                return
            
            url = urlparse(redis_url)
            BrevoEmailService._redis_client = redis.StrictRedis(
                host=url.hostname,
                port=url.port or 6379,
                password=url.password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                ssl=url.scheme == 'rediss'
            )
            BrevoEmailService._redis_client.ping()
            logger.info("✅ Email service Redis connected")
            
        except Exception as e:
            logger.error(f"❌ Email service Redis connection failed: {e}")
            BrevoEmailService._redis_client = None

    @property
    def redis_client(self):
        return BrevoEmailService._redis_client

    def _log_sender_info(self):
        """Log sender configuration for debugging."""
        logger.info(f"📧 Email Configuration:")
        logger.info(f"   Sender: {self.sender_name} <{self.sender_email}>")
        logger.info(f"   Reply-To: {self.reply_to_email}")
        logger.info(f"   Environment: {self.environment}")
        logger.info(f"   Method: {'SMTP' if self.smtp_enabled else 'API' if self.api_enabled else 'None'}")

    def _initialize_email_service(self):
        """Initialize email service - API first in production, SMTP first in development."""
        
        # In production, prefer API over SMTP (many hosts block SMTP ports)
        if self.environment == 'production':
            # Try API first in production
            if self.api_key and self.sender_email:
                self.api_enabled = self._test_api_connection()
                if self.api_enabled:
                    logger.info("✅ Using Brevo API for email delivery (Production)")
                    self.email_enabled = True
                    self.is_configured = True
                    return
            
            # Try SMTP as fallback
            if self.smtp_username and self.smtp_password:
                self.smtp_enabled = self._test_smtp_connection_safe()
                if self.smtp_enabled:
                    logger.info("✅ Using Brevo SMTP for email delivery (Production)")
                    self.email_enabled = True
                    self.is_configured = True
                    return
        else:
            # Development - try API first since SMTP might be blocked
            if self.api_key and self.sender_email:
                self.api_enabled = self._test_api_connection()
                if self.api_enabled:
                    logger.info("✅ Using Brevo API for email delivery (Development)")
                    self.email_enabled = True
                    self.is_configured = True
                    return
            
            # Try SMTP as fallback
            if self.smtp_username and self.smtp_password:
                self.smtp_enabled = self._test_smtp_connection_safe()
                if self.smtp_enabled:
                    logger.info("✅ Using Brevo SMTP for email delivery (Development)")
                    self.email_enabled = True
                    self.is_configured = True
                    return
        
        # No valid configuration
        if not self.smtp_username and not self.api_key:
            logger.warning("⚠️ Neither SMTP nor API credentials configured")
        elif self.environment == 'production' and not self.api_key:
            logger.warning("⚠️ In production environment - Brevo API key recommended")

    def _test_smtp_connection_safe(self) -> bool:
        """Test SMTP connectivity with timeout protection."""
        try:
            logger.info(f"Testing SMTP connection to {self.smtp_server}:{self.smtp_port}")
            
            timeout = 5 if self.environment == 'production' else 10
            
            # Test if port is reachable
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.smtp_server, self.smtp_port))
            sock.close()
            
            if result != 0:
                logger.warning(f"⚠️ SMTP port {self.smtp_port} appears to be blocked")
                return False
            
            # Test actual SMTP connection
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=timeout)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.quit()
            
            logger.info("✅ Brevo SMTP connection successful")
            return True
            
        except socket.timeout:
            logger.warning(f"⚠️ SMTP connection timed out - port might be blocked")
            return False
        except socket.error as e:
            logger.warning(f"⚠️ SMTP socket error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Brevo SMTP connection failed: {e}")
            return False

    def _test_api_connection(self) -> bool:
        """Test Brevo API connectivity."""
        if not self.api_key:
            logger.warning("⚠️ No Brevo API key configured")
            return False
            
        try:
            headers = {
                'api-key': self.api_key,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                f"{self.api_base_url}/account",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✅ Brevo API connected successfully")
                return True
            else:
                logger.warning(f"⚠️ Brevo API test failed: {response.status_code}")
                if response.status_code == 401:
                    logger.error("❌ Invalid API key")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("❌ Brevo API connection timeout")
            return False
        except Exception as e:
            logger.error(f"❌ Brevo API connection test failed: {e}")
            return False

    def _start_email_worker(self):
        """Background worker to process queued emails."""
        def worker():
            # Need to create app context for the worker thread
            from flask import current_app
            app = current_app._get_current_object()
            
            while True:
                try:
                    with app.app_context():
                        if self.redis_client and self.email_enabled:
                            email_json = self.redis_client.lpop('cinbrainlinks:email_queue')
                            if email_json:
                                email_data = json.loads(email_json)
                                self._send_email(email_data)
                            else:
                                time.sleep(1)
                        else:
                            time.sleep(5)
                except Exception as e:
                    logger.error(f"Email worker error: {e}")
                    time.sleep(5)

        thread = threading.Thread(target=worker, daemon=True, name="BrevoEmailWorker")
        thread.start()

    def _send_email(self, email_data: Dict, retry_count: int = 0):
        """Send email using available method."""
        if not self.email_enabled:
            self._store_fallback_email(email_data)
            return False
        
        # Use whichever method is enabled
        if self.api_enabled:
            success = self._send_email_api(email_data, retry_count)
            if success:
                return True
        
        if self.smtp_enabled:
            success = self._send_email_smtp(email_data, retry_count)
            if success:
                return True
        
        # Store as fallback if both fail
        self._store_fallback_email(email_data)
        return False

    def _send_email_smtp(self, email_data: Dict, retry_count: int = 0) -> bool:
        """Send email using SMTP with enhanced headers."""
        try:
            timeout = 10 if self.environment == 'production' else 30
            
            message = MIMEMultipart("alternative")
            message["Subject"] = email_data['subject']
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = email_data['to']
            message["Reply-To"] = self.reply_to_email
            
            # Enhanced headers for deliverability
            message["X-Mailer"] = "CinBrainLinks/1.0"
            message["X-Priority"] = "3"
            message["Importance"] = "Normal"
            message["Message-ID"] = f"<{uuid.uuid4()}@cinbrainlinks.com>"
            message["Date"] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
            
            # List-Unsubscribe headers
            message["List-Unsubscribe"] = f"<{self.frontend_url}/unsubscribe>"
            message["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
            
            if email_data.get('text'):
                message.attach(MIMEText(email_data['text'], "plain", "utf-8"))
            
            if email_data.get('html'):
                message.attach(MIMEText(email_data['html'], "html", "utf-8"))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=timeout)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(message)
            server.quit()
            
            logger.info(f"✅ Email sent via SMTP to {email_data['to']}")
            self._store_sent_status(email_data, 'smtp')
            return True
            
        except (socket.timeout, socket.error) as e:
            logger.warning(f"⚠️ SMTP network error: {e}")
            if self.environment != 'production' and retry_count < 1:
                time.sleep(2)
                return self._send_email_smtp(email_data, retry_count + 1)
            return False
            
        except Exception as e:
            logger.error(f"❌ SMTP send failed to {email_data['to']}: {e}")
            max_retries = 1 if self.environment == 'production' else 2
            if retry_count < max_retries:
                time.sleep(2 ** retry_count)
                return self._send_email_smtp(email_data, retry_count + 1)
            return False

    def _send_email_api(self, email_data: Dict, retry_count: int = 0) -> bool:
        """Send email using Brevo API."""
        if not self.api_key:
            return False
            
        headers = {
            'api-key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        payload = {
            'sender': {
                'email': self.sender_email,
                'name': self.sender_name
            },
            'to': [{
                'email': email_data['to'],
                'name': email_data.get('to_name', email_data['to'].split('@')[0])
            }],
            'subject': email_data['subject'],
            'htmlContent': email_data.get('html', '<p>No HTML content</p>'),
            'textContent': email_data.get('text', 'No text content'),
            'headers': {
                'X-Mailer': 'CinBrainLinks/1.0',
                'X-Priority': '3',
                'List-Unsubscribe': f'<{self.frontend_url}/unsubscribe>'
            },
            'tags': ['transactional', 'cinbrainlinks']
        }
        
        if self.reply_to_email:
            payload['replyTo'] = {
                'email': self.reply_to_email,
                'name': self.sender_name
            }

        try:
            response = requests.post(
                f"{self.api_base_url}/smtp/email",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 201:
                res = response.json()
                message_id = res.get('messageId', 'sent')
                logger.info(f"✅ Email sent via API to {email_data['to']} (ID: {message_id})")
                self._store_sent_status(email_data, 'api', message_id)
                return True
            else:
                logger.warning(f"⚠️ API returned {response.status_code}: {response.text}")
                if retry_count < 2:
                    time.sleep(2 ** retry_count)
                    return self._send_email_api(email_data, retry_count + 1)
                return False
                    
        except Exception as e:
            logger.error(f"❌ API request failed: {e}")
            if retry_count < 2:
                time.sleep(2 ** retry_count)
                return self._send_email_api(email_data, retry_count + 1)
            return False

    def _store_sent_status(self, email_data: Dict, method: str, message_id: str = None):
        """Store sent email status in Redis."""
        if not self.redis_client:
            return
            
        try:
            self.redis_client.setex(
                f"cinbrainlinks:email_sent:{email_data['id']}",
                86400,
                json.dumps({
                    'status': 'sent',
                    'timestamp': datetime.utcnow().isoformat(),
                    'to': email_data['to'],
                    'subject': email_data['subject'],
                    'method': method,
                    'message_id': message_id
                })
            )
        except Exception as e:
            logger.warning(f"Failed to store sent status: {e}")

    def _store_fallback_email(self, email_data: Dict):
        """Store unsent email in fallback queue."""
        if not self.redis_client:
            logger.warning(f"📧 Fallback email for {email_data['to']}")
            if email_data.get('reset_token'):
                reset_url = f"{self.frontend_url}/reset-password?token={email_data['reset_token']}"
                logger.info(f"🔗 Password reset link: {reset_url}")
            return
            
        email_data['failed_at'] = datetime.utcnow().isoformat()
        email_data['environment'] = self.environment
        
        key = f"cinbrainlinks:email_fallback:{uuid.uuid4()}"
        self.redis_client.setex(key, 604800, json.dumps(email_data))  # 7 days
        self.redis_client.rpush('cinbrainlinks:email_fallback_queue', key)
        logger.info(f"📥 Stored unsent email for {email_data['to']} in fallback queue")

    def _render_template(self, template_name: str, context: dict) -> tuple:
        """Render email template with context."""
        template = TEMPLATES.get(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")
        
        # Add common context
        context.setdefault("year", datetime.now().year)
        context.setdefault("dashboard_url", f"{self.frontend_url}/dashboard")
        context.setdefault("frontend_url", self.frontend_url)
        
        subject = template["subject"]
        html_content = render_template_string(template["html"], **context)
        text_content = render_template_string(template["text"], **context)
        
        return subject, html_content, text_content

    def queue_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: str = "",
        priority: str = 'normal',
        reset_token: str = None,
        to_name: str = ""
    ) -> bool:
        """Queue email to be sent asynchronously."""
        email_id = str(uuid.uuid4())
        
        if not to_name:
            to_name = to.split('@')[0].replace('.', ' ').title()
        
        email_data = {
            'id': email_id,
            'to': to,
            'to_name': to_name,
            'subject': subject,
            'html': html,
            'text': text,
            'timestamp': datetime.utcnow().isoformat(),
            'reset_token': reset_token,
            'environment': self.environment
        }

        if not self.email_enabled:
            logger.warning(f"Email service disabled - providing fallback for {to}")
            self._store_fallback_email(email_data)
            
            if reset_token:
                reset_url = f"{self.frontend_url}/reset-password?token={reset_token}"
                logger.info(f"🔗 Password reset link for {to}: {reset_url}")
            
            return True

        if self.redis_client:
            queue_key = 'cinbrainlinks:email_queue'
            if priority == 'high':
                self.redis_client.lpush(queue_key, json.dumps(email_data))
            else:
                self.redis_client.rpush(queue_key, json.dumps(email_data))
            logger.info(f"📧 Queued email for {to} (ID: {email_id})")
        else:
            # If no Redis, send directly in background thread
            threading.Thread(
                target=self._send_email,
                args=(email_data,),
                daemon=True
            ).start()
        
        return True

    # ============================================
    # PUBLIC API METHODS FOR CINBRAINLINKS
    # ============================================

    def send_welcome_email(
        self,
        to_email: str,
        user_name: str = None,
        async_send: bool = True
    ) -> bool:
        """Send welcome email to new user."""
        try:
            if not user_name:
                user_name = to_email.split('@')[0].replace('.', ' ').title()
            
            context = {"user_name": user_name}
            subject, html_content, text_content = self._render_template("welcome", context)
            
            if async_send:
                return self.queue_email(
                    to=to_email,
                    subject=subject,
                    html=html_content,
                    text=text_content,
                    to_name=user_name
                )
            else:
                email_data = {
                    'id': str(uuid.uuid4()),
                    'to': to_email,
                    'to_name': user_name,
                    'subject': subject,
                    'html': html_content,
                    'text': text_content,
                    'timestamp': datetime.utcnow().isoformat()
                }
                return self._send_email(email_data)
                
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")
            return False

    def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        user_name: str = None,
        request_info: dict = None,
        async_send: bool = True
    ) -> bool:
        """Send password reset email."""
        try:
            if not user_name:
                user_name = to_email.split('@')[0].replace('.', ' ').title()
            
            reset_url = f"{self.frontend_url}/reset-password?token={reset_token}"
            
            context = {
                "user_name": user_name,
                "reset_url": reset_url,
                "request_time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                "ip_address": request_info.get('ip', 'Unknown') if request_info else 'Unknown',
                "device_info": request_info.get('device', 'Unknown') if request_info else 'Unknown'
            }
            
            subject, html_content, text_content = self._render_template("password_reset", context)
            
            if async_send:
                return self.queue_email(
                    to=to_email,
                    subject=subject,
                    html=html_content,
                    text=text_content,
                    priority='high',
                    reset_token=reset_token,
                    to_name=user_name
                )
            else:
                email_data = {
                    'id': str(uuid.uuid4()),
                    'to': to_email,
                    'to_name': user_name,
                    'subject': subject,
                    'html': html_content,
                    'text': text_content,
                    'reset_token': reset_token,
                    'timestamp': datetime.utcnow().isoformat()
                }
                return self._send_email(email_data)
                
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            return False

    def send_link_expiration_alert(
        self,
        to_email: str,
        short_url: str,
        original_url: str,
        expires_at: str,
        click_count: int = 0,
        user_name: str = None,
        async_send: bool = True
    ) -> bool:
        """Send link expiration alert email."""
        try:
            if not user_name:
                user_name = to_email.split('@')[0].replace('.', ' ').title()
            
            context = {
                "user_name": user_name,
                "short_url": short_url,
                "original_url": original_url[:100] + '...' if len(original_url) > 100 else original_url,
                "expires_at": expires_at,
                "click_count": click_count
            }
            
            subject, html_content, text_content = self._render_template(
                "link_expiration_alert", context
            )
            
            if async_send:
                return self.queue_email(
                    to=to_email,
                    subject=subject,
                    html=html_content,
                    text=text_content,
                    to_name=user_name
                )
            else:
                email_data = {
                    'id': str(uuid.uuid4()),
                    'to': to_email,
                    'to_name': user_name,
                    'subject': subject,
                    'html': html_content,
                    'text': text_content,
                    'timestamp': datetime.utcnow().isoformat()
                }
                return self._send_email(email_data)
                
        except Exception as e:
            logger.error(f"Failed to send link expiration alert: {e}")
            return False

    def send_link_expired_notification(
        self,
        to_email: str,
        short_url: str,
        expires_at: str,
        user_name: str = None,
        async_send: bool = True
    ) -> bool:
        """Send notification when link has expired."""
        try:
            if not user_name:
                user_name = to_email.split('@')[0].replace('.', ' ').title()
            
            context = {
                "user_name": user_name,
                "short_url": short_url,
                "expires_at": expires_at
            }
            
            subject, html_content, text_content = self._render_template(
                "link_expired", context
            )
            
            if async_send:
                return self.queue_email(
                    to=to_email,
                    subject=subject,
                    html=html_content,
                    text=text_content,
                    to_name=user_name
                )
            else:
                email_data = {
                    'id': str(uuid.uuid4()),
                    'to': to_email,
                    'to_name': user_name,
                    'subject': subject,
                    'html': html_content,
                    'text': text_content,
                    'timestamp': datetime.utcnow().isoformat()
                }
                return self._send_email(email_data)
                
        except Exception as e:
            logger.error(f"Failed to send link expired notification: {e}")
            return False

    def get_email_status(self, email_id: str) -> Dict:
        """Get email delivery status."""
        if not self.redis_client:
            return {'status': 'unknown', 'id': email_id}
        
        try:
            # Check sent emails
            sent_data = self.redis_client.get(f"cinbrainlinks:email_sent:{email_id}")
            if sent_data:
                return json.loads(sent_data)
            
            # Check fallback queue
            fallback_data = self.redis_client.get(f"cinbrainlinks:email_fallback:{email_id}")
            if fallback_data:
                data = json.loads(fallback_data)
                data['status'] = 'fallback'
                return data
            
            return {'status': 'not_found', 'id': email_id}
            
        except Exception as e:
            logger.error(f"Error getting email status: {e}")
            return {'status': 'error', 'id': email_id}

    def get_queue_stats(self) -> Dict:
        """Get email queue statistics."""
        stats = {
            'queue_size': 0,
            'fallback_queue_size': 0,
            'smtp_enabled': self.smtp_enabled,
            'api_enabled': self.api_enabled,
            'email_enabled': self.email_enabled,
            'environment': self.environment,
            'sender': self.sender_email,
            'sender_name': self.sender_name
        }
        
        if not self.redis_client:
            return stats
            
        try:
            stats['queue_size'] = self.redis_client.llen('cinbrainlinks:email_queue')
            stats['fallback_queue_size'] = self.redis_client.llen('cinbrainlinks:email_fallback_queue')
            
            # Count sent emails in last 24h
            keys = self.redis_client.keys('cinbrainlinks:email_sent:*')
            stats['sent_count_24h'] = len(keys)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            stats['error'] = str(e)
            return stats


# Singleton accessor
_email_service_instance = None


def get_email_service() -> BrevoEmailService:
    """Get or create email service singleton instance."""
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = BrevoEmailService()
    return _email_service_instance


# Convenience class for backwards compatibility
class EmailService:
    """Wrapper class for backwards compatibility."""
    
    def __new__(cls):
        return get_email_service()