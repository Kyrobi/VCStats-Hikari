from textwrap import dedent
import hikari
import lightbulb

plugin = lightbulb.Plugin("command_donate")

@plugin.command
@lightbulb.command("donate", "Help contribute :)")
@lightbulb.implements(lightbulb.SlashCommand)
async def status_command(e: lightbulb.Context) -> None:
        # If bot tries to run commands, nothing will happen
    if e.member and e.member.is_bot:
        return
    
    message = dedent("""
    If the bot has provided you value, feel free to [donate](<https://bit.ly/3YvmWud>) :)
    """).strip()

    await e.respond(
        message,
        flags=hikari.MessageFlag.EPHEMERAL
        )
    


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
