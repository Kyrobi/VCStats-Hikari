from typing import List, Optional

import hikari
from helper import milliseconds_to_timestamp, get_leaderboard_members_and_time
import lightbulb

plugin = lightbulb.Plugin("command_leaderboard")

@plugin.command
@lightbulb.command("leaderboard", "Shows your server's leaderboard")
@lightbulb.implements(lightbulb.SlashCommand)
async def donate_command(e: lightbulb.Context) -> None:
    # If bot tries to run commands, nothing will happen
    if e.member and e.member.is_bot:
        return

    # Get page number from options (default to 1)
    page = e.options.page if hasattr(e.options, 'page') else 1
    name_interval = 10  # Shows 10 names per page
    requested_page = max(1, int(page))  # Ensure page is at least 1

    # Check if the command is used in a guild. If not, deny it
    guild_id: Optional[int] = e.guild_id
    if guild_id is None:
        await e.respond("Command can only be used inside a server")
        return
    
    # Get all members from the database that are associated with this guild
    all_members: List[int]
    all_times: List[int]
    
    all_members, all_times = await get_leaderboard_members_and_time(guild_id)
    pages_possible = max(1, (len(all_members) + name_interval - 1) // name_interval)
    
    # Validate requested page
    if requested_page > pages_possible:
        await e.respond(f"Page {requested_page} does not exist. Pages available: {pages_possible}")
        return
    
    # Get names for the requested page
    start_idx = (requested_page - 1) * name_interval
    end_idx = start_idx + name_interval
    paged_names = all_members[start_idx:end_idx]

    # Sum up all the time
    total_time: int = 0
    for i in all_times:
        total_time += i
    
    # Build the leaderboard message
    leaderboard_content: str = "".join(paged_names)
    server_total = f"**Server total**: {milliseconds_to_timestamp(total_time)}\n\n"
    
    result_suffix = f"Page ({requested_page}/{pages_possible})"
    next_page_notice = ""
    
    if requested_page < pages_possible:
        next_page_notice = f"\nDo `/leaderboard {requested_page + 1}` for more results."
    
    # Create embed
    embed = hikari.Embed(
        title="Voice Call Leaderboard [Top 1000]",
        description=f"{leaderboard_content}{server_total}{result_suffix}{next_page_notice}",
        color=0x3498db
    )
    
    await e.respond(embed)
    

def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
