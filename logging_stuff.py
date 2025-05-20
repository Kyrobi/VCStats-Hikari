import hikari

from textwrap import dedent
from typing import Dict, Optional
from lightbulb import BotApp
import lightbulb

from helper import get_tracking_queue

plugin = lightbulb.Plugin("logging")

shard_guild_counter: Dict[int, int] = {}
total_guild_count: int = 0

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

@plugin.listener(hikari.ShardReadyEvent)
async def reset_guild_counter(event: hikari.ShardReadyEvent) -> None:
    global total_guild_count
    old_shard_guild_count = shard_guild_counter.get(event.shard.id, 0)
    new_shard_guild_count = len(event.unavailable_guilds)

    shard_guild_counter[event.shard.id] = new_shard_guild_count
    total_guild_count += new_shard_guild_count - old_shard_guild_count


@plugin.listener(hikari.GuildJoinEvent)
async def increment_guild_counter(event: hikari.GuildJoinEvent) -> None:
    global total_guild_count
    shard_guild_counter[event.shard.id] += 1
    total_guild_count += 1


@plugin.listener(hikari.GuildLeaveEvent)
async def decrement_guild_counter(event: hikari.GuildLeaveEvent) -> None:
    global total_guild_count
    shard_guild_counter[event.shard.id] -= 1
    total_guild_count -= 1

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


    shard_count: int = 0
    shard_count = bot.shard_count

    shard_message: str = ""
    for k, v in shard_guild_counter.items():
        shard_message += f"Shard ID: {k} - Guilds: {v}\n"
    
    message = dedent(f"""
**Last 24 hours**
```
Total servers: {total_guild_count}
Total members in VC: {len(get_tracking_queue())}
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

def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)