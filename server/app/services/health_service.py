# server/app/services/health_service.py

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests

from flask import current_app

from app.extensions import db
from app.models.link import Link
from app.models.link_health import LinkHealthCheck
from app.services.redis_service import RedisService

logger = logging.getLogger(__name__)


class HealthService:

    HEALTHY_STATUS_CODES = {200, 201, 202, 203, 204, 301, 302, 303, 307, 308}
    REQUEST_TIMEOUT = 10
    MAX_REDIRECTS = 5

    @staticmethod
    def check_url(url: str) -> dict:
        start_time = time.time()

        try:
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                return {
                    "is_healthy": False,
                    "error_message": "Invalid URL scheme"
                }

            response = requests.head(
                url,
                timeout=HealthService.REQUEST_TIMEOUT,
                allow_redirects=True,
                headers={
                    "User-Agent": "Savlink Health Checker/1.0",
                    "Accept": "*/*"
                }
            )

            response_time_ms = int((time.time() - start_time) * 1000)
            status_code = response.status_code

            if status_code == 405:
                response = requests.get(
                    url,
                    timeout=HealthService.REQUEST_TIMEOUT,
                    allow_redirects=True,
                    headers={
                        "User-Agent": "Savlink Health Checker/1.0",
                        "Accept": "*/*"
                    },
                    stream=True
                )
                response.close()
                status_code = response.status_code
                response_time_ms = int((time.time() - start_time) * 1000)

            is_healthy = status_code in HealthService.HEALTHY_STATUS_CODES

            return {
                "is_healthy": is_healthy,
                "status_code": status_code,
                "response_time_ms": response_time_ms,
                "error_message": None if is_healthy else f"HTTP {status_code}"
            }

        except requests.exceptions.Timeout:
            return {
                "is_healthy": False,
                "status_code": None,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error_message": "Request timed out"
            }
        except requests.exceptions.SSLError as e:
            return {
                "is_healthy": False,
                "status_code": None,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error_message": "SSL certificate error"
            }
        except requests.exceptions.ConnectionError as e:
            return {
                "is_healthy": False,
                "status_code": None,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error_message": "Connection failed"
            }
        except requests.exceptions.TooManyRedirects:
            return {
                "is_healthy": False,
                "status_code": None,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error_message": "Too many redirects"
            }
        except Exception as e:
            logger.warning(f"Health check failed for {url}: {e}")
            return {
                "is_healthy": False,
                "status_code": None,
                "response_time_ms": int((time.time() - start_time) * 1000),
                "error_message": str(e)[:255]
            }

    @staticmethod
    def check_link(link: Link) -> LinkHealthCheck:
        result = HealthService.check_url(link.original_url)

        health_check = LinkHealthCheck(
            link_id=link.id,
            is_healthy=result["is_healthy"],
            status_code=result.get("status_code"),
            response_time_ms=result.get("response_time_ms"),
            error_message=result.get("error_message")
        )

        link.last_checked_at = health_check.checked_at
        link.last_check_status = result.get("status_code")
        link.is_broken = not result["is_healthy"]

        db.session.add(health_check)
        db.session.commit()

        try:
            RedisService().cache_health_status(link.id, {
                "is_broken": link.is_broken,
                "last_checked_at": link.last_checked_at.isoformat(),
                "status_code": link.last_check_status
            })
        except Exception:
            pass

        return health_check

    @staticmethod
    def check_links_batch(links: List[Link], max_workers: int = 5) -> Dict[str, dict]:
        results = {}

        def check_single(link):
            result = HealthService.check_url(link.original_url)
            return link.id, link, result

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(check_single, link): link for link in links}

            for future in as_completed(futures):
                try:
                    link_id, link, result = future.result()
                    results[link_id] = result

                    health_check = LinkHealthCheck(
                        link_id=link.id,
                        is_healthy=result["is_healthy"],
                        status_code=result.get("status_code"),
                        response_time_ms=result.get("response_time_ms"),
                        error_message=result.get("error_message")
                    )

                    link.last_checked_at = health_check.checked_at
                    link.last_check_status = result.get("status_code")
                    link.is_broken = not result["is_healthy"]

                    db.session.add(health_check)

                except Exception as e:
                    logger.error(f"Batch health check error: {e}")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Batch health check commit failed: {e}")

        return results

    @staticmethod
    def get_stale_links(user_id: str, hours: int = 24, limit: int = 50) -> List[Link]:
        threshold = datetime.utcnow() - timedelta(hours=hours)

        return Link.query.filter(
            Link.user_id == user_id,
            Link.is_deleted == False,
            db.or_(
                Link.last_checked_at.is_(None),
                Link.last_checked_at < threshold
            )
        ).limit(limit).all()

    @staticmethod
    def get_broken_links(user_id: str) -> List[Link]:
        return Link.query.filter(
            Link.user_id == user_id,
            Link.is_deleted == False,
            Link.is_broken == True
        ).order_by(Link.last_checked_at.desc()).all()

    @staticmethod
    def get_health_history(link_id: str, limit: int = 20) -> List[LinkHealthCheck]:
        return LinkHealthCheck.query.filter_by(
            link_id=link_id
        ).order_by(LinkHealthCheck.checked_at.desc()).limit(limit).all()

    @staticmethod
    def get_health_summary(user_id: str) -> dict:
        total = Link.query.filter_by(
            user_id=user_id,
            is_deleted=False
        ).count()

        broken = Link.query.filter_by(
            user_id=user_id,
            is_deleted=False,
            is_broken=True
        ).count()

        never_checked = Link.query.filter(
            Link.user_id == user_id,
            Link.is_deleted == False,
            Link.last_checked_at.is_(None)
        ).count()

        threshold = datetime.utcnow() - timedelta(hours=24)
        stale = Link.query.filter(
            Link.user_id == user_id,
            Link.is_deleted == False,
            Link.last_checked_at < threshold
        ).count()

        return {
            "total_links": total,
            "broken_links": broken,
            "healthy_links": total - broken,
            "never_checked": never_checked,
            "stale_checks": stale,
            "health_percentage": round(((total - broken) / total * 100) if total > 0 else 100, 1)
        }

    @staticmethod
    def schedule_background_check(user_id: str) -> None:
        app = current_app._get_current_object()

        def run_checks():
            with app.app_context():
                try:
                    stale_links = HealthService.get_stale_links(user_id, hours=24, limit=20)
                    if stale_links:
                        HealthService.check_links_batch(stale_links, max_workers=3)
                        logger.info(f"Background health check completed for {len(stale_links)} links")
                except Exception as e:
                    logger.error(f"Background health check failed: {e}")

        Thread(target=run_checks, daemon=True).start()

    @staticmethod
    def cleanup_old_checks(days: int = 30) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)

        try:
            result = LinkHealthCheck.query.filter(
                LinkHealthCheck.checked_at < cutoff
            ).delete(synchronize_session=False)

            db.session.commit()
            logger.info(f"Cleaned up {result} old health checks")
            return result

        except Exception as e:
            db.session.rollback()
            logger.error(f"Health check cleanup failed: {e}")
            return 0