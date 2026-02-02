# server/app/utils/validators.py

import re
from typing import Optional, Tuple, List
from urllib.parse import urlparse

from flask import current_app


class URLValidator:
    ALLOWED_SCHEMES = {"http", "https"}
    BLOCKED_SCHEMES = {"javascript", "data", "vbscript", "file", "ftp", "mailto"}
    MAX_URL_LENGTH = 2048

    BLOCKED_DOMAINS = {
        "bit.ly", "tinyurl.com", "goo.gl", "t.co", "ow.ly", "is.gd",
        "buff.ly", "shorte.st", "cutt.ly", "rebrand.ly", "short.io",
        "tiny.cc", "bc.vc", "v.gd", "soo.gd",
        "localhost", "127.0.0.1", "0.0.0.0", "::1",
        "10.0.0.0", "172.16.0.0", "192.168.0.0"
    }

    @classmethod
    def validate(cls, url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        if not url:
            return False, None, "URL is required"

        url = url.strip()

        if len(url) > cls.MAX_URL_LENGTH:
            return False, None, f"URL is too long (max {cls.MAX_URL_LENGTH} characters)"

        try:
            parsed = urlparse(url)
        except Exception:
            return False, None, "Invalid URL format"

        scheme = parsed.scheme.lower()

        if scheme in cls.BLOCKED_SCHEMES:
            return False, None, "This URL type is not allowed"

        if scheme not in cls.ALLOWED_SCHEMES:
            return False, None, "URL must start with http:// or https://"

        if not parsed.netloc:
            return False, None, "URL must include a domain"

        domain = parsed.netloc.split(":")[0].lower()

        if domain in cls.BLOCKED_DOMAINS:
            return False, None, "This domain cannot be shortened"

        for blocked in cls.BLOCKED_DOMAINS:
            if domain.endswith(f".{blocked}"):
                return False, None, "This domain cannot be shortened"

        try:
            from app.utils.base_url import get_public_base_url, get_backend_base_url
            
            public_domain = urlparse(get_public_base_url()).netloc.lower()
            backend_domain = urlparse(get_backend_base_url()).netloc.lower()
            
            if domain == public_domain or domain == backend_domain:
                return False, None, "Cannot shorten Savlink URLs"
        except Exception:
            pass

        if cls._is_ip_address(domain):
            if cls._is_private_ip(domain):
                return False, None, "Private IP addresses are not allowed"

        return True, url, None

    @classmethod
    def _is_ip_address(cls, domain: str) -> bool:
        parts = domain.split(".")
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False

    @classmethod
    def _is_private_ip(cls, ip: str) -> bool:
        try:
            parts = [int(p) for p in ip.split(".")]
            if parts[0] == 10:
                return True
            if parts[0] == 172 and 16 <= parts[1] <= 31:
                return True
            if parts[0] == 192 and parts[1] == 168:
                return True
            if parts[0] == 127:
                return True
            return False
        except Exception:
            return False

    @classmethod
    def normalize(cls, url: str) -> str:
        url = url.strip()
        
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        return url


class InputValidator:
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    
    SLUG_REGEX = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$')
    
    FOLDER_NAME_REGEX = re.compile(r'^[\w\s\-\.]+$', re.UNICODE)
    TAG_NAME_REGEX = re.compile(r'^[\w\-]+$', re.UNICODE)

    @classmethod
    def validate_email(cls, email: str) -> Tuple[bool, Optional[str], Optional[str]]:
        if not email:
            return False, None, "Email is required"

        email = email.strip().lower()

        if len(email) > 255:
            return False, None, "Email is too long"

        if not cls.EMAIL_REGEX.match(email):
            return False, None, "Please enter a valid email address"

        return True, email, None

    @classmethod
    def validate_password(cls, password: str) -> Tuple[bool, Optional[str]]:
        if not password:
            return False, "Password is required"

        if len(password) < cls.MIN_PASSWORD_LENGTH:
            return False, f"Password must be at least {cls.MIN_PASSWORD_LENGTH} characters"

        if len(password) > cls.MAX_PASSWORD_LENGTH:
            return False, "Password is too long"

        if not re.search(r'[A-Z]', password):
            return False, "Password must include an uppercase letter"

        if not re.search(r'[a-z]', password):
            return False, "Password must include a lowercase letter"

        if not re.search(r'\d', password):
            return False, "Password must include a number"

        if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_=+\[\]\\;\'`~]', password):
            return False, "Password must include a special character"

        return True, None

    @classmethod
    def validate_slug(cls, slug: str) -> Tuple[bool, Optional[str], Optional[str]]:
        if not slug:
            return False, None, "Slug is required"

        slug = slug.strip().lower()

        min_len = current_app.config.get("SLUG_MIN_LENGTH", 3)
        max_len = current_app.config.get("SLUG_MAX_LENGTH", 32)
        reserved = current_app.config.get("RESERVED_SLUGS", set())

        if len(slug) < min_len:
            return False, None, f"Short link must be at least {min_len} characters"

        if len(slug) > max_len:
            return False, None, f"Short link cannot exceed {max_len} characters"

        if not cls.SLUG_REGEX.match(slug):
            return False, None, "Short link can only contain letters, numbers, hyphens, and underscores"

        if slug in reserved:
            return False, None, "This short link is reserved"

        if slug.startswith(('-', '_')) or slug.endswith(('-', '_')):
            return False, None, "Short link cannot start or end with hyphen or underscore"

        if '--' in slug or '__' in slug:
            return False, None, "Short link cannot contain consecutive hyphens or underscores"

        return True, slug, None

    @classmethod
    def validate_folder_name(cls, name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        if not name:
            return False, None, "Folder name is required"

        name = name.strip()

        if len(name) > 100:
            return False, None, "Folder name is too long (max 100 characters)"

        if len(name) < 1:
            return False, None, "Folder name is too short"

        return True, name, None

    @classmethod
    def validate_tag_name(cls, name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        if not name:
            return False, None, "Tag name is required"

        name = name.strip().lower()

        if len(name) > 50:
            return False, None, "Tag name is too long (max 50 characters)"

        if len(name) < 1:
            return False, None, "Tag name is too short"

        if not cls.TAG_NAME_REGEX.match(name):
            return False, None, "Tag name can only contain letters, numbers, and hyphens"

        return True, name, None

    @classmethod
    def validate_color(cls, color: str) -> Tuple[bool, Optional[str], Optional[str]]:
        if not color:
            return True, None, None

        color = color.strip()

        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        if hex_pattern.match(color):
            return True, color.upper(), None

        return False, None, "Color must be a valid hex code (e.g., #FF5733)"

    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 255) -> str:
        if not value:
            return ""

        value = value.strip()

        if len(value) > max_length:
            value = value[:max_length]

        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)

        return value

    @classmethod
    def sanitize_markdown(cls, value: str, max_length: int = 5000) -> str:
        if not value:
            return ""

        value = value.strip()

        if len(value) > max_length:
            value = value[:max_length]

        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
        ]

        for pattern in dangerous_patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE | re.DOTALL)

        return value

    @classmethod
    def validate_url_list(cls, urls: List[str]) -> Tuple[List[str], List[dict]]:
        valid_urls = []
        errors = []

        for url in urls:
            is_valid, normalized, error = URLValidator.validate(url)
            if is_valid:
                valid_urls.append(normalized)
            else:
                errors.append({"url": url[:100], "error": error})

        return valid_urls, errors
