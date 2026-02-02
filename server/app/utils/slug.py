# server/app/utils/slug.py

import secrets
import string
import hashlib
from typing import Optional, List

from flask import current_app

from app.extensions import db
from app.models.link import Link


class SlugGenerator:
    ALLOWED_CHARS = string.ascii_lowercase + string.digits
    AMBIGUOUS_CHARS = "0o1il"
    
    WORD_SAFE_CHARS = "abcdefghjkmnpqrstuvwxyz23456789"

    def __init__(self, exclude_ambiguous: bool = True):
        if exclude_ambiguous:
            self.chars = self.WORD_SAFE_CHARS
        else:
            self.chars = self.ALLOWED_CHARS

    def generate(self, length: Optional[int] = None) -> str:
        if length is None:
            length = current_app.config.get("AUTO_SLUG_LENGTH", 7)

        return "".join(secrets.choice(self.chars) for _ in range(length))

    def generate_unique(self, max_attempts: int = 10) -> Optional[str]:
        reserved_slugs = current_app.config.get("RESERVED_SLUGS", set())

        for _ in range(max_attempts):
            slug = self.generate()

            if slug in reserved_slugs:
                continue

            existing = Link.query.filter_by(slug=slug).first()
            if not existing:
                return slug

        for _ in range(max_attempts):
            slug = self.generate(length=10)

            if slug in reserved_slugs:
                continue

            existing = Link.query.filter_by(slug=slug).first()
            if not existing:
                return slug

        return None

    def generate_from_url(self, url: str, length: int = 7) -> str:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        result = ""
        for char in url_hash:
            if len(result) >= length:
                break
            if char in self.chars:
                result += char
        
        while len(result) < length:
            result += secrets.choice(self.chars)
        
        return result[:length]

    def generate_readable(self) -> str:
        adjectives = [
            "quick", "bright", "calm", "bold", "swift",
            "smart", "cool", "fresh", "keen", "neat"
        ]
        nouns = [
            "link", "path", "gate", "road", "jump",
            "dash", "step", "wave", "star", "flow"
        ]
        
        adj = secrets.choice(adjectives)
        noun = secrets.choice(nouns)
        num = secrets.randbelow(100)
        
        return f"{adj}{noun}{num}"

    @staticmethod
    def is_available(slug: str) -> bool:
        reserved_slugs = current_app.config.get("RESERVED_SLUGS", set())

        if slug.lower() in reserved_slugs:
            return False

        existing = Link.query.filter_by(slug=slug.lower()).first()
        return existing is None

    @staticmethod
    def normalize(slug: str) -> str:
        slug = slug.lower().strip()
        
        slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
        
        while '--' in slug:
            slug = slug.replace('--', '-')
        while '__' in slug:
            slug = slug.replace('__', '_')
        
        slug = slug.strip('-_')
        
        return slug

    @staticmethod
    def suggest_alternatives(slug: str, count: int = 5) -> List[str]:
        suggestions = []
        base_slug = SlugGenerator.normalize(slug)
        
        if not base_slug:
            generator = SlugGenerator()
            for _ in range(count):
                suggestions.append(generator.generate())
            return suggestions

        for i in range(1, 100):
            candidate = f"{base_slug}{i}"
            if SlugGenerator.is_available(candidate):
                suggestions.append(candidate)
                if len(suggestions) >= count:
                    break

        generator = SlugGenerator()
        while len(suggestions) < count:
            suffix = generator.generate(3)
            candidate = f"{base_slug}-{suffix}"
            if SlugGenerator.is_available(candidate):
                suggestions.append(candidate)

        return suggestions[:count]

    @staticmethod
    def validate_custom(slug: str) -> tuple:
        from app.utils.validators import InputValidator
        return InputValidator.validate_slug(slug)
