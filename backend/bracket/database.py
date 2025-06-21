import os
import sys
from typing import Any

import sqlalchemy
from databases import Database
from heliclockter import datetime_utc

from bracket.config import config


def datetime_decoder(value: str) -> datetime_utc:
    value = value.split(".")[0].replace("+00", "+00:00")
    return datetime_utc.fromisoformat(value)


async def asyncpg_init(connection: Any) -> None:
    for timestamp_type in ("timestamp", "timestamptz"):
        await connection.set_type_codec(
            timestamp_type,
            encoder=datetime_utc.isoformat,
            decoder=datetime_decoder,
            schema="pg_catalog",
        )


def get_database_url():
    """Get database URL based on deployment mode"""
    if os.getenv('BRACKET_STANDALONE', '').lower() == 'true':
        # Standalone mode: Use SQLite
        if hasattr(sys, '_MEIPASS'):
            # Running as PyInstaller bundle
            db_path = os.path.join(os.path.dirname(sys.executable), 'bracket.db')
        else:
            # Running as script in development
            db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'bracket.db')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        return f"sqlite+aiosqlite:///{db_path}"
    else:
        # Normal mode: Use PostgreSQL (existing behavior)
        return str(config.pg_dsn)


def create_database_instance():
    """Create database instance based on deployment mode"""
    db_url = get_database_url()
    
    if db_url.startswith("sqlite"):
        # SQLite mode: No special initialization needed
        return Database(db_url)
    else:
        # PostgreSQL mode: Use existing asyncpg initialization
        return Database(db_url, init=asyncpg_init)


def create_sqlalchemy_engine():
    """Create SQLAlchemy engine based on deployment mode"""
    db_url = get_database_url()
    
    if db_url.startswith("sqlite"):
        # SQLite mode: Use synchronous SQLite URL
        sync_url = db_url.replace("sqlite+aiosqlite://", "sqlite:///")
        return sqlalchemy.create_engine(sync_url)
    else:
        # PostgreSQL mode: Use existing configuration
        return sqlalchemy.create_engine(str(config.pg_dsn))


database = create_database_instance()

engine = create_sqlalchemy_engine()