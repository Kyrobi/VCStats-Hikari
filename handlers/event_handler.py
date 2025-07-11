import lightbulb
import hikari

from typing import Optional
from helper import make_key, start_tracking_user
from logging_stuff import increment_member_join, increment_member_left, increment_member_move
from datastore import Datastore


plugin = lightbulb.Plugin("event_handler")
datastore = Datastore()

@plugin.listener(hikari.VoiceStateUpdateEvent) # type: ignore
async def on_voice_event(e: hikari.VoiceStateUpdateEvent):
    # user_id = e.state.user_id

    # Old channel state is what the previous channel is. So if a user joins a channel, 
    # their old one will be null since they haven't joined a channel before.
    # New channel state will be the one that they just joined.
    old_voice_state: Optional[hikari.VoiceState] = e.old_state
    new_voice_state: Optional[hikari.VoiceState] = e.state

    # You actually need the ID since that's how you determine if you joined / left the channel since
    # voice state won't always be None
    old_channel_id: Optional[hikari.Snowflake] = old_voice_state.channel_id if old_voice_state else None
    new_channel_id: Optional[hikari.Snowflake] = new_voice_state.channel_id if new_voice_state else None

    ########################
    # Joined a voice channel
    ########################
    if old_channel_id is None and new_channel_id is not None:
        # print(f"User {user_id} joined voice channel {new_channel_id}")
        await handle_join(new_voice_state)

    ########################
    # Left a voice channel
    ########################
    elif old_channel_id is not None and new_channel_id is None:
        # print(f"User {user_id} left voice channel {old_channel_id}")
        if old_voice_state is not None:
            await handle_leave(old_voice_state)

    ########################
    # Switched voice channels
    ########################
    elif old_channel_id != new_channel_id:
        if old_voice_state is not None:
            await handle_switch(old_voice_state, new_voice_state)
    


async def handle_join(voice_state: hikari.VoiceState):
    # print(f"{voice_state.member} joined channel")

    if voice_state.member is not None:
        if voice_state.member.is_bot:
            return

    increment_member_join()
    await start_tracking_user(voice_state.user_id, voice_state.guild_id)


async def handle_leave(voice_state: hikari.VoiceState):
    
    if voice_state.member is not None:
        if voice_state.member.is_bot:
            return
    
    increment_member_left()

    # After saving, remove the user from the dictionary to clean up
    user_id = voice_state.user_id
    guild_id = voice_state.guild_id

    await datastore.save_single(user_id, guild_id)

    dict_key: str = make_key(user_id, guild_id)

    async with datastore.get_tracking_queue_lock():
        datastore.get_tracking_queue().pop(dict_key, None)


async def handle_switch(old_voice_state: hikari.VoiceState, new_voice_state: hikari.VoiceState):
    # UPDATE: We don't actually care about if the user switch channels
    # Since switching channels is effectively just staying in the same channel.
    # Because of this, we only really care about if the user leaves.

    # This function will effectively only be used for logging purposes
    # print(f"{new_voice_state.member} switched channel")
    increment_member_move()


# REQUIRED FUNCTION - Lightbulb looks for this
def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(plugin)