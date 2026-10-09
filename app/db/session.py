from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# 1. Create the SQLAlchemy Engine
# connect_args={"check_same_thread": False} is needed ONLY for SQLite.
# Remove it if you switch to PostgreSQL/MySQL.
# engine = create_async_engine(
#     settings.SQLALCHEMY_DATABASE_URI,
#     echo=False,
#     # connect_args={"check_same_thread": False}
#     # if "sqlite" in settings.SQLALCHEMY_DATABASE_URI
#     # else {},
# )
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=False,
    pool_size=20,          
    max_overflow=20,      
    pool_pre_ping=True,    # detect dead connections
    pool_recycle=1800,     # recycle after 30 min
)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()
