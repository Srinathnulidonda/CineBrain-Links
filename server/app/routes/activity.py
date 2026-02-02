# server/app/routes/activity.py

import logging
from datetime import datetime, timedelta

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models.activity_log import ActivityLog, ActivityType

activity_bp = Blueprint("activity", __name__)
logger = logging.getLogger(__name__)


def api_response():
    return current_app.api_response


@activity_bp.route("", methods=["GET"])
@jwt_required()
def get_activity():
    user_id = get_jwt_identity()

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 100)

    activity_type = request.args.get("type")
    resource_type = request.args.get("resource_type")
    days = request.args.get("days", 30, type=int)

    since = datetime.utcnow() - timedelta(days=min(days, 90))

    query = ActivityLog.query.filter(
        ActivityLog.user_id == user_id,
        ActivityLog.created_at >= since
    )

    if activity_type:
        try:
            query = query.filter(ActivityLog.activity_type == ActivityType(activity_type))
        except ValueError:
            pass

    if resource_type:
        query = query.filter(ActivityLog.resource_type == resource_type)

    query = query.order_by(ActivityLog.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return api_response().success(data={
        "activities": [a.to_dict() for a in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_pages": pagination.pages,
            "total_items": pagination.total
        }
    })


@activity_bp.route("/summary", methods=["GET"])
@jwt_required()
def get_activity_summary():
    user_id = get_jwt_identity()

    days = request.args.get("days", 7, type=int)
    since = datetime.utcnow() - timedelta(days=min(days, 30))

    from app.extensions import db

    counts = db.session.query(
        ActivityLog.activity_type,
        db.func.count().label("count")
    ).filter(
        ActivityLog.user_id == user_id,
        ActivityLog.created_at >= since
    ).group_by(ActivityLog.activity_type).all()

    summary = {at.value: 0 for at in ActivityType}
    for activity_type, count in counts:
        summary[activity_type.value] = count

    recent = ActivityLog.query.filter(
        ActivityLog.user_id == user_id
    ).order_by(ActivityLog.created_at.desc()).limit(10).all()

    return api_response().success(data={
        "summary": summary,
        "recent": [a.to_dict() for a in recent],
        "period_days": days
    })
