import hikari
import lightbulb

from helper import seconds_to_timestamp
from logging_stuff import increment_leaderboard_used
from typing import List, Optional
from datastore import Datastore

plugin = lightbulb.Plugin("command_leaderboard")
datastore = Datastore()

@plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("page", "The page number to view", type=int, required=False, default=1, min_value=1)
@lightbulb.command("leaderboard", "Shows your server's leaderboard")
@lightbulb.implements(lightbulb.SlashCommand)
async def leaderboard_command(e: lightbulb.Context) -> None:
    # If bot tries to run commands, nothing will happen
    if e.member and e.member.is_bot:
        return
    
    print("here1")
    # Check if the command is used in a guild. If not, deny it
    guild_id: Optional[int] = e.guild_id
    if guild_id is None:
        await e.respond("Command can only be used inside a server")
        return
    
    print("here2")
    # Get page number from options (default to 1)
    page = e.options.page if hasattr(e.options, 'page') else 1
    name_interval = 10  # Shows 10 names per page
    print("here3")

    requested_page = max(1, int(page))  # This is the page that the user wants to see. Ensure page is at least 1
    print("here4")

    await datastore.save_all(guild_id=guild_id) # Save all the users in the guild so that all the data in the leaderboard will be fresh
    print("here5")

    # Get all members from the database that are associated with this guild
    all_members: Optional[List[int]]
    all_times: Optional[List[int]]
    all_members, all_times = await datastore.get_leaderboard_members_and_time(guild_id)
    print("here6")
    
    increment_leaderboard_used()

    # Validate requested page
    pages_possible = max(1, (len(all_members) + name_interval - 1) // name_interval)
    if requested_page > pages_possible:
        await e.respond(f"Page {requested_page} does not exist. Pages available: {pages_possible}")
        return
    print("here7")
    # print(f"All members: {all_members}")

    # Get names for the requested page
    print("here8")
    start_idx: int = (requested_page - 1) * name_interval
    end_idx: int = start_idx + name_interval
    paged_members: List[int] = all_members[start_idx:end_idx]
    paged_times: List[int] = all_times[start_idx:end_idx]

    # Build the leaderboard entries
    print("here9")
    leaderboard_entries: List[str] = []
    for i, member_id in enumerate(paged_members):
        position = start_idx + i + 1  # Position in the overall leaderboard
        time_spent = seconds_to_timestamp(paged_times[i])
        # Format each entry with member ID and their time
        leaderboard_entries.append(f"**{position}.** <@{member_id}>: {time_spent}")
    
    print("here10")
    leaderboard_content: str = "\n".join(leaderboard_entries)
    
    # Sum up all the time
    total_time: int = sum(all_times)
    
    server_total: str = f"**Server total**: {seconds_to_timestamp(total_time)}\n\n"
    
    result_suffix: str = f"Page ({requested_page}/{pages_possible})"
    next_page_notice: str = ""
    print("here11")
    
    if requested_page < pages_possible:
        next_page_notice = f"\nDo `/leaderboard {requested_page + 1}` for more results."
    
    print("here12")
    # Create embed
    embed = hikari.Embed(
        title="Voice Call Leaderboard [Top 200]",
        description=f"{leaderboard_content}\n\n{server_total}{result_suffix}{next_page_notice}",
        color=0x3498db
    )
    print("here12")
    await e.respond(embed)
    

def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
