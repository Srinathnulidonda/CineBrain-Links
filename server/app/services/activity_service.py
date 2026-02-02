# server/app/services/activity_service.py

import logging
from datetime import datetime
from typing import Optional, List
from threading import Thread

from flask import current_app, request

from app.extensions import db
from app.models.activity_log import ActivityLog, ActivityType

logger = logging.getLogger(__name__)


class ActivityService:

    @staticmethod
    def log(
        user_id: str,
        activity_type: ActivityType,
        resource_type: str,
        resource_id: Optional[str] = None,
        resource_title: Optional[str] = None,
        metadata: Optional[dict] = None,
        async_log: bool = True
    ) -> Optional[ActivityLog]:

        ip_address = None
        user_agent = None

        try:
            if request:
                ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
                if ip_address:
                    ip_address = ip_address.split(',')[0].strip()[:45]
                user_agent = request.headers.get('User-Agent', '')[:255]
        except RuntimeError:
            pass

        if async_log:
            app = current_app._get_current_object()
            Thread(
                target=ActivityService._log_async,
                args=(
                    app, user_id, activity_type, resource_type,
                    resource_id, resource_title, metadata,
                    ip_address, user_agent
                ),
                daemon=True
            ).start()
            return None
        else:
            return ActivityService._create_log(
                user_id, activity_type, resource_type,
                resource_id, resource_title, metadata,
                ip_address, user_agent
            )

    @staticmethod
    def _log_async(
        app,
        user_id: str,
        activity_type: ActivityType,
        resource_type: str,
        resource_id: Optional[str],
        resource_title: Optional[str],
        metadata: Optional[dict],
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> None:
        with app.app_context():
            try:
                ActivityService._create_log(
                    user_id, activity_type, resource_type,
                    resource_id, resource_title, metadata,
                    ip_address, user_agent
                )
            except Exception as e:
                logger.error(f"Async activity log failed: {e}")

    @staticmethod
    def _create_log(
        user_id: str,
        activity_type: ActivityType,
        resource_type: str,
        resource_id: Optional[str],
        resource_title: Optional[str],
        metadata: Optional[dict],
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> ActivityLog:
        activity = ActivityLog(
            user_id=user_id,
            activity_type=activity_type,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_title=resource_title,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent
        )

        db.session.add(activity)
        db.session.commit()

        return activity

    @staticmethod
    def get_user_activity(
        user_id: str,
        activity_type: Optional[ActivityType] = None,
        resource_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ActivityLog]:
        query = ActivityLog.query.filter_by(user_id=user_id)

        if activity_type:
            query = query.filter_by(activity_type=activity_type)

        if resource_type:
            query = query.filter_by(resource_type=resource_type)

        return query.order_by(
            ActivityLog.created_at.desc()
        ).offset(offset).limit(limit).all()

    @staticmethod
    def get_resource_activity(
        resource_type: str,
        resource_id: str,
        limit: int = 50
    ) -> List[ActivityLog]:
        return ActivityLog.query.filter_by(
            resource_type=resource_type,
            resource_id=resource_id
        ).order_by(ActivityLog.created_at.desc()).limit(limit).all()

    @staticmethod
    def cleanup_old_activity(days: int = 90) -> int:
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)

        try:
            result = ActivityLog.query.filter(
                ActivityLog.created_at < cutoff
            ).delete(synchronize_session=False)

            db.session.commit()
            logger.info(f"Cleaned up {result} old activity logs")
            return result

        except Exception as e:
            db.session.rollback()
            logger.error(f"Activity cleanup failed: {e}")
            return 0

    @staticmethod
    def get_activity_summary(user_id: str, days: int = 7) -> dict:
        from datetime import timedelta

        since = datetime.utcnow() - timedelta(days=days)

        activities = ActivityLog.query.filter(
            ActivityLog.user_id == user_id,
            ActivityLog.created_at >= since
        ).all()

        summary = {at.value: 0 for at in ActivityType}

        for activity in activities:
            summary[activity.activity_type.value] += 1

        return {
            "period_days": days,
            "total_activities": len(activities),
            "by_type": summary
        }
