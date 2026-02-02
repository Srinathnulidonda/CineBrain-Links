# server/app/routes/sharing.py

import logging
from datetime import datetime

from flask import Blueprint, request, current_app, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models.link import Link
from app.models.shared_link import SharedLink
from app.models.activity_log import ActivityType
from app.services.activity_service import ActivityService
from app.utils.base_url import get_public_base_url

sharing_bp = Blueprint("sharing", __name__)
logger = logging.getLogger(__name__)


def api_response():
    return current_app.api_response


@sharing_bp.route("/links/<link_id>", methods=["POST"])
@jwt_required()
def create_share(link_id: str):
    user_id = get_jwt_identity()
    base_url = get_public_base_url()

    link = Link.query.filter_by(id=link_id, user_id=user_id, is_deleted=False).first()

    if not link:
        return api_response().error("Link not found", 404, "NOT_FOUND")

    data = request.get_json() or {}

    password = data.get("password")
    expires_at_str = data.get("expires_at")
    max_views = data.get("max_views", type=int)

    expires_at = None
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
            if expires_at <= datetime.utcnow():
                return api_response().error("Expiration must be in the future", 400)
        except (ValueError, TypeError):
            return api_response().error("Invalid expiration date format", 400)

    try:
        share = SharedLink(
            link_id=link_id,
            password=password,
            expires_at=expires_at,
            max_views=max_views
        )

        db.session.add(share)
        db.session.commit()

        ActivityService.log(
            user_id=user_id,
            activity_type=ActivityType.LINK_SHARED,
            resource_type="link",
            resource_id=link.id,
            resource_title=link.title or link.original_url[:50],
            metadata={"share_id": share.id}
        )

        logger.info(f"Share created: {share.id} for link {link_id}")

        return api_response().success(
            data={"share": share.to_dict(base_url=base_url)},
            message="Share link created",
            status=201
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Share creation failed: {e}")
        return api_response().error("Failed to create share", 500)


@sharing_bp.route("/links/<link_id>", methods=["GET"])
@jwt_required()
def get_link_shares(link_id: str):
    user_id = get_jwt_identity()
    base_url = get_public_base_url()

    link = Link.query.filter_by(id=link_id, user_id=user_id, is_deleted=False).first()

    if not link:
        return api_response().error("Link not found", 404, "NOT_FOUND")

    shares = SharedLink.query.filter_by(link_id=link_id).order_by(SharedLink.created_at.desc()).all()

    return api_response().success(data={
        "shares": [s.to_dict(base_url=base_url) for s in shares]
    })


@sharing_bp.route("/<share_id>", methods=["DELETE"])
@jwt_required()
def revoke_share(share_id: str):
    user_id = get_jwt_identity()

    share = SharedLink.query.join(Link).filter(
        SharedLink.id == share_id,
        Link.user_id == user_id
    ).first()

    if not share:
        return api_response().error("Share not found", 404, "NOT_FOUND")

    try:
        share.revoke()
        db.session.commit()

        logger.info(f"Share revoked: {share_id}")

        return api_response().success(message="Share link revoked")

    except Exception as e:
        db.session.rollback()
        logger.error(f"Share revocation failed: {e}")
        return api_response().error("Failed to revoke share", 500)


@sharing_bp.route("/s/<share_token>", methods=["GET"])
def access_shared_link(share_token: str):
    share = SharedLink.query.filter_by(share_token=share_token).first()

    if not share:
        return jsonify({"success": False, "error": {"message": "Share link not found"}}), 404

    if not share.is_accessible:
        if share.is_expired:
            return jsonify({"success": False, "error": {"message": "This share link has expired"}}), 410
        return jsonify({"success": False, "error": {"message": "This share link is no longer active"}}), 410

    if share.has_password:
        return jsonify({
            "success": True,
            "data": {
                "requires_password": True,
                "share_token": share_token
            }
        }), 200

    link = share.link

    share.record_view()
    db.session.commit()

    base_url = get_public_base_url()

    return jsonify({
        "success": True,
        "data": {
            "requires_password": False,
            "link": {
                "original_url": link.original_url,
                "title": link.title,
                "notes": link.notes,
                "short_url": f"{base_url}/{link.slug}" if link.slug else None,
                "created_at": link.created_at.isoformat()
            }
        }
    }), 200


@sharing_bp.route("/s/<share_token>/verify", methods=["POST"])
def verify_share_password(share_token: str):
    share = SharedLink.query.filter_by(share_token=share_token).first()

    if not share or not share.is_accessible:
        return jsonify({"success": False, "error": {"message": "Share link not accessible"}}), 404

    data = request.get_json() or {}
    password = data.get("password", "")

    if not share.check_password(password):
        return jsonify({"success": False, "error": {"message": "Incorrect password"}}), 401

    link = share.link

    share.record_view()
    db.session.commit()

    base_url = get_public_base_url()

    return jsonify({
        "success": True,
        "data": {
            "link": {
                "original_url": link.original_url,
                "title": link.title,
                "notes": link.notes,
                "short_url": f"{base_url}/{link.slug}" if link.slug else None,
                "created_at": link.created_at.isoformat()
            }
        }
    }), 200