import asyncio
import hikari
import lightbulb
import time

from typing import Dict, List, Optional, Tuple
from handlers.database_handler import DatabaseHandler
from objects.user import User
from cachetools import TTLCache

tracking_queue: Dict[str, User] = {}
tracking_queue_lock = asyncio.Lock()

db_handler: Optional[DatabaseHandler] = None
bot_instance = None

# Dict[Tuple[int, int], int] -> guildID, userID, position
user_leaderboard_position_cache: TTLCache[tuple[int, int], int] = TTLCache(maxsize=10_000, ttl=60 * 60) # type: ignore

PERFORMANCE_LOGGING_CHANNEL = 1377200295389565020

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

async def log_info_to_channel(channel_id: int, message: str) -> None:
    if bot_instance is not None:
        await bot_instance.rest.create_message(
                channel_id,
                message
            )
    
def get_tracking_queue() -> Dict[str, User]:
    return tracking_queue

def get_tracking_queue_lock() -> asyncio.Lock:
    return tracking_queue_lock


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

    if time_difference <= 0:
        return

    # Save the time, and then update the time to current so that
    # the difference calculation doesn't break
    if db_handler is not None:

        start = time.perf_counter()
        await db_handler.insert(user_id, time_difference, guild_id)
        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        await log_info_to_channel(1377205400981602334,f"`insert` completed in {elapsed_ms:.3f}ms")

        user_from_tracking_queue.set_joined_time(int(time.time()))


async def save_tracking_stats_bulk() -> None:
    user_ids: List[int] = []
    time_differences: List[int] = []
    server_ids: List[int] = []

    async with get_tracking_queue_lock():
        for user in get_tracking_queue().values():
            current_user: User = user

            time_difference: int = int(time.time()) - current_user.get_joined_time()

            if(time_difference <= 0):
                continue

            time_differences.append(time_difference)
            user_ids.append(current_user.get_user_id())
            server_ids.append(current_user.get_guild_id())

            # Make sure to update the time delta once saving
            current_user.set_joined_time(int(time.time()))
            
            # print(f"Saving stats for {current_user.get_user_id()} in {current_user.get_guild_id()} with time {time_difference}")

        if db_handler is not None:
            start = time.perf_counter()
            await db_handler.bulk_insert(user_ids, time_differences, server_ids)
            end = time.perf_counter()
            elapsed_ms = (end - start) * 1000
            await log_info_to_channel(PERFORMANCE_LOGGING_CHANNEL,f"`bulk_insert` completed in {elapsed_ms:.3f}ms")


async def get_user_time_and_leaderboard_position(user_id: int, guild_id: int) -> Tuple[Optional[int], Optional[int]]:
    """
    Returns [time, position]
    """
    if db_handler is not None:

        start = time.perf_counter()

        user_time = 0
        position = 0

        # If the position is in cache, we fetch the position in cache.
        # If it is not in the cache, we use the more expensive call the obtain the position
        if (guild_id, user_id) in user_leaderboard_position_cache:
            user_time = await db_handler.get_user_time(user_id, guild_id)
            position = user_leaderboard_position_cache[(guild_id, user_id)]
        else:
            user_time, position = await db_handler.get_user_time_and_position(user_id, guild_id)
            if position is not None:
                user_leaderboard_position_cache[(guild_id, user_id)] = position

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        await log_info_to_channel(PERFORMANCE_LOGGING_CHANNEL,f"`get_user_time_and_position` completed in {elapsed_ms:.3f}ms")

        return (user_time, position)
    else:
        return None, None


async def get_leaderboard_members_and_time(guild_id: int) -> tuple[Optional[List[int]], Optional[List[int]]]:
    if db_handler is not None:

        start = time.perf_counter()
        result = await db_handler.get_leaderboard_members_and_time_from_database(guild_id)
        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        await log_info_to_channel(PERFORMANCE_LOGGING_CHANNEL,f"`get_leaderboard_members_and_time_from_database` completed in {elapsed_ms:.3f}ms")

        return result
    else:
        return None, None
    

async def reset_all(guild_id: int) -> None:
    if db_handler is not None:

        start = time.perf_counter()
        await db_handler.reset_all_database(guild_id)
        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        await log_info_to_channel(PERFORMANCE_LOGGING_CHANNEL,f"`reset_all_database` completed in {elapsed_ms:.3f}ms")

async def reset_user(guild_id: int, user_id: int) -> None:
    if db_handler is not None:

        start = time.perf_counter()
        await db_handler.reset_specific_user_database(guild_id, user_id)
        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        await log_info_to_channel(PERFORMANCE_LOGGING_CHANNEL,f"`reset_specific_user_database` completed in {elapsed_ms:.3f}ms")

async def if_member_has_permission(member: hikari.Member, permission: hikari.Permissions) -> bool:
    # author_member = await ctx.bot.rest.fetch_member(ctx.guild_id, ctx.author.id)
    member_permissions: hikari.Permissions = lightbulb.utils.permissions_for(member)

    # print(f"Permission for {member}: {member_permissions}")

    if permission in member_permissions:
        return True
    else:
        return False


@staticmethod
def seconds_to_timestamp(seconds: int) -> str:
    # Implement your milliseconds to timestamp conversion
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:,}h {minutes}m {seconds}s"
    # return f"{hours:,}h {minutes}m"

@staticmethod
def make_key(user_id: int, guild_id: int) -> str:
    key: str = f"{user_id}-{guild_id}"
    return key