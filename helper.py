from typing import Dict, List, Optional
from lightbulb import Plugin
import lightbulb
from handlers.database_handler import DatabaseHandler
from objects.user import User

import time

from objects.user import User

tracking_queue: Dict[str, User] = {}
db_handler: Optional[DatabaseHandler] = None
bot_instance = None

async def initialize(bot: lightbulb.BotApp):

    global bot_instance
    bot_instance = bot

    global db_handler
    db_handler = DatabaseHandler()
    await db_handler.init()

async def uninitialize():
    global db_handler
    if db_handler is not None:
        await db_handler.uninitialize()

async def log_info_to_channel(client: Plugin, channel_id: int, message: str) -> None:
    await client.app.rest.create_message(
            channel_id,
            message
        )
    
def get_tracking_queue() -> Dict[str, User]:
    return tracking_queue

async def start_tracking_user(user_id: int, guild_id: int):
    # Original Java code saved the time in milliseconds, so
    # we need to convert the time into milliseconds as well
    # so that it doesn't mess up existing data
    seconds: int = int(time.time())

    tracking_queue[make_key(user_id, guild_id)] = User(user_id, guild_id, seconds)


async def save_tracking_stats_single(user_id1: int, guild_id1: int) -> None:
    dict_key: str = make_key(user_id1, guild_id1)
    user_from_tracking_queue: User = tracking_queue[dict_key]

    user_id: int = user_from_tracking_queue.get_user_id()
    time_difference: int = int(time.time() - user_from_tracking_queue.get_joined_time())
    guild_id: int = user_from_tracking_queue.get_guild_id()

    # Save the time, and then update the time to current so that
    # the difference calculation doesn't break
    if db_handler is not None:
        await db_handler.insert(user_id, time_difference, guild_id)
        user_from_tracking_queue.set_joined_time(int(time.time()))


async def save_tracking_stats_bulk() -> None:
    user_ids: List[int] = []
    time_differences: List[int] = []
    server_ids: List[int] = []

    for user in tracking_queue.values():
        current_user: User = user

        time_difference: int = int(time.time()) - current_user.get_joined_time()

        time_differences.append(time_difference)
        user_ids.append(current_user.get_guild_id())
        server_ids.append(current_user.get_guild_id())

        # Make sure to update the time delta once saving
        current_user.set_joined_time(int(time.time()))

    if db_handler is not None:
        await db_handler.bulk_insert(user_ids, time_differences, server_ids)


async def get_user_time_and_leaderboard_position(user_id: int, guild_id: int) -> tuple[Optional[int], Optional[int]]:
    if db_handler is not None:
        return await db_handler.get_user_time_and_position(user_id, guild_id)
    else:
        return None, None


async def get_leaderboard_members_and_time(guild_id: int) -> tuple[Optional[list[int]], Optional[list[int]]]:
    if db_handler is not None:
        return await db_handler.get_leaderboard_members_and_time_from_database(guild_id)
    else:
        return None, None

@staticmethod
def seconds_to_timestamp(seconds: int) -> str:
    # Implement your milliseconds to timestamp conversion
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:,}h {minutes}m {seconds}s"

@staticmethod
def make_key(user_id: int, guild_id: int) -> str:
    key: str = f"{user_id}-{guild_id}"
    return key