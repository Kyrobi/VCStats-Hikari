import hikari
import lightbulb


plugin = lightbulb.Plugin("command_test")

@plugin.command
@lightbulb.command("test", "does nothing", guilds=[1000784443797164136])
@lightbulb.implements(lightbulb.SlashCommand)
async def status_command(e: lightbulb.Context) -> None:
        # If bot tries to run commands, nothing will happen
    if e.member and e.member.is_bot:
        return

    await e.respond("test!!!",flags=hikari.MessageFlag.EPHEMERAL)    


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
