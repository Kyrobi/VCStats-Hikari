import hikari
import lightbulb

from typing import Optional
from hikari import Member
from helper import if_member_has_permission, reset_all
from logging_stuff import increment_reset_all_used

plugin = lightbulb.Plugin("command_reset_all")

# This command clears the leaderboard for a server
@plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("guild_id", "Current guild/server ID", type=str, required=True)
@lightbulb.command("resetall", "Reset EVERYONE's total voice time. This can't be undone!!!")
@lightbulb.implements(lightbulb.SlashCommand)
async def status_command(e: lightbulb.Context) -> None:
        # If bot tries to run commands, nothing will happen

    if e.guild_id is None:
        await e.respond("This command can only be used in a server.")
        return
    
    member: Optional[Member] = e.member
    current_guild_id: int = e.guild_id
    
    if member is None:
        await e.respond("Something went wrong...")
        return

    if member.is_bot:
        await e.respond("Bots cannot use this command.")
        return
    
    if await if_member_has_permission(member, hikari.Permissions.ADMINISTRATOR):
        confirmation_id: Optional[str] = e.options.guild_id if hasattr(e.options, 'guild_id') else None

        if confirmation_id is None:
            await e.respond("Please provide the server ID for this server.")
            return
        
        try:
            if int(confirmation_id) != current_guild_id:
                await e.respond("This is not the correct server ID for this server.")
                return
            
            await reset_all(current_guild_id)
            await e.respond("Everyone's stats got reset!")
            increment_reset_all_used()

        except ValueError:
            await e.respond("This is not a valid server ID.")
            return

    else:
        await e.respond("You need to have administrator permission to use this command", flags=hikari.MessageFlag.EPHEMERAL)
    

    

def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
