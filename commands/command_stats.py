import time
import lightbulb

from typing import Optional
from helper import save_tracking_stats_single, make_key, milliseconds_to_timestamp, get_user_time_and_leaderboard_position, tracking_queue

plugin = lightbulb.Plugin("command_stats")

@plugin.command
@lightbulb.command("stats", "Shows your total time in the voice chat for this server")
@lightbulb.implements(lightbulb.SlashCommand)
async def status_command(e: lightbulb.Context) -> None:
        # If bot tries to run commands, nothing will happen
    if e.member and e.member.is_bot:
        return
    
    # Update stats right before showing them (if needed)
    # You'll need to implement your save_stats and start_stats equivalents
    # if ctx.member.id in join_tracker:  # Assuming you have a similar join_tracker
    #     await save_stats(ctx.member)
    #     await start_stats(ctx.member)

    # Get leaderboard position and time
    guild_id: Optional[int] = e.guild_id
    user_id: Optional[int] = e.author.id

    if guild_id is None:
        await e.respond("This command can only be used inside a server")
        return
    
    db_total_time, leaderboard_position = await get_user_time_and_leaderboard_position(user_id, guild_id) # Current time in the database
    new_total_time: Optional[int] = None

    # If the user is actively in the VC, we add onto the time in the database
    dict_key = make_key(user_id, guild_id)
    if dict_key in tracking_queue:
        time_delta: int = int(time.time()) - int(tracking_queue[dict_key].get_joined_time())
        
        new_total_time = db_total_time + time_delta

        await save_tracking_stats_single(user_id, guild_id)
        # Purposfully not pop the data from the dictionary since it's assumed the user is still in the VC

    if leaderboard_position is not None:
        # If the user is in the VC while using this command, we fetch the database time with the time delta added on
        if new_total_time is not None:
            await e.respond(
                f"{e.author.mention}\n"
                f"Leaderboard Ranking: **#{leaderboard_position}**\n"
                f"Total Time Spent: **{milliseconds_to_timestamp(new_total_time)}**",
                user_mentions=True
            )
        # If the user is not in the VC, just grab the time from the database
        else:
            await e.respond(
                f"{e.author.mention}\n"
                f"Leaderboard Ranking: **#{leaderboard_position}**\n"
                f"Total Time Spent: **{milliseconds_to_timestamp(db_total_time)}**",
                user_mentions=True
            )

    else:
        await e.respond("You have never been in a voice call before on this server. Please join one to start tracking your time.")
        return



def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
