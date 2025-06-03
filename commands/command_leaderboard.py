import asyncio
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
    
    # Check if the command is used in a guild. If not, deny it
    guild_id: Optional[int] = e.guild_id
    if guild_id is None:
        await e.respond("Command can only be used inside a server")
        return
    
    # Get page number from options (default to 1)
    page = e.options.page if hasattr(e.options, 'page') else 1
    name_interval = 10  # Shows 10 names per page

    requested_page = max(1, int(page))  # This is the page that the user wants to see. Ensure page is at least 1

    all_times: Optional[List[int]] = None
    all_members: Optional[List[int]] = None

    try:
        # Add timeout to prevent indefinite hanging
        await asyncio.wait_for(
            datastore.save_all(guild_id=guild_id), 
            timeout=30.0  # 30 second timeout
        )
    except asyncio.TimeoutError:
        await e.respond("The leaderboard is temporarily unavailable. Please try again later.")
        return
    except Exception as error:
        print(f"Error in leaderboard save_all: {error}")
        await e.respond("An error occurred while updating the leaderboard. Please try again later.")
        return

    try:
        # Get leaderboard data with timeout
        all_members, all_times = await asyncio.wait_for(
            datastore.get_leaderboard_members_and_time(guild_id),
            timeout=15.0
        )
    except asyncio.TimeoutError:
        await e.respond("The leaderboard is temporarily unavailable. Please try again later.")
        return
    except Exception as error:
        print(f"Error fetching leaderboard data: {error}")
        await e.respond("An error occurred while updating the leaderboard. Please try again later.")
        return
    
    increment_leaderboard_used()

    # Validate requested page
    pages_possible = max(1, (len(all_members) + name_interval - 1) // name_interval)
    if requested_page > pages_possible:
        await e.respond(f"Page {requested_page} does not exist. Pages available: {pages_possible}")
        return
    # print(f"All members: {all_members}")

    # Get names for the requested page
    start_idx: int = (requested_page - 1) * name_interval
    end_idx: int = start_idx + name_interval
    paged_members: List[int] = all_members[start_idx:end_idx]
    paged_times: List[int] = all_times[start_idx:end_idx]

    # Build the leaderboard entries
    leaderboard_entries: List[str] = []
    for i, member_id in enumerate(paged_members):
        position = start_idx + i + 1  # Position in the overall leaderboard
        time_spent = seconds_to_timestamp(paged_times[i])
        # Format each entry with member ID and their time
        leaderboard_entries.append(f"**{position}.** <@{member_id}>: {time_spent}")
    
    leaderboard_content: str = "\n".join(leaderboard_entries)
    
    # Sum up all the time
    total_time: int = sum(all_times)
    
    server_total: str = f"**Server total**: {seconds_to_timestamp(total_time)}\n\n"
    
    result_suffix: str = f"Page ({requested_page}/{pages_possible})"
    next_page_notice: str = ""
    
    if requested_page < pages_possible:
        next_page_notice = f"\nDo `/leaderboard {requested_page + 1}` for more results."
    
    # Create embed
    embed = hikari.Embed(
        title="Voice Call Leaderboard [Top 200]",
        description=f"{leaderboard_content}\n\n{server_total}{result_suffix}{next_page_notice}",
        color=0x3498db
    )

    await e.respond(embed)
    

def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
