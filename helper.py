from typing import Dict, List, Optional
from lightbulb import Plugin
import lightbulb
from handlers.database_handler import DatabaseHandler
from objects.user import User

import time

from objects.user import User

class UserTracker:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UserTracker, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        # Initalize all the 
        self.tracking_queue: Dict[str, User] = {}
        self.db_handler: Optional[DatabaseHandler] = None

        self._initialized = True

    async def initialize(self):
        self.db_handler = DatabaseHandler()
        await self.db_handler.init()

    async def uninitialize(self):
        if self.db_handler is not None:
            await self.db_handler.uninitialize()

    async def log_info_to_channel(self, client: Plugin, channel_id: int, message: str) -> None:
        await client.app.rest.create_message(
                channel_id,
                message
            )
        
    def get_tracking_queue(self) -> Dict[str, User]:
        return self.tracking_queue

    async def start_tracking_user(self, user_id: int, guild_id: int):
        # Original Java code saved the time in milliseconds, so
        # we need to convert the time into milliseconds as well
        # so that it doesn't mess up existing data
        seconds: int = int(time.time())

        self.tracking_queue[self.make_key(user_id, guild_id)] = User(user_id, guild_id, seconds)


    async def save_tracking_stats_single(self, user_id1: int, guild_id1: int):
        dict_key: str = self.make_key(user_id1, guild_id1)
        user_from_tracking_queue: User = self.tracking_queue[dict_key]

        user_id: int = user_from_tracking_queue.get_user_id()
        time_difference: int = int(time.time() - user_from_tracking_queue.get_joined_time())
        guild_id: int = user_from_tracking_queue.get_guild_id()

        # Save the time, and then update the time to current so that
        # the difference calculation doesn't break
        if self.db_handler is not None:
            await self.db_handler.insert(user_id, time_difference, guild_id)
            user_from_tracking_queue.set_joined_time(int(time.time()))


    async def save_tracking_stats_bulk(self) -> None:
        user_ids: List[int] = []
        time_differences: List[int] = []
        server_ids: List[int] = []

        for user in self.tracking_queue.values():
            current_user: User = user

            time_difference: int = int(time.time()) - current_user.get_joined_time()

            time_differences.append(time_difference)
            user_ids.append(current_user.get_guild_id())
            server_ids.append(current_user.get_guild_id())

            # Make sure to update the time delta once saving
            current_user.set_joined_time(int(time.time()))

        if self.db_handler is not None:
            await self.db_handler.bulk_insert(user_ids, time_differences, server_ids)


    async def get_user_time_and_leaderboard_position(self, user_id: int, guild_id: int) -> tuple[Optional[int], Optional[int]]:
        if self.db_handler is not None:
            return await self.db_handler.get_user_time_and_position(user_id, guild_id)
        else:
            return None, None


    async def get_leaderboard_members_and_time(self, guild_id: int) -> tuple[Optional[list[int]], Optional[list[int]]]:
        if self.db_handler is not None:
            return await self.db_handler.get_leaderboard_members_and_time_from_database(guild_id)
        else:
            return None, None


    async def add_all_users_in_voice_channels(self, bot: lightbulb.BotApp) -> None:
        # Iterate through all guilds the bot is in
        async for guild in bot.rest.fetch_my_guilds():

            print(f"Guild: {guild.name}")
            # Get voice states for this guild
            voice_states = bot.cache.get_voice_states_view_for_guild(guild.id)
            # print(f"Voice_states: {voice_state.member.nickname}")
            # Iterate through all voice states in this guild
            for voice_state in voice_states.values():

                # Get the member object
                member = bot.cache.get_member(guild.id, voice_state.user_id)
                
                if member and voice_state.channel_id is not None:  # Make sure they're in a voice channel
                    if not member.is_bot:  # Filter out bots
                        print(f"Adding {member}")
                        dict_key = self.make_key(member.id, guild.id)
                        self.tracking_queue[dict_key] = User(member.id, guild.id, int(time.time()))

        print("test")

    @staticmethod
    def seconds_to_timestamp(seconds: int) -> str:
        # Implement your milliseconds to timestamp conversion
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours:,}h {minutes}m {seconds}s"

    @staticmethod
    def make_key(user_id: int, guild_id: int) -> str:
        key: str = f"{user_id}-{guild_id}"
        return key