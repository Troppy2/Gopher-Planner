import os

from flask import Flask, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException
from flask_cors import CORS

from app.api.v1.auth import auth_bp
from app.api.v1.courses import courses_bp
from app.api.v1.profile import profile_bp
from app.api.v1.summary import summary_bp
from app.api.v1.coursework import coursework_bp
from app.api.v1.plan import plan_bp
from app.api.v1.transcripts import transcripts_bp
from app.api.v1.liberal_ed import liberal_ed_bp
from app.core.config import Settings
from app.extensions import db, migrate
from app.extensions.rate_limit import limiter
from app import models


def create_app() -> Flask:
    app = Flask(__name__)

    settings = Settings.from_env()
    app.config["SETTINGS"] = settings

    app.config["SQLALCHEMY_DATABASE_URI"] = settings.database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
    app.config["RATELIMIT_ENABLED"] = os.getenv("RATELIMIT_ENABLED", "true").strip().lower() != "false"
    app.config["RATELIMIT_STORAGE_URI"] = os.getenv("RATELIMIT_STORAGE_URI", "memory://").strip() or "memory://"

    # Behind a hosting proxy, trust that many X-Forwarded-For/-Proto hops so rate limits
    # see the real client address and secure cookies see HTTPS. Never trust headers by default.
    proxy_hops = int(os.getenv("TRUSTED_PROXY_HOPS", "0") or 0)
    if proxy_hops > 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_hops, x_proto=proxy_hops)

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    CORS(
        app,
        resources={r"/api/*": {"origins": settings.frontend_origin}},
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=True,
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(summary_bp)
    app.register_blueprint(coursework_bp)
    app.register_blueprint(plan_bp)
    app.register_blueprint(transcripts_bp)
    app.register_blueprint(liberal_ed_bp)

    @app.get("/health")
    def health():
        """Liveness: the process is serving requests."""
        return {"status": "ok"}

    @app.get("/ready")
    def ready():
        """Readiness: the database answers. Use this for deploy health checks."""
        try:
            db.session.execute(text("SELECT 1"))
            return {"status": "ok"}
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Readiness check failed")
            return {"status": "unavailable"}, 503

    @app.errorhandler(HTTPException)
    def http_error(error):
        response = error.get_response()
        response.data = jsonify({
            "error": error.description,
            "code": "too_large" if error.code == 413 else error.name.lower().replace(" ", "_"),
        }).data
        response.content_type = "application/json"
        return response

    @app.errorhandler(500)
    def internal_error(error):
        # Flask logs the original stack before invoking this handler.
        db.session.rollback()
        return {"error": "Internal server error", "code": "internal_error"}, 500

    return app
