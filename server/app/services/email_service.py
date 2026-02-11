# server/app/services/email_service.py

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

TEMPLATES = {
    "welcome": {
        "subject": "Welcome to Savlink",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5; }
        .container { max-width: 560px; margin: 40px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .header { background: #1a1a2e; color: #fff; padding: 32px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; font-weight: 600; letter-spacing: -0.5px; }
        .content { padding: 32px; }
        .content h2 { margin: 0 0 16px; font-size: 20px; color: #1a1a2e; }
        .content p { margin: 0 0 16px; color: #555; }
        .features { margin: 24px 0; padding: 0; }
        .features li { padding: 8px 0; padding-left: 24px; position: relative; list-style: none; color: #555; }
        .features li::before { content: "✓"; position: absolute; left: 0; color: #10b981; font-weight: bold; }
        .button { display: inline-block; background: #1a1a2e; color: #fff !important; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 500; }
        .footer { text-align: center; padding: 24px; color: #888; font-size: 13px; border-top: 1px solid #eee; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Savlink</h1>
        </div>
        <div class="content">
            <h2>Welcome, {{ user_name }}</h2>
            <p>Your account is ready. Here's what you can do with Savlink:</p>
            <ul class="features">
                <li>Create short, memorable links</li>
                <li>Track clicks and engagement</li>
                <li>Organize your link collection</li>
                <li>Access links from anywhere</li>
            </ul>
            <p style="text-align: center; margin-top: 32px;">
                <a href="{{ dashboard_url }}" class="button">Go to Dashboard</a>
            </p>
        </div>
        <div class="footer">
            <p>© {{ year }} Savlink</p>
        </div>
    </div>
</body>
</html>
        """,
        "text": """Welcome to Savlink

Hi {{ user_name }},

Your account is ready. You can now:
- Create short, memorable links
- Track clicks and engagement
- Organize your link collection
- Access links from anywhere

Get started: {{ dashboard_url }}

- Savlink
        """
    },
    
    "email_verification": {
        "subject": "Verify your Savlink email address",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5; }
        .container { max-width: 560px; margin: 40px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .header { background: #1a1a2e; color: #fff; padding: 32px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; font-weight: 600; }
        .content { padding: 32px; }
        .content h2 { margin: 0 0 16px; font-size: 20px; color: #1a1a2e; }
        .content p { margin: 0 0 16px; color: #555; }
        .button { display: inline-block; background: #1a1a2e; color: #fff !important; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-weight: 500; font-size: 16px; }
        .notice { background: #e7f3ff; border-left: 3px solid #1a1a2e; padding: 12px 16px; margin: 24px 0; font-size: 14px; color: #1a1a2e; }
        .footer { text-align: center; padding: 24px; color: #888; font-size: 13px; border-top: 1px solid #eee; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Savlink</h1>
        </div>
        <div class="content">
            <h2>Verify your email address</h2>
            <p>Hi {{ user_name }},</p>
            <p>Welcome to Savlink! To complete your registration and secure your account, please verify your email address by clicking the button below:</p>
            <p style="text-align: center; margin: 32px 0;">
                <a href="{{ verification_url }}" class="button">Verify Email Address</a>
            </p>
            <div class="notice">
                This verification link will expire in 24 hours for security reasons.
            </div>
            <p style="font-size: 14px; color: #666;">If you didn't create an account with Savlink, you can safely ignore this email.</p>
        </div>
        <div class="footer">
            <p>© {{ year }} Savlink</p>
        </div>
    </div>
</body>
</html>
        """,
        "text": """Verify your Savlink email address

Hi {{ user_name }},

Welcome to Savlink! To complete your registration and secure your account, please verify your email address by visiting this link:

{{ verification_url }}

This verification link will expire in 24 hours for security reasons.

If you didn't create an account with Savlink, you can safely ignore this email.

- Savlink
        """
    },
    
    "password_reset": {
        "subject": "Reset your Savlink password",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5; }
        .container { max-width: 560px; margin: 40px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .header { background: #1a1a2e; color: #fff; padding: 32px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; font-weight: 600; }
        .content { padding: 32px; }
        .content p { margin: 0 0 16px; color: #555; }
        .button { display: inline-block; background: #1a1a2e; color: #fff !important; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 500; }
        .notice { background: #fef3c7; border-left: 3px solid #f59e0b; padding: 12px 16px; margin: 24px 0; font-size: 14px; color: #92400e; }
        .meta { font-size: 13px; color: #888; margin-top: 24px; padding-top: 16px; border-top: 1px solid #eee; }
        .footer { text-align: center; padding: 24px; color: #888; font-size: 13px; border-top: 1px solid #eee; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Savlink</h1>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>We received a request to reset your password. Click the button below to choose a new one:</p>
            <p style="text-align: center; margin: 32px 0;">
                <a href="{{ reset_url }}" class="button">Reset Password</a>
            </p>
            <div class="notice">
                This link expires in 1 hour and can only be used once.
            </div>
            <p style="font-size: 14px; color: #666;">If you didn't request this, you can safely ignore this email.</p>
            <div class="meta">
                <p><strong>Request details:</strong></p>
                <p>Time: {{ request_time }}<br>IP: {{ ip_address }}<br>Device: {{ device_info }}</p>
            </div>
        </div>
        <div class="footer">
            <p>© {{ year }} Savlink</p>
        </div>
    </div>
</body>
</html>
        """,
        "text": """Reset your Savlink password

Hi {{ user_name }},

We received a request to reset your password. Visit this link to choose a new one:

{{ reset_url }}

This link expires in 1 hour and can only be used once.

If you didn't request this, you can safely ignore this email.

Request details:
- Time: {{ request_time }}
- IP: {{ ip_address }}
- Device: {{ device_info }}

- Savlink
        """
    },
    
    "link_expiration_alert": {
        "subject": "Your Savlink is expiring soon",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5; }
        .container { max-width: 560px; margin: 40px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .header { background: #1a1a2e; color: #fff; padding: 32px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; font-weight: 600; }
        .content { padding: 32px; }
        .content p { margin: 0 0 16px; color: #555; }
        .link-box { background: #f8f9fa; border: 1px solid #e9ecef; padding: 16px; border-radius: 8px; margin: 20px 0; }
        .link-box .label { color: #6c757d; font-size: 12px; text-transform: uppercase; margin-bottom: 4px; }
        .link-box .value { font-size: 14px; color: #333; word-break: break-all; }
        .button { display: inline-block; background: #1a1a2e; color: #fff !important; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 500; }
        .footer { text-align: center; padding: 24px; color: #888; font-size: 13px; border-top: 1px solid #eee; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Savlink</h1>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>One of your links is about to expire:</p>
            <div class="link-box">
                <div class="label">Short URL</div>
                <div class="value">{{ short_url }}</div>
                <div class="label" style="margin-top: 12px;">Expires</div>
                <div class="value" style="color: #dc3545;">{{ expires_at }}</div>
            </div>
            <p>To keep this link active, extend its expiration from your dashboard.</p>
            <p style="text-align: center; margin-top: 24px;">
                <a href="{{ dashboard_url }}" class="button">Manage Link</a>
            </p>
        </div>
        <div class="footer">
            <p>© {{ year }} Savlink</p>
        </div>
    </div>
</body>
</html>
        """,
        "text": """Your Savlink is expiring soon

Hi {{ user_name }},

One of your links is about to expire:

Short URL: {{ short_url }}
Expires: {{ expires_at }}

To keep this link active, extend its expiration from your dashboard: {{ dashboard_url }}

- Savlink
        """
    },
    
    "link_expiration_warning": {
        "subject": "Your Savlink expires in {{ hours }} hours",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5; }
        .container { max-width: 560px; margin: 40px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .header { background: #1a1a2e; color: #fff; padding: 32px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; font-weight: 600; }
        .content { padding: 32px; }
        .content p { margin: 0 0 16px; color: #555; }
        .link-card { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 16px; margin: 20px 0; }
        .link-card .title { font-weight: 600; color: #1a1a2e; margin-bottom: 4px; }
        .link-card .url { color: #666; font-size: 14px; word-break: break-all; }
        .link-card .expires { color: #dc3545; font-size: 14px; margin-top: 8px; }
        .button { display: inline-block; background: #1a1a2e; color: #fff !important; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 500; }
        .footer { text-align: center; padding: 24px; color: #888; font-size: 13px; border-top: 1px solid #eee; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Savlink</h1>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>Your shortened link is about to expire:</p>
            <div class="link-card">
                <div class="title">{{ link_title }}</div>
                <div class="url">{{ short_url }}</div>
                <div class="expires">Expires in {{ hours }} hours</div>
            </div>
            <p>After expiration, this link will no longer redirect to its destination.</p>
            <p style="text-align: center; margin-top: 24px;">
                <a href="{{ dashboard_url }}" class="button">Extend Link</a>
            </p>
        </div>
        <div class="footer">
            <p>© {{ year }} Savlink</p>
        </div>
    </div>
</body>
</html>
        """,
        "text": """Your Savlink expires in {{ hours }} hours

Hi {{ user_name }},

Your shortened link is about to expire:

{{ link_title }}
{{ short_url }}
Expires in {{ hours }} hours

After expiration, this link will no longer redirect.

Extend it here: {{ dashboard_url }}

- Savlink
        """
    },
    
    "broken_link_alert": {
        "subject": "Broken link detected in your Savlink",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5; }
        .container { max-width: 560px; margin: 40px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .header { background: #1a1a2e; color: #fff; padding: 32px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; font-weight: 600; }
        .content { padding: 32px; }
        .content p { margin: 0 0 16px; color: #555; }
        .alert { background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 16px; margin: 20px 0; }
        .alert .title { font-weight: 600; color: #856404; margin-bottom: 4px; }
        .alert .url { color: #666; font-size: 14px; word-break: break-all; }
        .alert .error { color: #dc3545; font-size: 14px; margin-top: 8px; }
        .button { display: inline-block; background: #1a1a2e; color: #fff !important; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 500; }
        .footer { text-align: center; padding: 24px; color: #888; font-size: 13px; border-top: 1px solid #eee; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Savlink</h1>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>We detected a broken link in your collection:</p>
            <div class="alert">
                <div class="title">{{ link_title }}</div>
                <div class="url">{{ original_url }}</div>
                <div class="error">Error: {{ error_message }}</div>
            </div>
            <p>This link may have been moved, deleted, or the server is temporarily unavailable.</p>
            <p style="text-align: center; margin-top: 24px;">
                <a href="{{ dashboard_url }}" class="button">Fix Link</a>
            </p>
        </div>
        <div class="footer">
            <p>© {{ year }} Savlink</p>
        </div>
    </div>
</body>
</html>
        """,
        "text": """Broken link detected in your Savlink

Hi {{ user_name }},

We detected a broken link in your collection:

{{ link_title }}
{{ original_url }}
Error: {{ error_message }}

This link may have been moved, deleted, or temporarily unavailable.

Fix it here: {{ dashboard_url }}

- Savlink
        """
    },
    
    "weekly_digest": {
        "subject": "Your Savlink Weekly Digest",
        "html": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5; }
        .container { max-width: 560px; margin: 40px auto; background: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .header { background: #1a1a2e; color: #fff; padding: 32px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; font-weight: 600; }
        .content { padding: 32px; }
        .stats { display: flex; justify-content: space-around; margin: 24px 0; }
        .stat { text-align: center; }
        .stat .number { font-size: 32px; font-weight: 700; color: #1a1a2e; }
        .stat .label { font-size: 12px; color: #888; text-transform: uppercase; }
        .section { margin: 24px 0; }
        .section h3 { margin: 0 0 12px; font-size: 16px; color: #1a1a2e; }
        .link-item { padding: 8px 0; border-bottom: 1px solid #eee; }
        .link-item:last-child { border-bottom: none; }
        .link-item .title { font-weight: 500; }
        .link-item .clicks { color: #888; font-size: 14px; }
        .button { display: inline-block; background: #1a1a2e; color: #fff !important; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 500; }
        .footer { text-align: center; padding: 24px; color: #888; font-size: 13px; border-top: 1px solid #eee; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Weekly Digest</h1>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>Here's your Savlink activity for the past week:</p>
            
            <div class="stats">
                <div class="stat">
                    <div class="number">{{ total_links }}</div>
                    <div class="label">Total Links</div>
                </div>
                <div class="stat">
                    <div class="number">{{ new_links }}</div>
                    <div class="label">New Links</div>
                </div>
                <div class="stat">
                    <div class="number">{{ total_clicks }}</div>
                    <div class="label">Total Clicks</div>
                </div>
            </div>
            
            {% if top_links %}
            <div class="section">
                <h3>Top Performing Links</h3>
                {% for link in top_links %}
                <div class="link-item">
                    <div class="title">{{ link.title }}</div>
                    <div class="clicks">{{ link.clicks }} clicks</div>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            <p style="text-align: center; margin-top: 24px;">
                <a href="{{ dashboard_url }}" class="button">View Dashboard</a>
            </p>
        </div>
        <div class="footer">
            <p>© {{ year }} Savlink</p>
        </div>
    </div>
</body>
</html>
        """,
        "text": """Your Savlink Weekly Digest

Hi {{ user_name }},

Here's your activity for the past week:

Total Links: {{ total_links }}
New Links: {{ new_links }}
Total Clicks: {{ total_clicks }}

{% if top_links %}
Top Performing Links:
{% for link in top_links %}
- {{ link.title }}: {{ link.clicks }} clicks
{% endfor %}
{% endif %}

View Dashboard: {{ dashboard_url }}

- Savlink
        """
    }
}


class BrevoEmailService:
    _instance = None
    _redis_client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        self.smtp_server = current_app.config.get("BREVO_SMTP_SERVER", "smtp-relay.brevo.com")
        self.smtp_port = current_app.config.get("BREVO_SMTP_PORT", 587)
        self.smtp_username = current_app.config.get("BREVO_SMTP_USERNAME")
        self.smtp_password = current_app.config.get("BREVO_SMTP_PASSWORD")
        self.api_key = current_app.config.get("BREVO_API_KEY")
        
        self.sender_email = current_app.config.get("BREVO_SENDER_EMAIL", "noreply@savlink.app")
        self.sender_name = current_app.config.get("BREVO_SENDER_NAME", "Savlink")
        self.reply_to_email = current_app.config.get("REPLY_TO_EMAIL", self.sender_email)
        
        self.frontend_url = current_app.config.get("FRONTEND_URL", "http://localhost:3000")
        self.base_url = current_app.config.get("BASE_URL", "http://localhost:5000")
        self.environment = current_app.config.get("FLASK_ENV", "development")
        
        self.api_base_url = "https://api.brevo.com/v3"
        
        self.email_enabled = False
        self.smtp_enabled = False
        self.api_enabled = False
        self.is_configured = False
        
        self._init_redis()
        self._initialize_email_service()
        
        if self.email_enabled:
            self._start_email_worker()
            logger.info("Email service initialized")
        else:
            logger.warning("Email service disabled - no valid configuration")

    def _init_redis(self):
        try:
            redis_url = current_app.config.get("REDIS_URL")
            if not redis_url:
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
            
        except Exception as e:
            logger.error(f"Email service Redis connection failed: {e}")
            BrevoEmailService._redis_client = None

    @property
    def redis_client(self):
        return BrevoEmailService._redis_client

    def _initialize_email_service(self):
        if self.api_key and self.sender_email:
            self.api_enabled = self._test_api_connection()
            if self.api_enabled:
                logger.info("Using Brevo API for email delivery")
                self.email_enabled = True
                self.is_configured = True
                return
        
        if self.smtp_username and self.smtp_password:
            self.smtp_enabled = self._test_smtp_connection_safe()
            if self.smtp_enabled:
                logger.info("Using Brevo SMTP for email delivery")
                self.email_enabled = True
                self.is_configured = True
                return

    def _test_smtp_connection_safe(self) -> bool:
        try:
            timeout = 5 if self.environment == 'production' else 10
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.smtp_server, self.smtp_port))
            sock.close()
            
            if result != 0:
                return False
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=timeout)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.quit()
            
            return True
            
        except Exception as e:
            logger.warning(f"SMTP connection test failed: {e}")
            return False

    def _test_api_connection(self) -> bool:
        if not self.api_key:
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
            
            return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Brevo API connection test failed: {e}")
            return False

    def _start_email_worker(self):
        # Get the Flask app instance when starting the worker
        flask_app = current_app._get_current_object()
        
        def worker(app):
            while True:
                try:
                    with app.app_context():
                        if self.redis_client and self.email_enabled:
                            email_json = self.redis_client.lpop('savlink:email_queue')
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

        thread = threading.Thread(target=worker, args=(flask_app,), daemon=True, name="SavlinkEmailWorker")
        thread.start()

    def _send_email(self, email_data: Dict, retry_count: int = 0):
        if not self.email_enabled:
            self._store_fallback_email(email_data)
            return False
        
        if self.api_enabled:
            success = self._send_email_api(email_data, retry_count)
            if success:
                return True
        
        if self.smtp_enabled:
            success = self._send_email_smtp(email_data, retry_count)
            if success:
                return True
        
        self._store_fallback_email(email_data)
        return False

    def _send_email_smtp(self, email_data: Dict, retry_count: int = 0) -> bool:
        try:
            timeout = 10 if self.environment == 'production' else 30
            
            message = MIMEMultipart("alternative")
            message["Subject"] = email_data['subject']
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = email_data['to']
            message["Reply-To"] = self.reply_to_email
            message["X-Mailer"] = "Savlink/1.0"
            message["Message-ID"] = f"<{uuid.uuid4()}@savlink.app>"
            message["Date"] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
            
            if email_data.get('text'):
                message.attach(MIMEText(email_data['text'], "plain", "utf-8"))
            
            if email_data.get('html'):
                message.attach(MIMEText(email_data['html'], "html", "utf-8"))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=timeout)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(message)
            server.quit()
            
            logger.info(f"Email sent via SMTP to {email_data['to']}")
            self._store_sent_status(email_data, 'smtp')
            return True
            
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            if retry_count < 2:
                time.sleep(2 ** retry_count)
                return self._send_email_smtp(email_data, retry_count + 1)
            return False

    def _send_email_api(self, email_data: Dict, retry_count: int = 0) -> bool:
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
            'tags': ['transactional', 'savlink']
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
                logger.info(f"Email sent via API to {email_data['to']} (ID: {message_id})")
                self._store_sent_status(email_data, 'api', message_id)
                return True
            else:
                if retry_count < 2:
                    time.sleep(2 ** retry_count)
                    return self._send_email_api(email_data, retry_count + 1)
                return False
                    
        except Exception as e:
            logger.error(f"API request failed: {e}")
            if retry_count < 2:
                time.sleep(2 ** retry_count)
                return self._send_email_api(email_data, retry_count + 1)
            return False

    def _store_sent_status(self, email_data: Dict, method: str, message_id: str = None):
        if not self.redis_client:
            return
            
        try:
            self.redis_client.setex(
                f"savlink:email_sent:{email_data['id']}",
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
        except Exception:
            pass

    def _store_fallback_email(self, email_data: Dict):
        if not self.redis_client:
            logger.warning(f"Fallback email for {email_data['to']}")
            if email_data.get('reset_token'):
                reset_url = f"{self.frontend_url}/reset-password?token={email_data['reset_token']}"
                logger.info(f"Password reset link: {reset_url}")
            elif email_data.get('verification_token'):
                verify_url = f"{self.frontend_url}/verify-email?token={email_data['verification_token']}"
                logger.info(f"Email verification link: {verify_url}")
            return
            
        email_data['failed_at'] = datetime.utcnow().isoformat()
        
        key = f"savlink:email_fallback:{uuid.uuid4()}"
        self.redis_client.setex(key, 604800, json.dumps(email_data))
        self.redis_client.rpush('savlink:email_fallback_queue', key)

    def _render_template(self, template_name: str, context: dict) -> tuple:
        template = TEMPLATES.get(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")
        
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
        verification_token: str = None,
        to_name: str = ""
    ) -> bool:
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
            'verification_token': verification_token,
            'environment': self.environment
        }

        if not self.email_enabled:
            self._store_fallback_email(email_data)
            
            if reset_token:
                reset_url = f"{self.frontend_url}/reset-password?token={reset_token}"
                logger.info(f"Password reset link for {to}: {reset_url}")
            
            if verification_token:
                verify_url = f"{self.frontend_url}/verify-email?token={verification_token}"
                logger.info(f"Email verification link for {to}: {verify_url}")
            
            return True

        if self.redis_client:
            queue_key = 'savlink:email_queue'
            if priority == 'high':
                self.redis_client.lpush(queue_key, json.dumps(email_data))
            else:
                self.redis_client.rpush(queue_key, json.dumps(email_data))
        else:
            threading.Thread(
                target=self._send_email,
                args=(email_data,),
                daemon=True
            ).start()
        
        return True

    def send_welcome_email(
        self,
        to_email: str,
        user_name: str = None,
        async_send: bool = True
    ) -> bool:
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

    def send_email_verification(
        self,
        to_email: str,
        verification_token: str,
        user_name: str = None,
        async_send: bool = True
    ) -> bool:
        """Send email verification email"""
        try:
            if not user_name:
                user_name = to_email.split('@')[0].replace('.', ' ').title()
            
            verification_url = f"{self.frontend_url}/verify-email?token={verification_token}"
            
            context = {
                "user_name": user_name,
                "verification_url": verification_url
            }
            
            subject, html_content, text_content = self._render_template("email_verification", context)
            
            if async_send:
                return self.queue_email(
                    to=to_email,
                    subject=subject,
                    html=html_content,
                    text=text_content,
                    priority='high',
                    verification_token=verification_token,
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
                    'verification_token': verification_token,
                    'timestamp': datetime.utcnow().isoformat()
                }
                return self._send_email(email_data)
                
        except Exception as e:
            logger.error(f"Failed to send verification email: {e}")
            return False

    def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        user_name: str = None,
        request_info: dict = None,
        async_send: bool = True
    ) -> bool:
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

    def send_expiration_warning(
        self,
        to_email: str,
        link_title: str,
        short_url: str,
        hours_remaining: int,
        user_name: str = None,
        async_send: bool = True
    ) -> bool:
        try:
            if not user_name:
                user_name = to_email.split('@')[0].replace('.', ' ').title()

            context = {
                "user_name": user_name,
                "link_title": link_title or short_url,
                "short_url": short_url,
                "hours": hours_remaining
            }

            subject, html_content, text_content = self._render_template(
                "link_expiration_warning", context
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
            logger.error(f"Failed to send expiration warning: {e}")
            return False

    def send_broken_link_alert(
        self,
        to_email: str,
        link_title: str,
        original_url: str,
        error_message: str,
        user_name: str = None,
        async_send: bool = True
    ) -> bool:
        try:
            if not user_name:
                user_name = to_email.split('@')[0].replace('.', ' ').title()

            context = {
                "user_name": user_name,
                "link_title": link_title or original_url[:50],
                "original_url": original_url,
                "error_message": error_message
            }

            subject, html_content, text_content = self._render_template(
                "broken_link_alert", context
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
            logger.error(f"Failed to send broken link alert: {e}")
            return False

    def send_weekly_digest(
        self,
        to_email: str,
        total_links: int,
        new_links: int,
        total_clicks: int,
        top_links: list,
        user_name: str = None,
        async_send: bool = True
    ) -> bool:
        try:
            if not user_name:
                user_name = to_email.split('@')[0].replace('.', ' ').title()

            context = {
                "user_name": user_name,
                "total_links": total_links,
                "new_links": new_links,
                "total_clicks": total_clicks,
                "top_links": top_links
            }

            subject, html_content, text_content = self._render_template(
                "weekly_digest", context
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
            logger.error(f"Failed to send weekly digest: {e}")
            return False

    def get_queue_stats(self) -> Dict:
        stats = {
            'queue_size': 0,
            'fallback_queue_size': 0,
            'smtp_enabled': self.smtp_enabled,
            'api_enabled': self.api_enabled,
            'email_enabled': self.email_enabled,
            'environment': self.environment,
            'sender': self.sender_email
        }
        
        if not self.redis_client:
            return stats
            
        try:
            stats['queue_size'] = self.redis_client.llen('savlink:email_queue')
            stats['fallback_queue_size'] = self.redis_client.llen('savlink:email_fallback_queue')
            keys = self.redis_client.keys('savlink:email_sent:*')
            stats['sent_count_24h'] = len(keys)
            return stats
        except Exception as e:
            stats['error'] = str(e)
            return stats

    def get_fallback_emails(self, limit: int = 10) -> list:
        """Get emails that failed to send (for manual retry)"""
        if not self.redis_client:
            return []
        
        try:
            fallback_keys = self.redis_client.lrange('savlink:email_fallback_queue', 0, limit - 1)
            emails = []
            
            for key in fallback_keys:
                email_data = self.redis_client.get(key)
                if email_data:
                    emails.append(json.loads(email_data))
            
            return emails
        except Exception as e:
            logger.error(f"Failed to get fallback emails: {e}")
            return []

    def retry_failed_emails(self, max_retry: int = 5) -> int:
        """Retry failed emails from fallback queue"""
        if not self.redis_client or not self.email_enabled:
            return 0
        
        retried = 0
        try:
            for _ in range(max_retry):
                key = self.redis_client.lpop('savlink:email_fallback_queue')
                if not key:
                    break
                
                email_data = self.redis_client.get(key)
                if email_data:
                    email_dict = json.loads(email_data)
                    if self._send_email(email_dict):
                        retried += 1
                        self.redis_client.delete(key)
                    else:
                        # Put back in queue
                        self.redis_client.rpush('savlink:email_fallback_queue', key)
                        break
            
            logger.info(f"Retried {retried} failed emails")
            return retried
        except Exception as e:
            logger.error(f"Email retry failed: {e}")
            return retried


_email_service_instance = None


def get_email_service() -> BrevoEmailService:
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = BrevoEmailService()
    return _email_service_instance


class EmailService:
    def __new__(cls):
        return get_email_service()