import hikari
import lightbulb
import time

from datastore import Datastore
from objects.user import User
from typing import Optional

bot_instance = None
datastore = Datastore()

PERFORMANCE_LOGGING_CHANNEL = 1377200295389565020

async def initialize(bot: lightbulb.BotApp):
    global bot_instance
    bot_instance = bot


async def log_info_to_channel(channel_id: int, message: str) -> None:
    if bot_instance is not None:
        await bot_instance.rest.create_message(
                channel_id,
                message
            )


async def start_tracking_user(user_id: int, guild_id: int):
    # Original Java code saved the time in milliseconds, so
    # we need to convert the time into milliseconds as well
    # so that it doesn't mess up existing data
    seconds: int = int(time.time())

    async with datastore.get_tracking_queue_lock():
        tracking_queue = datastore.get_tracking_queue()
        tracking_queue[make_key(user_id, guild_id)] = User(user_id, guild_id, seconds)
    

async def if_member_has_permission(member: hikari.Member, permission: hikari.Permissions) -> bool:
    # author_member = await ctx.bot.rest.fetch_member(ctx.guild_id, ctx.author.id)
    member_permissions: hikari.Permissions = lightbulb.utils.permissions_for(member)

    # print(f"Permission for {member}: {member_permissions}")

    if permission in member_permissions:
        return True
    else:
        return False
    
async def if_member_is_owner(guild_id: int, user_id: int) -> bool:
    if bot_instance is not None:

        # Check the cache first before making an API call
        guild: Optional[hikari.Guild] = bot_instance.cache.get_guild(guild_id)

        if guild is None:
            try:
                guild = await bot_instance.rest.fetch_guild(guild_id)
                
                if guild.owner_id == user_id:
                    return True
                
                else:
                    return False
                
            except:
                return False
            
        return False

    else:
        print("Bot instance none")
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