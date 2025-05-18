from textwrap import dedent
import lightbulb

plugin = lightbulb.Plugin("command_stats")

@plugin.command
@lightbulb.command("help", "Show shows the available bot commands")
@lightbulb.implements(lightbulb.SlashCommand)
async def status_command(e: lightbulb.Context) -> None:
        # If bot tries to run commands, nothing will happen
    if e.member and e.member.is_bot:
        return
    await e.respond(get_message())
    
    
def get_message() -> str:
    message = dedent("""
    **Commands**:
    ```
    /stats - View your call time for the current server
    /leaderboard - View the vc leaderboard for your server
    /donate - If you wish to donate money
    ```
    **Administrator Commands**:
    (Need administrator permission)
    ```
    /resetall - Reset EVERYONE's total voice time. This can't be undone!!!
    /resetuser - Reset specific person's total voice time. This can't be undone!!!
    ```
    **Notes**:
    ```
    - Users in an AFK voice channel won't have their time counted.
    ```
    """).strip()

    return message

def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)
