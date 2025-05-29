import lightbulb

from typing import Optional
from helper import get_tracking_queue, get_user_time_and_leaderboard_position, make_key, save_tracking_stats_single, seconds_to_timestamp
from logging_stuff import increment_stats_used

plugin = lightbulb.Plugin("command_stats")

@plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
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
    
    increment_stats_used()
    
    # If the user is actively in the VC, we add onto the time in the database
    dict_key = make_key(user_id, guild_id)
    if dict_key in get_tracking_queue():
        await save_tracking_stats_single(user_id, guild_id)
    
    db_total_time, leaderboard_position = await get_user_time_and_leaderboard_position(user_id, guild_id) # Current time in the database

    # print(f"db_total_time: {db_total_time}, leaderboard_position: {leaderboard_position}")

    db_total_time = 0 if db_total_time is None else db_total_time

    if leaderboard_position is not None:
        # If the user is not in the VC, just grab the time from the database
        await e.respond(
            f"{e.author.mention}\n"
            f"Ranking: **#{leaderboard_position}** `Updated hourly`\n"
            f"Total Time Spent: **{seconds_to_timestamp(db_total_time)}**\n\n"
            ,user_mentions=True
        )

    else:
        await e.respond("You have never been in a voice call before on this server. Please join one to start tracking your time.")
        return



def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
