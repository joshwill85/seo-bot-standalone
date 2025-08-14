"""Database connection and session management."""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import Base


# Create engine with production settings
engine = create_engine(
    settings.database_url,
    echo=settings.log_level == "DEBUG",
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=20,
    max_overflow=0,
    connect_args={
        "connect_timeout": 30,
        "application_name": "seo_bot"
    } if "postgresql" in settings.database_url else {}
)


# Enable foreign key constraints for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite."""
    if 'sqlite' in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables."""
    Base.metadata.drop_all(bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get a database session with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class DatabaseManager:
    """Database operations manager."""
    
    def __init__(self, session: Session = None):
        self.session = session
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    def get_or_create(self, model_class, **kwargs):
        """Get an existing instance or create a new one."""
        instance = self.session.query(model_class).filter_by(**kwargs).first()
        if instance:
            return instance, False
        else:
            instance = model_class(**kwargs)
            self.session.add(instance)
            return instance, True
    
    def bulk_create(self, instances):
        """Create multiple instances efficiently."""
        self.session.bulk_save_objects(instances)
        self.session.commit()
    
    def bulk_update(self, instances):
        """Update multiple instances efficiently."""
        for instance in instances:
            self.session.merge(instance)
        self.session.commit()
    
    def create_all(self):
        """Create all tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_all(self):
        """Drop all tables."""
        Base.metadata.drop_all(bind=self.engine)
    
    def reset_database(self):
        """Reset database by dropping and recreating all tables."""
        self.drop_all()
        self.create_all()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Context manager for database sessions."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            with self.session_scope() as session:
                session.execute("SELECT 1")
                return True
        except Exception:
            return False


# Global database manager instance
db_manager = DatabaseManager()


# Initialize database on import
def init_db():
    """Initialize the database with tables."""
    create_tables()


if __name__ == "__main__":
    # Create tables when run as script
    init_db()
    print("Database initialized successfully!")