from textwrap import dedent
from typing import Optional

from lightbulb import BotApp

bot: Optional[BotApp] = None

totalTimesJoined: int = 0
totalTimesLeft: int = 0
totalTimesMoved: int = 0

# Commands
helpUsed: int = 0
statsUsed: int = 0
leaderboardUsed: int = 0
resetAllUsed: int = 0
resetUserUsed: int = 0
donateUsed: int = 0

@staticmethod
def increment_member_join() -> None:
    global totalTimesJoined
    totalTimesJoined += 1

@staticmethod
def increment_member_left() -> None:
    global totalTimesLeft
    totalTimesLeft += 1

@staticmethod
def increment_member_move() -> None:
    global totalTimesMoved
    totalTimesMoved += 1

@staticmethod
def increment_help_used() -> None:
    global helpUsed
    helpUsed += 1

@staticmethod
def increment_stats_used() -> None:
    global statsUsed
    statsUsed += 1

@staticmethod
def increment_leaderboard_used() -> None:
    global leaderboardUsed
    leaderboardUsed += 1

@staticmethod
def increment_reset_all_used() -> None:
    global resetAllUsed
    resetAllUsed += 1

@staticmethod
def increment_reset_user_used() -> None:
    global resetUserUsed
    resetUserUsed += 1

@staticmethod
def increment_donate_used() -> None:
    global donateUsed
    donateUsed += 1

async def fetch_stats(bot: Optional[BotApp]) -> str:

    if bot is None:
        return "Error"
    
    global totalTimesJoined
    global totalTimesLeft
    global totalTimesMoved

    global helpUsed
    global statsUsed
    global leaderboardUsed
    global resetAllUsed
    global resetUserUsed
    global donateUsed
    
    totalServers: int = 0
    totalMembers: int = 0
    totalMembersInVC : int = 0

    for i in bot.cache.get_available_guilds_view():
        totalServers += 1
        totalMembers += len(bot.cache.get_members_view_for_guild(i))
        totalMembersInVC += len(bot.cache.get_voice_states_view_for_guild(i))

    shard_count: int = 0
    shard_count = bot.shard_count

    shard_message: str = ""
    guilds_per_shard = {}
    # Loop through all guilds and count them for each shard
    for guild_id, guild in bot.cache.get_guilds_view().items():
        # Calculate which shard this guild belongs to
        shard_id = (guild_id >> 22) % bot.shard_count
        
        # Increment the count for this shard
        if shard_id not in guilds_per_shard:
            guilds_per_shard[shard_id] = 0
        guilds_per_shard[shard_id] += 1

    # Now output the information
    for id, shard_gateway in bot.shards.items():
        guild_count: int = guilds_per_shard.get(id, 0) # type: ignore
        shard_message += f"Shard ID: {id} - Guilds: {guild_count}\n"
    
    message = dedent(f"""
    **Last 24 hours**:
    ```
    Total servers the bot is in: {totalServers}
    Total members in all servers: {totalMembers}
    Total members in VC at the moment: {totalMembersInVC}
    ==========
    Total times joined: {totalTimesJoined}
    Total times left: {totalTimesLeft}
    Total times moved: {totalTimesMoved}
    ==========
    /donate used: {donateUsed}
    /resetall used: {resetAllUsed}
    /resetuser used: {resetUserUsed}
    /help used: {helpUsed}
    /stats used: {statsUsed}
    /leaderboard used: {leaderboardUsed}
    ==========
    Total Shards: {shard_count}
    {shard_message}
    ```
    """).strip()

    totalTimesJoined = 0
    totalTimesLeft = 0
    totalTimesMoved = 0

    helpUsed = 0
    statsUsed = 0
    leaderboardUsed = 0
    resetAllUsed = 0
    resetUserUsed = 0
    donateUsed = 0

    return message

def start_logging(botInstance: BotApp) -> None:
    global bot
    bot = botInstance