from sqlalchemy import select, update, and_, func
from sqlalchemy.exc import SQLAlchemyError

from database.database import get_db, Connection, Device


class DatabaseWorker:
    @staticmethod
    async def create_connection(user_id: int, name: str, max_devices: int = 3):
        async for db in get_db():
            try:
                new_connection = Connection(
                    user_id=user_id,
                    name=name,
                    max_devices=max_devices
                )
                db.add(new_connection)
                await db.commit()
                await db.refresh(new_connection)
                return new_connection
            except SQLAlchemyError as sqlex:
                await db.rollback()
                raise sqlex

    @staticmethod
    async def add_device(connection_id: str, device_info: dict):
        async for db in get_db():
            try:
                stmt = select(Connection).where(
                    Connection.connection_id == connection_id,
                    Connection.is_active == True
                )
                result = await db.execute(stmt)
                connection = result.scalar_one_or_none()

                if not connection:
                    return None, "Connection not found"

                device_count = len([device for device in connection.devices if device.is_active])
                if device_count >= connection.max_devices:
                    return None, "Device limit reached"

                existing_device = next(
                    (device for device in connection.devices if device.device_uid == device_info['device_uid']),None
                )

                if existing_device:
                    existing_device.name = device_info.get('name')
                    existing_device.platform = device_info.get('platform')
                    existing_device.model = device_info.get('model')
                    existing_device.os_version = device_info.get('os_version')
                    existing_device.is_active = True
                    device = existing_device
                else:
                    device = Device(
                        connection_id=connection.id,
                        **device_info
                    )
                    db.add(device)
                    await db.commit()
                    await db.refresh(device)
                    return device, "Success"
            except SQLAlchemyError as sqlex:
                await db.rollback()
                raise sqlex

    @staticmethod
    async def disconnect_device(device_uid: str, connection_id: str = None):
        async for db in get_db():
            try:
                conditions = [Device.device_uid == device_uid, Device.is_active == True]
                if connection_id:
                    stmt = select(Connection.id).where(Connection.connection_id == connection_id)
                    result = await db.execute(stmt)
                    conn_id = result.scalar_one_or_none()
                    if conn_id:
                        conditions.append(Device.connection_id == conn_id)

                stmt = update(Device).where(and_(*conditions)).values(
                    is_active=False,
                    last_seen=func.now()
                )
                await db.execute(stmt)
                await db.commit()
            except SQLAlchemyError as sqlex:
                await db.rollback()
                raise sqlex

    @staticmethod
    async def get_active_devices(connection_id: str):
        async for db in get_db():
            try:
                stmt = select(Device).join(Connection).where(
                    Connection.connection_id == connection_id,
                    Device.is_active == True
                )
                result = await db.execute(stmt)
                return result.scalars().all()
            except SQLAlchemyError as sqlex:
                await db.rollback()
                raise sqlex

    @staticmethod
    async def get_connection_stats(connection_id: str):
        async for db in get_db():
            try:
                stmt = select(Connection).where(Connection.connection_id == connection_id)
                result = await db.execute(stmt)
                connection = result.scalar_one_or_none()

                if not connection:
                    return None

                active_devices = [d for d in connection.devices if d.is_active]

                return {
                    'connection_id': connection.connection_id,
                    'name': connection.name,
                    'max_devices': connection.max_devices,
                    'active_devices': len(active_devices),
                    'devices': [
                        {
                            'id': device.id,
                            'name': device.name,
                            'platform': device.platform,
                            'model': device.model,
                            'last_seen': device.last_seen
                        }
                        for device in active_devices
                    ]
                }
            except SQLAlchemyError as sqlex:
                await db.rollback()
                raise sqlex


