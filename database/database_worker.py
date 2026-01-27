from typing import Optional, Tuple

from sqlalchemy import select, update, and_, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from data.enums import APIStatus
from database.database import get_db, Connection, Device


class DatabaseWorker:
    @staticmethod
    async def create_connection(user_id: int, name: str, max_devices: int = 3) -> Tuple[Optional[Connection], APIStatus]:
        async for db in get_db():
            try:
                existing_stmt = select(Connection).where(
                    Connection.user_id == user_id,
                    Connection.name == name
                )
                existing_result = await db.execute(existing_stmt)
                if existing_result.scalar_one_or_none():
                    return None, APIStatus.CONFLICT

                new_connection = Connection(
                    user_id=user_id,
                    name=name,
                    max_devices=max_devices
                )
                db.add(new_connection)
                await db.commit()
                await db.refresh(new_connection)
                return new_connection, APIStatus.SUCCESS
            except SQLAlchemyError as sqlex:
                await db.rollback()
                raise sqlex

    @staticmethod
    async def remove_connection(user_id: int, name: str) -> APIStatus:
        async for db in get_db():
            try:
                stmt = select(Connection).where(
                    Connection.user_id == user_id,
                    Connection.name == name
                )
                result = await db.execute(stmt)
                connection = result.scalars().first()
                if connection is None:
                    return APIStatus.NOT_FOUND
                await db.delete(connection)
                await db.commit()
                return APIStatus.SUCCESS
            except SQLAlchemyError as sqlex:
                await db.rollback()
                raise sqlex

    @staticmethod
    async def get_user_connections(user_id: int):
        async for db in get_db():
            try:
                stmt = select(Connection).where(
                    Connection.user_id == user_id
                ).options(
                    selectinload(Connection.devices)
                )
                result = await db.execute(stmt)
                connections = result.scalars().all()
                return connections
            except SQLAlchemyError as sqlex:
                await db.rollback()
                raise sqlex

    @staticmethod
    async def add_device(connection_id: str, device_info: dict) -> Tuple[Optional[Device], APIStatus]:
        async for db in get_db():
            try:
                stmt = select(Connection).where(
                    Connection.connection_id == connection_id,
                    Connection.is_active == True
                )
                result = await db.execute(stmt)
                connection = result.scalar_one_or_none()

                if not connection:
                    return None, APIStatus.NOT_FOUND

                active_count_stmt = select(func.count(Device.id)).where(
                    Device.connection_id == connection.id,
                    Device.is_active == True
                )
                active_count_result = await db.execute(active_count_stmt)
                active_count = active_count_result.scalar() or 0

                if active_count >= connection.max_devices:
                    return None, APIStatus.LIMIT_EXCEEDED

                device_uid = device_info['device_uid']

                device_stmt = select(Device).where(
                    Device.connection_id == connection.id,
                    Device.device_uid == device_uid
                )
                device_result = await db.execute(device_stmt)
                existing_device = device_result.scalar_one_or_none()

                if existing_device:
                    existing_device.name = device_info.get('name')
                    existing_device.platform = device_info.get('platform')
                    existing_device.model = device_info.get('model')
                    existing_device.os_version = device_info.get('os_version')
                    existing_device.is_active = True
                    existing_device.last_seen = func.now()

                    await db.commit()
                    await db.refresh(existing_device)
                    return existing_device, APIStatus.SUCCESS

                else:
                    device = Device(
                        connection_id=connection.id,
                        **device_info
                    )
                    db.add(device)
                    await db.commit()
                    await db.refresh(device)
                    return device, APIStatus.SUCCESS

            except SQLAlchemyError as sqlex:
                await db.rollback()
                raise sqlex

    @staticmethod
    async def disconnect_device(device_uid: str, connection_id: str = None) -> APIStatus:
        async for db in get_db():
            try:
                if not connection_id:
                    return APIStatus.UNAUTHORIZED

                stmt = select(Device).join(Connection).where(
                    Device.device_uid == device_uid,
                    Device.is_active == True,
                    Connection.connection_id == connection_id,
                    Connection.is_active == True
                )
                result = await db.execute(stmt)
                device = result.scalar_one_or_none()

                if not device:
                    return APIStatus.NOT_FOUND

                device.is_active = False
                device.last_seen = func.now()
                await db.commit()
                return APIStatus.SUCCESS
            except SQLAlchemyError as sqlex:
                await db.rollback()
                raise sqlex

    @staticmethod
    async def get_device_active_status(connection_id: str, device_uid: str) -> Tuple[bool, APIStatus]:
        async for db in get_db():
            stmt = select(Device).join(Connection).where(
                Connection.connection_id == connection_id,
                Device.device_uid == device_uid,
            ).options(
                selectinload(Device.connection)
            )
            result = await db.execute(stmt)
            device = result.scalar_one_or_none()
            if not device: return True, APIStatus.NOT_FOUND
            return device.is_active, APIStatus.SUCCESS

    @staticmethod
    async def get_active_devices(connection_id: str) -> Tuple[Optional[list[Device]], APIStatus]:
        async for db in get_db():
            if not connection_id:
                return None, APIStatus.UNAUTHORIZED,
            try:
                stmt = select(Device).join(Connection).where(
                    Connection.connection_id == connection_id,
                    Device.is_active == True,
                    Connection.is_active == True
                ).options(
                    selectinload(Device.connection)
                )
                result = await db.execute(stmt)
                devices = result.scalars().all()
                return devices, APIStatus.SUCCESS
            except SQLAlchemyError as sqlex:
                await db.rollback()
                raise sqlex

    @staticmethod
    async def get_connection_by_id(connection_id: str) -> Optional[Connection]:
        async for db in get_db():
            try:
                stmt = select(Connection).where(
                    Connection.connection_id == connection_id
                ).options(
                    selectinload(Connection.devices)
                )
                result = await db.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError as sqlex:
                await db.rollback()
                raise sqlex


