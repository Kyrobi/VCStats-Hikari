import hikari
import hikari.errors
import lightbulb

from typing import Optional
from hikari import Member
from helper import if_member_has_permission, if_member_is_owner, get_no_admin_perms_message
from datastore import Datastore

plugin = lightbulb.Plugin("command_set_logging")
datastore = Datastore()

# This command clears the leaderboard for a server
@plugin.command
@lightbulb.app_command_permissions(dm_enabled=False)
@lightbulb.option("channel", "Channel to log to", type=hikari.OptionType.CHANNEL, required=True)
@lightbulb.command("vc_logging", "Sets the channel to log join and leave notifications to")
@lightbulb.implements(lightbulb.SlashCommand)
async def status_command(e: lightbulb.Context) -> None:
        # If bot tries to run commands, nothing will happen

    if e.guild_id is None:
        await e.respond("This command can only be used in a server.")
        return
    
    member: Optional[Member] = e.member
    
    if member is None:
        await e.respond("Something went wrong...")
        return

    if member.is_bot:
        await e.respond("Bots cannot use this command.")
        return
    
    if await if_member_is_owner(guild_id=e.guild_id, user_id=member.id) or await if_member_has_permission(member, hikari.Permissions.ADMINISTRATOR):
        partial_channel: Optional[hikari.PartialChannel] = e.options.channel if hasattr(e.options, 'channel') else None

        try:
            if partial_channel is None:
                await e.respond("Please provide the server ID for this server.")
                return
            
            # We verify that the logging channel is inside from the same guild - incase a mod is used to
            # set the channel from a different guild
            try:
                full_channel: Optional[hikari.PartialChannel] = await plugin.app.rest.fetch_channel(partial_channel.id)
                if not isinstance(full_channel, hikari.GuildChannel) or full_channel.guild_id != e.guild_id:
                    await e.respond("Error setting the channel")
                    return
                
                logging_channel_id: hikari.Snowflake = partial_channel.id
                await e.respond(f"Event logs will be sent to `{partial_channel}`")

                await datastore.set_logging_channel(guild_id=e.guild_id, channel_id=logging_channel_id)
            except:
                pass

        except hikari.errors.BadRequestError:
            await e.respond("That is not a valid channel")

    else:
        await e.respond(get_no_admin_perms_message(),flags=hikari.MessageFlag.EPHEMERAL)
    

    
def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
