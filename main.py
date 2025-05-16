import config
import hikari
import lightbulb

from helper import initialize, uninitialize, get_tracking_queue, make_key
from typing import Dict, Mapping

from objects.user import User

user_tracker_queue: Dict[str, User] = get_tracking_queue()

# Initialize the bot - NEW SYNTAX for Lightbulb 2.x
bot = lightbulb.BotApp(
    token=config.BOT_TOKEN,
    intents=hikari.Intents.ALL  # Adjust intents as needed
)

# Function when the bot is starting up
@bot.listen(hikari.StartingEvent)
async def on_starting(event: hikari.StartingEvent) -> None:
    # Load Eventhandlers
    bot.load_extensions("handlers.event_handler") # Handles the join and leave events

    # Load Commands
    bot.load_extensions("commands.command_stats")
    bot.load_extensions("commands.command_help")
    bot.load_extensions("commands.command_donate")
    # bot.load_extensions("commands.command_leaderboard")

# After bot has fully started
@bot.listen(hikari.StartedEvent)
async def on_started(event: hikari.StartedEvent) -> None:

    await initialize(bot)

    # await user_tracker.add_all_users_in_voice_channels(bot)
    print(f"Initialized tracking for {len(user_tracker_queue)} users already in voice channels")

# Function when the bot is shutting down
@bot.listen(hikari.StoppingEvent)
async def on_stopping(event: hikari.StoppingEvent) -> None:
    await uninitialize()
    print("Bot shutting down")

@bot.listen(hikari.GuildAvailableEvent)
async def on_guild_available(event: hikari.GuildAvailableEvent) -> None:

    voice_states: Mapping[hikari.Snowflake, hikari.VoiceState] = event.guild.get_voice_states()

    for voice_state in voice_states.values():
        print(voice_state.member)


bot.run()