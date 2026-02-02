# server/app/services/click_service.py

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from threading import Thread

from flask import Request, current_app
from user_agents import parse as parse_user_agent

from app.extensions import db
from app.models.link import Link
from app.models.link_click import LinkClick

logger = logging.getLogger(__name__)


class ClickService:

    @staticmethod
    def parse_request(request: Request) -> dict:
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()

        ip_hash = None
        if ip_address:
            ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:64]

        user_agent_str = request.headers.get('User-Agent', '')
        referrer = request.headers.get('Referer', '')

        device_type = None
        browser = None
        os = None

        if user_agent_str:
            try:
                ua = parse_user_agent(user_agent_str)

                if ua.is_mobile:
                    device_type = "Mobile"
                elif ua.is_tablet:
                    device_type = "Tablet"
                elif ua.is_pc:
                    device_type = "Desktop"
                elif ua.is_bot:
                    device_type = "Bot"
                else:
                    device_type = "Other"

                browser = ua.browser.family[:50] if ua.browser.family else None
                os = ua.os.family[:50] if ua.os.family else None

            except Exception:
                if 'Mobile' in user_agent_str or 'Android' in user_agent_str:
                    device_type = "Mobile"
                elif 'iPad' in user_agent_str or 'Tablet' in user_agent_str:
                    device_type = "Tablet"
                else:
                    device_type = "Desktop"

        country_code = ClickService._get_country_from_headers(request)

        return {
            "ip_hash": ip_hash,
            "user_agent": user_agent_str[:512] if user_agent_str else None,
            "referrer": referrer[:512] if referrer else None,
            "device_type": device_type,
            "browser": browser,
            "os": os,
            "country_code": country_code,
        }

    @staticmethod
    def _get_country_from_headers(request: Request) -> Optional[str]:
        country = request.headers.get('CF-IPCountry')
        if country and country != 'XX':
            return country[:2].upper()

        country = request.headers.get('X-Country-Code')
        if country:
            return country[:2].upper()

        return None

    @staticmethod
    def record_click(
        link_id: str,
        request_data: dict,
        async_record: bool = True
    ) -> Optional[LinkClick]:
        if async_record:
            app = current_app._get_current_object()
            Thread(
                target=ClickService._record_click_async,
                args=(app, link_id, request_data),
                daemon=True
            ).start()
            return None
        else:
            return ClickService._create_click(link_id, request_data)

    @staticmethod
    def _record_click_async(app, link_id: str, request_data: dict) -> None:
        with app.app_context():
            try:
                ClickService._create_click(link_id, request_data)
            except Exception as e:
                logger.error(f"Async click recording failed: {e}")

    @staticmethod
    def _create_click(link_id: str, request_data: dict) -> Optional[LinkClick]:
        try:
            link = Link.query.get(link_id)
            if not link:
                return None

            if link.click_tracking_enabled:
                click = LinkClick(
                    link_id=link_id,
                    ip_hash=request_data.get("ip_hash"),
                    user_agent=request_data.get("user_agent"),
                    referrer=request_data.get("referrer"),
                    device_type=request_data.get("device_type"),
                    browser=request_data.get("browser"),
                    os=request_data.get("os"),
                    country_code=request_data.get("country_code"),
                )
                db.session.add(click)

            link.clicks += 1
            link.last_clicked_at = datetime.utcnow()

            db.session.commit()
            return click if link.click_tracking_enabled else None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Click recording failed: {e}")
            return None

    @staticmethod
    def get_link_analytics(link_id: str, days: int = 30) -> dict:
        since = datetime.utcnow() - timedelta(days=days)

        clicks = LinkClick.query.filter(
            LinkClick.link_id == link_id,
            LinkClick.clicked_at >= since
        ).all()

        clicks_by_day = {}
        referrers = {}
        devices = {}
        browsers = {}
        countries = {}

        for click in clicks:
            day_key = click.clicked_at.strftime("%Y-%m-%d")
            clicks_by_day[day_key] = clicks_by_day.get(day_key, 0) + 1

            if click.referrer_domain:
                referrers[click.referrer_domain] = referrers.get(click.referrer_domain, 0) + 1

            if click.device_type:
                devices[click.device_type] = devices.get(click.device_type, 0) + 1

            if click.browser:
                browsers[click.browser] = browsers.get(click.browser, 0) + 1

            if click.country_code:
                countries[click.country_code] = countries.get(click.country_code, 0) + 1

        timeline = []
        current = since.date()
        end = datetime.utcnow().date()
        while current <= end:
            key = current.strftime("%Y-%m-%d")
            timeline.append({"date": key, "clicks": clicks_by_day.get(key, 0)})
            current += timedelta(days=1)

        return {
            "total_in_period": len(clicks),
            "timeline": timeline,
            "referrers": sorted(
                [{"domain": k, "count": v} for k, v in referrers.items()],
                key=lambda x: x["count"],
                reverse=True
            )[:10],
            "devices": sorted(
                [{"type": k, "count": v} for k, v in devices.items()],
                key=lambda x: x["count"],
                reverse=True
            ),
            "browsers": sorted(
                [{"name": k, "count": v} for k, v in browsers.items()],
                key=lambda x: x["count"],
                reverse=True
            )[:10],
            "countries": sorted(
                [{"code": k, "count": v} for k, v in countries.items()],
                key=lambda x: x["count"],
                reverse=True
            )[:10],
        }

    @staticmethod
    def cleanup_old_clicks(days: int = 365) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)

        try:
            result = LinkClick.query.filter(
                LinkClick.clicked_at < cutoff
            ).delete(synchronize_session=False)

            db.session.commit()
            logger.info(f"Cleaned up {result} old clicks")
            return result

        except Exception as e:
            db.session.rollback()
            logger.error(f"Click cleanup failed: {e}")
            return 0

    @staticmethod
    def get_top_referrers(user_id: str, days: int = 30, limit: int = 10) -> List[dict]:
        since = datetime.utcnow() - timedelta(days=days)

        results = db.session.query(
            LinkClick.referrer_domain,
            db.func.count().label("count")
        ).join(Link).filter(
            Link.user_id == user_id,
            LinkClick.clicked_at >= since,
            LinkClick.referrer_domain.isnot(None)
        ).group_by(LinkClick.referrer_domain).order_by(
            db.desc("count")
        ).limit(limit).all()

        return [{"domain": r[0], "count": r[1]} for r in results]

    @staticmethod
    def get_device_breakdown(user_id: str, days: int = 30) -> dict:
        since = datetime.utcnow() - timedelta(days=days)

        results = db.session.query(
            LinkClick.device_type,
            db.func.count().label("count")
        ).join(Link).filter(
            Link.user_id == user_id,
            LinkClick.clicked_at >= since,
            LinkClick.device_type.isnot(None)
        ).group_by(LinkClick.device_type).all()

        total = sum(r[1] for r in results)
        breakdown = {}

        for device_type, count in results:
            breakdown[device_type] = {
                "count": count,
                "percentage": round((count / total * 100) if total > 0 else 0, 1)
            }

        return breakdown