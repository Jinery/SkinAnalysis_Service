import uuid

from sqlalchemy import Column, Integer, BigInteger, ForeignKey, String, Boolean, DateTime, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from files.file_manager import file_manager

DATABASE_URL = f"sqlite+aiosqlite:///{file_manager.get_database_path()}"
Base = declarative_base()

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    connections = relationship("Connection", back_populates="user")


class Connection(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    connection_id = Column(String(36), nullable=False, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, ForeignKey('users.id'), index=True)
    name = Column(String(100), nullable=False)
    max_devices = Column(Integer, nullable=False, default=3)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User", back_populates="connections")
    devices = relationship("Device", back_populates="connection", cascade="all, delete-orphan")


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    connection_id = Column(Integer, ForeignKey('connections.id'), index=True)
    device_uid = Column(String(255), nullable=False, index=True)
    name = Column(String(100))
    platform = Column(String(50))
    model = Column(String(100))
    os_version = Column(String(50))
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, server_default=func.now())

    connection = relationship("Connection", back_populates="devices")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()