# server/app/utils/helpers.py

import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List
from urllib.parse import urlparse


def hash_string(value: str, algorithm: str = "sha256") -> str:
    if algorithm == "md5":
        return hashlib.md5(value.encode()).hexdigest()
    elif algorithm == "sha256":
        return hashlib.sha256(value.encode()).hexdigest()
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")


def truncate_string(value: str, max_length: int = 100, suffix: str = "...") -> str:
    if not value or len(value) <= max_length:
        return value or ""
    
    return value[:max_length - len(suffix)] + suffix


def extract_domain(url: str, include_subdomain: bool = False) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        
        domain = domain.split(":")[0]
        
        if not include_subdomain and domain.startswith("www."):
            domain = domain[4:]
        
        return domain.lower()
    except Exception:
        return ""


def format_number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return str(value)


def time_ago(dt: datetime) -> str:
    if not dt:
        return "never"
    
    now = datetime.utcnow()
    diff = now - dt
    
    seconds = int(diff.total_seconds())
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h ago"
    elif seconds < 604800:
        days = seconds // 86400
        return f"{days}d ago"
    elif seconds < 2592000:
        weeks = seconds // 604800
        return f"{weeks}w ago"
    else:
        return dt.strftime("%b %d, %Y")


def parse_duration(duration_str: str) -> Optional[timedelta]:
    patterns = {
        r'^(\d+)\s*m(?:in(?:ute)?s?)?$': lambda m: timedelta(minutes=int(m)),
        r'^(\d+)\s*h(?:our)?s?$': lambda m: timedelta(hours=int(m)),
        r'^(\d+)\s*d(?:ay)?s?$': lambda m: timedelta(days=int(m)),
        r'^(\d+)\s*w(?:eek)?s?$': lambda m: timedelta(weeks=int(m)),
        r'^(\d+)\s*mo(?:nth)?s?$': lambda m: timedelta(days=int(m) * 30),
    }
    
    duration_str = duration_str.lower().strip()
    
    for pattern, factory in patterns.items():
        match = re.match(pattern, duration_str)
        if match:
            return factory(match.group(1))
    
    return None


def safe_get(data: Dict, *keys, default: Any = None) -> Any:
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data


def chunks(lst: List, size: int):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def clean_dict(d: Dict, remove_none: bool = True, remove_empty: bool = False) -> Dict:
    result = {}
    for key, value in d.items():
        if remove_none and value is None:
            continue
        if remove_empty and value in ("", [], {}):
            continue
        result[key] = value
    return result


def generate_cache_key(*parts) -> str:
    key_parts = [str(p) for p in parts if p is not None]
    return ":".join(key_parts)


def is_valid_uuid(value: str) -> bool:
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    return bool(uuid_pattern.match(value))


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    
    local, domain = email.split("@", 1)
    
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"


def mask_url(url: str, show_domain: bool = True) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        
        if show_domain:
            return f"{parsed.scheme}://{domain}/***"
        else:
            return f"{parsed.scheme}://***/***"
    except Exception:
        return "***"
