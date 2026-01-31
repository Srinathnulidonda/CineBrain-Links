# server/app/utils/slug.py

"""
Slug generation utilities.
"""

import secrets
import string
from typing import Optional

from flask import current_app

from app.extensions import db
from app.models.link import Link


class SlugGenerator:
    """Generator for unique URL slugs."""
    
    # Characters allowed in auto-generated slugs (URL-safe, no ambiguous chars)
    ALLOWED_CHARS = string.ascii_lowercase + string.digits
    AMBIGUOUS_CHARS = "0o1il"  # Removed to avoid confusion
    
    def __init__(self):
        """Initialize slug generator."""
        self.chars = "".join(
            c for c in self.ALLOWED_CHARS if c not in self.AMBIGUOUS_CHARS
        )
    
    def generate(self, length: Optional[int] = None) -> str:
        """
        Generate a random slug.
        
        Args:
            length: Length of the slug (default from config)
        
        Returns:
            Random slug string
        """
        if length is None:
            length = current_app.config.get("AUTO_SLUG_LENGTH", 7)
        
        return "".join(secrets.choice(self.chars) for _ in range(length))
    
    def generate_unique(self, max_attempts: int = 10) -> Optional[str]:
        """
        Generate a unique slug that doesn't exist in the database.
        
        Args:
            max_attempts: Maximum number of generation attempts
        
        Returns:
            Unique slug or None if unable to generate
        """
        reserved_slugs = current_app.config.get("RESERVED_SLUGS", set())
        
        for _ in range(max_attempts):
            slug = self.generate()
            
            # Check if reserved
            if slug in reserved_slugs:
                continue
            
            # Check database for uniqueness
            existing = Link.query.filter_by(slug=slug).first()
            if not existing:
                return slug
        
        # If we couldn't find a unique slug, try with longer length
        for _ in range(max_attempts):
            slug = self.generate(length=10)
            
            if slug in reserved_slugs:
                continue
            
            existing = Link.query.filter_by(slug=slug).first()
            if not existing:
                return slug
        
        return None
    
    @staticmethod
    def is_available(slug: str) -> bool:
        """
        Check if a slug is available.
        
        Args:
            slug: Slug to check
        
        Returns:
            True if slug is available
        """
        reserved_slugs = current_app.config.get("RESERVED_SLUGS", set())
        
        if slug.lower() in reserved_slugs:
            return False
        
        existing = Link.query.filter_by(slug=slug.lower()).first()
        return existing is None