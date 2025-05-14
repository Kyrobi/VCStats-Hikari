import config
import hikari
import lightbulb

# Initialize the bot - NEW SYNTAX for Lightbulb 2.x
bot = lightbulb.BotApp(
    token=config.BOT_TOKEN,
    intents=hikari.Intents.ALL  # Adjust intents as needed
)

# Function when the bot is starting up
@bot.listen(hikari.StartingEvent)
async def on_starting(event: hikari.StartingEvent) -> None:
    ...
    # Load Eventhandlers
    bot.load_extensions("handlers.event_handler") # Handles the join and leave events

    # Load Commands
    bot.load_extensions("commands.command_stats")
    bot.load_extensions("commands.command_help")
    bot.load_extensions("commands.command_donate")

# Function when the bot is shutting down
@bot.listen(hikari.StoppingEvent)
async def on_stopping(event: hikari.StoppingEvent) -> None:
    print("Bot shutting down")


bot.run()