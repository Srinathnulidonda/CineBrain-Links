# server/app/utils/validators.py

"""
Input validation utilities.
Strict validation for security and data integrity.
"""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse

from flask import current_app


class URLValidator:
    """Validator for URLs."""
    
    # Allowed URL schemes
    ALLOWED_SCHEMES = {"http", "https"}
    
    # Maximum URL length
    MAX_URL_LENGTH = 2048
    
    # Regex for basic URL structure
    URL_REGEX = re.compile(
        r'^(?:http|https)://'  # scheme
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    # Blocked domains (malicious, spam, etc.)
    BLOCKED_DOMAINS = {
        "bit.ly", "tinyurl.com", "goo.gl", "t.co",  # Other shorteners
        "localhost", "127.0.0.1", "0.0.0.0",  # Local addresses
    }
    
    @classmethod
    def validate(cls, url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate a URL.
        
        Args:
            url: URL to validate
        
        Returns:
            Tuple of (is_valid, normalized_url, error_message)
        """
        if not url:
            return False, None, "URL is required"
        
        url = url.strip()
        
        # Check length
        if len(url) > cls.MAX_URL_LENGTH:
            return False, None, f"URL exceeds maximum length of {cls.MAX_URL_LENGTH} characters"
        
        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception:
            return False, None, "Invalid URL format"
        
        # Check scheme
        if parsed.scheme.lower() not in cls.ALLOWED_SCHEMES:
            return False, None, f"URL scheme must be one of: {', '.join(cls.ALLOWED_SCHEMES)}"
        
        # Check for host
        if not parsed.netloc:
            return False, None, "URL must have a valid domain"
        
        # Extract domain without port
        domain = parsed.netloc.split(":")[0].lower()
        
        # Check against blocked domains
        if domain in cls.BLOCKED_DOMAINS:
            return False, None, "This domain is not allowed"
        
        # Check with regex
        if not cls.URL_REGEX.match(url):
            return False, None, "Invalid URL format"
        
        # Normalize URL
        normalized = url.strip()
        
        return True, normalized, None
    
    @classmethod
    def is_valid(cls, url: str) -> bool:
        """Quick check if URL is valid."""
        is_valid, _, _ = cls.validate(url)
        return is_valid


class InputValidator:
    """General input validator."""
    
    # Email regex (RFC 5322 simplified)
    EMAIL_REGEX = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    # Password requirements
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    
    # Slug requirements
    SLUG_REGEX = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$')
    
    @classmethod
    def validate_email(cls, email: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate email address.
        
        Args:
            email: Email to validate
        
        Returns:
            Tuple of (is_valid, normalized_email, error_message)
        """
        if not email:
            return False, None, "Email is required"
        
        email = email.strip().lower()
        
        if len(email) > 255:
            return False, None, "Email is too long"
        
        if not cls.EMAIL_REGEX.match(email):
            return False, None, "Invalid email format"
        
        return True, email, None
    
    @classmethod
    def validate_password(cls, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"
        
        if len(password) < cls.MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {cls.MIN_PASSWORD_LENGTH} characters"
        
        if len(password) > cls.MAX_PASSWORD_LENGTH:
            return False, f"Password must not exceed {cls.MAX_PASSWORD_LENGTH} characters"
        
        # Check for at least one uppercase letter
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        # Check for at least one lowercase letter
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        # Check for at least one digit
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        # Check for at least one special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, None
    
    @classmethod
    def validate_slug(cls, slug: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate custom slug.
        
        Args:
            slug: Slug to validate
        
        Returns:
            Tuple of (is_valid, normalized_slug, error_message)
        """
        if not slug:
            return False, None, "Slug is required"
        
        slug = slug.strip().lower()
        
        min_length = current_app.config.get("SLUG_MIN_LENGTH", 4)
        max_length = current_app.config.get("SLUG_MAX_LENGTH", 20)
        reserved_slugs = current_app.config.get("RESERVED_SLUGS", set())
        
        if len(slug) < min_length:
            return False, None, f"Slug must be at least {min_length} characters"
        
        if len(slug) > max_length:
            return False, None, f"Slug must not exceed {max_length} characters"
        
        if not cls.SLUG_REGEX.match(slug):
            return False, None, "Slug can only contain letters, numbers, hyphens, and underscores"
        
        if slug in reserved_slugs:
            return False, None, "This slug is reserved and cannot be used"
        
        return True, slug, None
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 255) -> str:
        """
        Sanitize a string input.
        
        Args:
            value: String to sanitize
            max_length: Maximum allowed length
        
        Returns:
            Sanitized string
        """
        if not value:
            return ""
        
        # Strip whitespace
        value = value.strip()
        
        # Truncate if too long
        if len(value) > max_length:
            value = value[:max_length]
        
        # Remove null bytes and other control characters
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
        
        return value