from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Determine DB dialect
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine_kwargs = {}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # Production PostgreSQL connection pooling parameters
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    })

engine = create_engine(
    settings.DATABASE_URL,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_and_migrate_db():
    """Initializes tables and safely adds new columns to existing SQLite databases."""
    Base.metadata.create_all(bind=engine)
    if is_sqlite:
        try:
            with engine.connect() as conn:
                # Check user_preferences columns
                res = conn.execute(text("PRAGMA table_info(user_preferences)")).fetchall()
                cols = [row[1] for row in res]
                if "session_id" not in cols:
                    conn.execute(text("ALTER TABLE user_preferences ADD COLUMN session_id VARCHAR(100)"))
                if "persona" not in cols:
                    conn.execute(text("ALTER TABLE user_preferences ADD COLUMN persona VARCHAR(50) DEFAULT 'general'"))
                if "preferred_activities" not in cols:
                    conn.execute(text("ALTER TABLE user_preferences ADD COLUMN preferred_activities JSON"))
                if "alert_notifications_enabled" not in cols:
                    conn.execute(text("ALTER TABLE user_preferences ADD COLUMN alert_notifications_enabled BOOLEAN DEFAULT 1"))
                if "updated_at" not in cols:
                    conn.execute(text("ALTER TABLE user_preferences ADD COLUMN updated_at DATETIME"))
                conn.commit()
        except Exception as ex:
            logger.warning(f"SQLite auto-migration warning: {ex}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
