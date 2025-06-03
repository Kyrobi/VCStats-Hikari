import config
import hikari
import lightbulb
import asyncio

from helper import initialize, make_key, start_tracking_user
from datastore import Datastore
from typing import Dict, List, Mapping, Optional
from objects.user import User
from logging_stuff import fetch_stats


# Set the cache we want to enable
cache_options = (
    hikari.api.CacheComponents.VOICE_STATES |# Only want the cache for voice states
    hikari.api.CacheComponents.ROLES | # Required to do permission checks
    hikari.api.CacheComponents.MEMBERS # Required to retreive member information given just user_id
)

# Initialize the bot - NEW SYNTAX for Lightbulb 2.x
bot = lightbulb.BotApp(
    token=config.BOT_TOKEN,
    # intents=hikari.Intents.ALL
    cache_settings=hikari.impl.CacheSettings(components=cache_options)
)

datastore = Datastore()

# Function when the bot is starting up
@bot.listen(hikari.StartingEvent)
async def on_starting(event: hikari.StartingEvent) -> None:

    # Start the datastore first
    await datastore.initialize()

    # Load Eventhandlers
    bot.load_extensions("handlers.event_handler") # Handles the join and leave events

    # Load Commands
    bot.load_extensions("commands.command_stats")
    bot.load_extensions("commands.command_help")
    bot.load_extensions("commands.command_donate")
    bot.load_extensions("commands.command_leaderboard")
    bot.load_extensions("commands.command_reset_guild_stats")
    bot.load_extensions("commands.command_reset_user_stats")
    # bot.load_extensions("commands.command_test")
    bot.load_extensions("logging_stuff")

# After bot has fully started
@bot.listen(hikari.StartedEvent)
async def on_started(event: hikari.StartedEvent) -> None:

    await initialize(bot)

    # await user_tracker.add_all_users_in_voice_channels(bot)
    print(f"Initialized tracking for {len(datastore.get_tracking_queue())} users already in voice channels")

    asyncio.create_task(queue_updater(60 * 60 * 1)) # Runs every 1 hour
    asyncio.create_task(auto_save_all(60 * 5)) # Runs every 5 minutes
    asyncio.create_task(get_stats(60 * 60 * 24)) # Runs every 24 hours


# Function when the bot is shutting down
@bot.listen(hikari.StoppingEvent)
async def on_stopping(event: hikari.StoppingEvent) -> None:
    if datastore:
        await datastore.save_all(None)
    else:
        print("Datastore was not available...")

    print("Bot shutting down")

    await datastore.uninitialize()


# Adds all the existing users in the voice channel into the queue if the bot were to restart
@bot.listen(hikari.GuildAvailableEvent)
async def on_guild_available(event: hikari.GuildAvailableEvent) -> None:

    # Actually returns a mapping of user IDs to their voice channels.
    # So it doesn't return all the voice channel, but all the users that are in the voice channels
    voice_states: Mapping[hikari.Snowflake, hikari.VoiceState] = event.guild.get_voice_states()

    for user_id, user_voice_state in voice_states.items(): # type: ignore

        member: Optional[hikari.Member] = bot.cache.get_member(event.guild_id, user_id)
        if member and member.is_bot:
            continue

        dict_key: str = make_key(user_id, event.guild_id)
        
        if dict_key not in datastore.get_tracking_queue():
            await start_tracking_user(user_id, event.guild_id)
            # print(f"{user_voice_state.member} added to tracking queue on startup...")


async def auto_save_all(interval_seconds: int) -> None:
    while True:
        # print("Running auto_save_all")
        if datastore:
            await datastore.save_all(None)
        else:
            print("Datastore was not available...")

        await asyncio.sleep(interval_seconds)


async def get_stats(interval_seconds: int) -> None:
    while True:
        stats: str = await fetch_stats(bot)
        await bot.rest.create_message(1157849921802752070, stats)

        await asyncio.sleep(interval_seconds)


async def queue_updater(interval_seconds: int) -> None:
    """
    Runs through the tracking queue, and see if the user is still in the VC. If not, remove them from the 
    queue. This is used to catch any edgecases that might happen where the user is no longer in the
    voice channel without the bot catching it. For example, a user leaving a voice channel while an API
    outage occurs, so the leave event on the bot is never fired.
    """
    print("Starting tracking queue auto clearing scheduler")

    while True:
        print("Running tracking queue auto clearing")
        keys_to_remove: List[str] = []

        async with datastore.get_tracking_queue_lock():
            tracking_queue: Dict[str, User] = datastore.get_tracking_queue().copy()


            for key in tracking_queue:
                user_id, guild_id = map(int, key.split("-"))
                # print(f"Tracking queue uid: {user_id}, gid: {guild_id}")
                user_voice_state: Optional[hikari.VoiceState] = bot.cache.get_voice_state(guild_id, user_id)

                # If the user is not in voice channel and they are still in the queue, we add it to the removal list
                if user_voice_state is None:
                    if key in tracking_queue:
                        keys_to_remove.append(key)
                        await datastore.save_single(user_id1=user_id, guild_id1=guild_id)
 
            # Now remove it from the actual dictionary
            for key in keys_to_remove:
                datastore.get_tracking_queue().pop(key, None)

        await asyncio.sleep(interval_seconds)

bot.run()