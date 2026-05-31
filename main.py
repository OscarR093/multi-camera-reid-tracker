import os
import sys
import logging
import threading
import time
import signal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


def resolve_db_path() -> str:
    from core.config import settings
    db_path = settings.sqlite_db_path
    if not os.path.isabs(db_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    settings.sqlite_db_path = db_path
    return db_path


def main():
    import uvicorn
    from core.pipeline import Pipeline, set_pipeline
    from api.websocket import ws_manager
    from core.config import settings

    resolve_db_path()

    pipeline = Pipeline()
    set_pipeline(pipeline)

    pipeline.set_callback(ws_manager.pipeline_callback)

    pipeline_thread = threading.Thread(
        target=pipeline.start, daemon=True, name="pipeline"
    )
    pipeline_thread.start()

    time.sleep(2)

    if pipeline.identity_manager and pipeline.identity_manager.sqlite:
        try:
            from api.auth import get_password_hash
            sqlite = pipeline.identity_manager.sqlite
            existing = sqlite.get_user("admin")
            if not existing:
                hashed = get_password_hash("admin123")
                sqlite.add_user("admin", hashed, "admin")
                logger.info("Default admin user created (admin / admin123)")
        except Exception as e:
            logger.warning(f"Could not create default admin: {e}")

    config = uvicorn.Config(
        "api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )
    server = uvicorn.Server(config)

    def shutdown():
        logger.info("Shutting down...")
        pipeline.stop()
        server.should_exit = True

    signal.signal(signal.SIGINT, lambda s, f: shutdown())
    signal.signal(signal.SIGTERM, lambda s, f: shutdown())

    try:
        server.run()
    except KeyboardInterrupt:
        pass
    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()
