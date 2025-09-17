from aiogram.filters import BaseFilter
from aiogram.types import Message

from db.psql.models.models import User


class NewUser(BaseFilter):
    async def __call__(self, msg: Message) -> bool:
        """
            Check user in db
        :param msg: Message
        :return: bool
        """
        user_id = await User.check(tg_id=msg.from_user.id)
        return not bool(user_id)
