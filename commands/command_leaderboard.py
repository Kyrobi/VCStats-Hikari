from typing import List, Optional

import hikari
from helper import seconds_to_timestamp, get_leaderboard_members_and_time
import lightbulb

plugin = lightbulb.Plugin("command_leaderboard")

@plugin.command
@lightbulb.option("page", "The page number to view", type=int, required=False, default=1, min_value=1)
@lightbulb.command("leaderboard", "Shows your server's leaderboard")
@lightbulb.implements(lightbulb.SlashCommand)
async def leaderboard_command(e: lightbulb.Context) -> None:
    # If bot tries to run commands, nothing will happen
    if e.member and e.member.is_bot:
        return

    # Get page number from options (default to 1)
    page = e.options.page if hasattr(e.options, 'page') else 1
    name_interval = 10  # Shows 10 names per page

    # This is the page that the user wants to see
    requested_page = max(1, int(page))  # Ensure page is at least 1

    # Check if the command is used in a guild. If not, deny it
    guild_id: Optional[int] = e.guild_id
    if guild_id is None:
        await e.respond("Command can only be used inside a server")
        return
    
    # Get all members from the database that are associated with this guild
    all_members: Optional[List[int]]
    all_times: Optional[List[int]]
    
    all_members, all_times = await get_leaderboard_members_and_time(guild_id)

    if all_members is None or all_times is None:
        return

    # Validate requested page
    pages_possible = max(1, (len(all_members) + name_interval - 1) // name_interval)
    if requested_page > pages_possible:
        await e.respond(f"Page {requested_page} does not exist. Pages available: {pages_possible}")
        return
    
    # print(f"All members: {all_members}")

    # Get names for the requested page
    start_idx = (requested_page - 1) * name_interval
    end_idx = start_idx + name_interval
    paged_members = all_members[start_idx:end_idx]
    paged_times = all_times[start_idx:end_idx]

    # Build the leaderboard entries
    leaderboard_entries: List[str] = []
    for i, member_id in enumerate(paged_members):
        position = start_idx + i + 1  # Position in the overall leaderboard
        time_spent = seconds_to_timestamp(paged_times[i])
        # Format each entry with member ID and their time
        leaderboard_entries.append(f"**{position}.** <@{member_id}>: {time_spent}")
    
    leaderboard_content = "\n".join(leaderboard_entries)
    
    # Sum up all the time
    total_time = sum(all_times)
    
    server_total = f"**Server total**: {seconds_to_timestamp(total_time)}\n\n"
    
    result_suffix = f"Page ({requested_page}/{pages_possible})"
    next_page_notice = ""
    
    if requested_page < pages_possible:
        next_page_notice = f"\nDo `/leaderboard {requested_page + 1}` for more results."
    
    # Create embed
    embed = hikari.Embed(
        title="Voice Call Leaderboard [Top 1000]",
        description=f"{leaderboard_content}\n\n{server_total}{result_suffix}{next_page_notice}",
        color=0x3498db
    )
    
    await e.respond(embed)
    

def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
