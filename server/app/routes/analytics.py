# server/app/routes/analytics.py

import logging
from datetime import datetime, timedelta

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.link import Link, LinkType
from app.models.link_click import LinkClick
from app.utils.base_url import get_public_base_url

analytics_bp = Blueprint("analytics", __name__)
logger = logging.getLogger(__name__)


def api_response():
    return current_app.api_response


@analytics_bp.route("/links/<link_id>", methods=["GET"])
@jwt_required()
def get_link_analytics(link_id: str):
    user_id = get_jwt_identity()

    link = Link.query.filter_by(id=link_id, user_id=user_id, is_deleted=False).first()

    if not link:
        return api_response().error("Link not found", 404, "NOT_FOUND")

    if link.link_type != LinkType.SHORTENED:
        return api_response().error("Analytics only available for shortened links", 400)

    days = request.args.get("days", 30, type=int)
    days = min(days, 365)
    since = datetime.utcnow() - timedelta(days=days)

    clicks = LinkClick.query.filter(
        LinkClick.link_id == link_id,
        LinkClick.clicked_at >= since
    ).order_by(LinkClick.clicked_at.desc()).all()

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

    base_url = get_public_base_url()

    return api_response().success(data={
        "link": {
            "id": link.id,
            "slug": link.slug,
            "short_url": f"{base_url}/{link.slug}",
            "original_url": link.original_url,
            "title": link.title
        },
        "summary": {
            "total_clicks": link.clicks,
            "clicks_in_period": len(clicks),
            "unique_referrers": len(referrers),
            "last_clicked_at": link.last_clicked_at.isoformat() if link.last_clicked_at else None
        },
        "timeline": timeline,
        "referrers": [{"domain": k, "count": v} for k, v in sorted(referrers.items(), key=lambda x: x[1], reverse=True)[:10]],
        "devices": [{"type": k, "count": v} for k, v in sorted(devices.items(), key=lambda x: x[1], reverse=True)],
        "browsers": [{"name": k, "count": v} for k, v in sorted(browsers.items(), key=lambda x: x[1], reverse=True)[:10]],
        "countries": [{"code": k, "count": v} for k, v in sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]]
    })


@analytics_bp.route("/links/<link_id>/clicks", methods=["GET"])
@jwt_required()
def get_link_clicks(link_id: str):
    user_id = get_jwt_identity()

    link = Link.query.filter_by(id=link_id, user_id=user_id, is_deleted=False).first()

    if not link:
        return api_response().error("Link not found", 404, "NOT_FOUND")

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)

    query = LinkClick.query.filter_by(link_id=link_id).order_by(LinkClick.clicked_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return api_response().success(data={
        "clicks": [c.to_dict() for c in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total
        }
    })


@analytics_bp.route("/overview", methods=["GET"])
@jwt_required()
def get_analytics_overview():
    user_id = get_jwt_identity()

    days = request.args.get("days", 30, type=int)
    days = min(days, 365)
    since = datetime.utcnow() - timedelta(days=days)

    total_links = Link.query.filter_by(
        user_id=user_id,
        is_deleted=False,
        link_type=LinkType.SHORTENED
    ).count()

    total_clicks = db.session.query(db.func.sum(Link.clicks)).filter(
        Link.user_id == user_id,
        Link.is_deleted == False,
        Link.link_type == LinkType.SHORTENED
    ).scalar() or 0

    recent_clicks = LinkClick.query.join(Link).filter(
        Link.user_id == user_id,
        LinkClick.clicked_at >= since
    ).count()

    clicks_by_day = db.session.query(
        db.func.date(LinkClick.clicked_at).label("date"),
        db.func.count().label("count")
    ).join(Link).filter(
        Link.user_id == user_id,
        LinkClick.clicked_at >= since
    ).group_by(db.func.date(LinkClick.clicked_at)).all()

    timeline = {row.date.strftime("%Y-%m-%d"): row.count for row in clicks_by_day}

    formatted_timeline = []
    current = since.date()
    end = datetime.utcnow().date()
    while current <= end:
        key = current.strftime("%Y-%m-%d")
        formatted_timeline.append({"date": key, "clicks": timeline.get(key, 0)})
        current += timedelta(days=1)

    top_links = Link.query.filter_by(
        user_id=user_id,
        is_deleted=False,
        link_type=LinkType.SHORTENED
    ).order_by(Link.clicks.desc()).limit(10).all()

    base_url = get_public_base_url()

    return api_response().success(data={
        "summary": {
            "total_shortened_links": total_links,
            "total_clicks": int(total_clicks),
            "clicks_in_period": recent_clicks,
            "period_days": days
        },
        "timeline": formatted_timeline,
        "top_links": [
            {
                "id": l.id,
                "slug": l.slug,
                "short_url": f"{base_url}/{l.slug}",
                "title": l.title,
                "clicks": l.clicks
            }
            for l in top_links
        ]
    })