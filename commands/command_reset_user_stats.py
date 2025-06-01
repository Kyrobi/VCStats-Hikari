import hikari
import lightbulb

from typing import Optional
from hikari import Member
from helper import if_member_has_permission, if_member_is_owner, get_no_admin_perms_message
from logging_stuff import increment_reset_user_used
from datastore import Datastore

plugin = lightbulb.Plugin("command_reset_user")
datastore = Datastore()

# This command clears the leaderboard for a server
@plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("user_id", "ID of the member you want to reset", type=str, required=True)
@lightbulb.command("resetuser", "Reset a specific user's stats. This cannot be undone!!!")
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
    
    if await if_member_is_owner(guild_id=e.guild_id, user_id=member.id) or await if_member_has_permission(member, hikari.Permissions.ADMINISTRATOR):
        member_to_reset: Optional[str] = e.options.user_id if hasattr(e.options, 'user_id') else None

        if member_to_reset is None:
            await e.respond("Invalid member.")
            return
        

        user = None
        try:
            user = await plugin.bot.rest.fetch_user(int(member_to_reset))

            await datastore.reset_user_data(current_guild_id, int(member_to_reset))
            await e.respond(f"{user.mention}'s stats got reset!")
            increment_reset_user_used()

        except hikari.NotFoundError:
            await e.respond("User does not exist.")
            return
        except (hikari.UnauthorizedError, hikari.RateLimitTooLongError, hikari.InternalServerError):
            await e.respond("Something went wrong running this command.")
            return
        except ValueError:
            await e.respond("Invalid user ID.")
            return

    else:
        await e.respond(get_no_admin_perms_message(), flags=hikari.MessageFlag.EPHEMERAL)
    

    

def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
