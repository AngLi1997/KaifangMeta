from datetime import datetime

from pydantic import BaseModel

from app.core.crud import CRUDBase
from app.domains.users.models import User


class UserController(CRUDBase[User, BaseModel, BaseModel]):
    def __init__(self):
        super().__init__(model=User)

    async def update_last_login(self, id: int) -> None:
        user = await self.model.get(id=id)
        user.last_login = datetime.now()
        await user.save()


user_controller = UserController()
