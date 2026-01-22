import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict

import redis.asyncio as redis

from data.schemas import TaskStatus


class TaskManager:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)

    async def create_task(self, user_id: int) -> str:
        task_id = str(uuid.uuid4())

        task_data = {
            'task_id': task_id,
            'user_id': user_id,
            'status': TaskStatus.PENDING,
            'message': 'Task created',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'progress': 0
        }

        await self.redis.setex(
            f"task:{task_id}",
            3600,
            json.dumps(task_data)
        )

        return task_id

    async def update_task(self, task_id: str, status: Optional[TaskStatus] = None, message: Optional[str] = None,
                          progress: Optional[int] = None, result: Optional[Dict] = None) -> bool:
        if task_id not in self.redis:
            return False

        task = self.redis.getex(f"task:{task_id}")

        if status:
            task.status = status
        if message:
            task.message = message
        if progress is not None:
            task.progress = progress
        if result:
            task.result = result

        task.updated_at = datetime.now().isoformat()
        await self.redis.set(f"task:{task_id}", json.dumps(task))
        return True

    async def get_task(self, task_id: str) -> Optional[Dict]:
        return await self.redis.get(f"task:{task_id}")

    async def cleanup_old_tasks(self, hours_old: int = 24):
        cutoff = datetime.now().timestamp() - (hours_old * 3600)

        tasks_to_remove = []
        async for task_id in self.redis.scan_iter("task:*"):
            task = await self.redis.get(f"task:{task_id}")
            created_at = datetime.fromisoformat(task['created_at']).timestamp()
            if created_at < cutoff:
                tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            await self.redis.delete(f"task:{task_id}")

task_manager = TaskManager()