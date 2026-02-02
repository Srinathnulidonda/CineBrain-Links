# server/app/services/metadata_service.py

import hashlib
import logging
import re
from typing import Optional, Dict
from urllib.parse import urlparse, urljoin
from threading import Thread

import requests
from bs4 import BeautifulSoup

from flask import current_app

from app.extensions import db
from app.models.link import Link
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)


class MetadataService:

    REQUEST_TIMEOUT = 10
    MAX_CONTENT_LENGTH = 1024 * 1024

    @staticmethod
    def fetch_metadata(url: str) -> dict:
        url_hash = hashlib.md5(url.encode()).hexdigest()

        try:
            redis = RedisService()
            cached = redis.get_cached_metadata(url_hash)
            if cached:
                return cached
        except Exception:
            pass

        metadata = {
            "title": None,
            "description": None,
            "image": None,
            "favicon": None,
            "site_name": None,
            "type": None,
        }

        try:
            response = requests.get(
                url,
                timeout=MetadataService.REQUEST_TIMEOUT,
                headers={
                    "User-Agent": "Savlink Metadata Fetcher/1.0 (+https://savlink.vercel.app)",
                    "Accept": "text/html,application/xhtml+xml,*/*"
                },
                allow_redirects=True,
                stream=True
            )

            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > MetadataService.MAX_CONTENT_LENGTH:
                logger.warning(f"Content too large for {url}")
                return metadata

            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type.lower():
                return metadata

            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > MetadataService.MAX_CONTENT_LENGTH:
                    break

            response.close()

            soup = BeautifulSoup(content, 'html.parser')
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            og_title = soup.find('meta', property='og:title')
            og_description = soup.find('meta', property='og:description')
            og_image = soup.find('meta', property='og:image')
            og_site_name = soup.find('meta', property='og:site_name')
            og_type = soup.find('meta', property='og:type')

            twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
            twitter_description = soup.find('meta', attrs={'name': 'twitter:description'})
            twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})

            meta_description = soup.find('meta', attrs={'name': 'description'})

            title_tag = soup.find('title')

            if og_title and og_title.get('content'):
                metadata['title'] = og_title['content'][:255]
            elif twitter_title and twitter_title.get('content'):
                metadata['title'] = twitter_title['content'][:255]
            elif title_tag and title_tag.string:
                metadata['title'] = title_tag.string.strip()[:255]

            if og_description and og_description.get('content'):
                metadata['description'] = og_description['content'][:1000]
            elif twitter_description and twitter_description.get('content'):
                metadata['description'] = twitter_description['content'][:1000]
            elif meta_description and meta_description.get('content'):
                metadata['description'] = meta_description['content'][:1000]

            if og_image and og_image.get('content'):
                metadata['image'] = MetadataService._resolve_url(og_image['content'], base_url)
            elif twitter_image and twitter_image.get('content'):
                metadata['image'] = MetadataService._resolve_url(twitter_image['content'], base_url)

            if og_site_name and og_site_name.get('content'):
                metadata['site_name'] = og_site_name['content'][:100]

            if og_type and og_type.get('content'):
                metadata['type'] = og_type['content'][:50]

            metadata['favicon'] = MetadataService._fetch_favicon(soup, base_url)

            try:
                redis = RedisService()
                redis.cache_metadata(url_hash, metadata, ttl=86400)
            except Exception:
                pass

            return metadata

        except requests.exceptions.Timeout:
            logger.warning(f"Metadata fetch timeout for {url}")
            return metadata
        except requests.exceptions.RequestException as e:
            logger.warning(f"Metadata fetch failed for {url}: {e}")
            return metadata
        except Exception as e:
            logger.error(f"Metadata parsing error for {url}: {e}")
            return metadata

    @staticmethod
    def _resolve_url(url: str, base_url: str) -> str:
        if url.startswith('//'):
            return f"https:{url}"
        elif url.startswith('/'):
            return urljoin(base_url, url)
        elif not url.startswith(('http://', 'https://')):
            return urljoin(base_url, url)
        return url

    @staticmethod
    def _fetch_favicon(soup: BeautifulSoup, base_url: str) -> Optional[str]:
        icon_links = soup.find_all('link', rel=lambda x: x and 'icon' in x.lower() if x else False)

        for link in icon_links:
            href = link.get('href')
            if href:
                return MetadataService._resolve_url(href, base_url)

        return f"{base_url}/favicon.ico"

    @staticmethod
    def update_link_metadata(link: Link, async_update: bool = True) -> None:
        if async_update:
            app = current_app._get_current_object()
            Thread(
                target=MetadataService._update_link_metadata_async,
                args=(app, link.id),
                daemon=True
            ).start()
        else:
            MetadataService._update_link_metadata_sync(link)

    @staticmethod
    def _update_link_metadata_async(app, link_id: str) -> None:
        with app.app_context():
            try:
                link = Link.query.get(link_id)
                if link:
                    MetadataService._update_link_metadata_sync(link)
            except Exception as e:
                logger.error(f"Async metadata update failed: {e}")

    @staticmethod
    def _update_link_metadata_sync(link: Link) -> None:
        try:
            metadata = MetadataService.fetch_metadata(link.original_url)

            if metadata.get('title') and not link.title:
                link.og_title = metadata['title']

            if metadata.get('description'):
                link.og_description = metadata['description']

            if metadata.get('image'):
                link.og_image = metadata['image']

            if metadata.get('favicon'):
                link.favicon_url = metadata['favicon']

            db.session.commit()
            logger.debug(f"Updated metadata for link {link.id}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Metadata update failed for link {link.id}: {e}")

    @staticmethod
    def extract_domain(url: str) -> str:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return url

    @staticmethod
    def get_favicon_url(url: str) -> str:
        try:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            return f"{base_url}/favicon.ico"
        except Exception:
            return ""

    @staticmethod
    def suggest_title(url: str) -> Optional[str]:
        try:
            metadata = MetadataService.fetch_metadata(url)
            return metadata.get('title')
        except Exception:
            return None