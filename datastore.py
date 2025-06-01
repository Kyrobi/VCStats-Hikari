import config
import valkey
import asyncio
import time

from typing import List, Optional, Dict
from objects.user import User
from asyncache import cached # type: ignore
from cachetools import TTLCache

DATABASE_NOT_CONNECTED_MESSAGE = "Database is not connected..."

tracking_queue: Dict[str, User] = {}
tracking_queue_lock = asyncio.Lock()

# Dict[Tuple[int, int], int] -> guildID, userID, position
user_leaderboard_position_cache: TTLCache[tuple[int, int], int] = TTLCache(maxsize=10_000, ttl=60 * 60) # type: ignore

# Define the connection pools
connection_pool_0 = None
connection_pool_1 = None

# Establish the actual connections
conn_user_stats = None
conn_server_settings = None

class Datastore:

    async def initialize(self):
        global connection_pool_0
        global connection_pool_1

        global conn_user_stats
        global conn_server_settings

        # Define the connection pools
        connection_pool_0 = valkey.ConnectionPool(host=config.VALKEY_HOST, port=config.VALKEY_PORT, db=0)
        connection_pool_1 = valkey.ConnectionPool(host=config.VALKEY_HOST, port=config.VALKEY_PORT, db=1)

        # Establish the actual connections
        conn_user_stats = valkey.Valkey(connection_pool=connection_pool_0)
        conn_server_settings = valkey.Valkey(connection_pool=connection_pool_1)


    async def uninitialize(self):
        # Close the clients
        if conn_user_stats:
            conn_user_stats.close()

        if conn_server_settings:
            conn_server_settings.close()

        # Close the connection pools
        if connection_pool_0:
            connection_pool_0.disconnect()

        if connection_pool_1:
            connection_pool_1.disconnect()

    def get_tracking_queue(self) -> Dict[str, User]:
        return tracking_queue

    def get_tracking_queue_lock(self) -> asyncio.Lock:
        return tracking_queue_lock


    async def insert(self, user_id: int, time_difference: int, server_id: int):
        "Do not call this method directly. It's used by functions liked save_single()"
        try:
            if conn_user_stats:

                # Get the current time value for the user from the hash
                # current_time = await asyncio.to_thread(conn_user_stats.hget, key, field)
                key = f"guild:{server_id}"
                current_time = await asyncio.to_thread(conn_user_stats.zscore, key, str(user_id))

                # If the time exists, add the time difference, otherwise set it to the time_difference
                if current_time:
                    new_time = int(current_time) + time_difference # type: ignore
                else:
                    new_time = time_difference

                # Set the new time in the hash
                # await asyncio.to_thread(conn_user_stats.hset, key, field, str(new_time)) # type: ignore
                # conn_user_stats.zadd(key, {str(user_id): str(new_time)})
                await asyncio.to_thread(conn_user_stats.zadd, key, {str(user_id): str(new_time)})

            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)

        except Exception as error:
            print(f"Error inserting data: {error}")

    async def save_single(self, user_id1: int, guild_id1: int) -> None:
        from helper import make_key

        dict_key: str = make_key(user_id1, guild_id1)
        user_from_tracking_queue: User = tracking_queue[dict_key]

        user_id: int = user_from_tracking_queue.get_user_id()
        time_difference: int = int(time.time() - user_from_tracking_queue.get_joined_time())
        guild_id: int = user_from_tracking_queue.get_guild_id()

        if time_difference <= 0:
            return

        # Save the time, and then update the time to current so that
        # the difference calculation doesn't break
        if conn_user_stats is not None:

            start = time.perf_counter()
            await self.insert(user_id, time_difference, guild_id)
            end = time.perf_counter()
            elapsed_ms = (end - start) * 1000
            from helper import log_info_to_channel
            await log_info_to_channel(1377205400981602334,f"`insert` completed in {elapsed_ms:.3f}ms")

            user_from_tracking_queue.set_joined_time(int(time.time()))

    async def save_all(self) -> None:
        if not conn_user_stats:
            print(DATABASE_NOT_CONNECTED_MESSAGE)
            return
        
        user_ids: List[int] = []
        time_differences: List[int] = []
        server_ids: List[int] = []

        async with tracking_queue_lock:
            for user in tracking_queue.values():
                current_user: User = user

                time_difference: int = int(time.time()) - current_user.get_joined_time()

                if(time_difference <= 0):
                    continue

                time_differences.append(time_difference)
                user_ids.append(current_user.get_user_id())
                server_ids.append(current_user.get_guild_id())

                # Make sure to update the time delta once saving
                current_user.set_joined_time(int(time.time()))

        start = time.perf_counter()
        
        BATCH_SIZE = 1000
        for i in range(0, len(user_ids), BATCH_SIZE):
            pipe = conn_user_stats.pipeline(transaction=False) # type: ignore
            for j in range(i, min(i + BATCH_SIZE, len(user_ids))):
                key = f"guild:{server_ids[j]}"
                pipe.zadd(key, {str(user_ids[j]): time_differences[j]}) # type: ignore
            await asyncio.to_thread(pipe.execute)

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        from helper import log_info_to_channel
        await log_info_to_channel(1377200295389565020,f"`save_all` completed in {elapsed_ms:.3f}ms")


    async def get_user_time(self, user_id: int, server_id: int) -> Optional[int]:
        start = time.perf_counter()
        try:
            if conn_user_stats:

                key = f"guild:{server_id}"

                # Use asyncio.to_thread to run the synchronous hget in a separate thread
                print("here1")
                result: Optional[str] = await asyncio.to_thread(conn_user_stats.zscore, key, str(user_id)) # type: ignore
                print(f"{result}")

                # Return the result, defaulting to 0 if not found
                end = time.perf_counter()
                elapsed_ms = (end - start) * 1000
                from helper import log_info_to_channel
                await log_info_to_channel(1377200295389565020,f"`get_user_time` completed in {elapsed_ms:.3f}ms")
                return int(result) if result else 0
            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
                return None
        except Exception as error:  # Catch any potential errors
            print(f"Error fetching time: {error}")
            return None
        

    async def get_user_time_and_position(self, user_id: int, server_id: int) -> tuple[int, Optional[int]]:
        
        try:
            if conn_user_stats:
                start = time.perf_counter()

                # Get the user's time from the sorted set (zscore returns the score, i.e., time)
                # user_time = await asyncio.to_thread(conn_user_stats.zscore, leaderboard_key, str(user_id))
                key = f"guild:{server_id}"
                user_time = await asyncio.to_thread(conn_user_stats.zscore, key, str(user_id))

                if user_time is None:
                    print("None user time")
                    return (0, None)  # If user doesn't have time, return default values

                # Get the user's position from the sorted set (zrank returns the 0-based index)
                print("here2")
                # user_position = await asyncio.to_thread(conn_user_stats.zrank, leaderboard_key, str(user_id))
                user_position = await asyncio.to_thread(conn_user_stats.zrevrank, key, str(user_id))
                print(f"{user_position}")

                end = time.perf_counter()
                elapsed_ms = (end - start) * 1000
                from helper import log_info_to_channel
                await log_info_to_channel(1377200295389565020,f"`get_user_time_and_position` completed in {elapsed_ms:.3f}ms")

                # Return the time and position (position is 1-based)
                return (int(user_time), user_position + 1 if user_position is not None else None) # type: ignore

            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
                return (0, None)
        except Exception as error:
            print(f"Error fetching time and position: {error}")
            return (0, None)
        
        

    get_leaderboard_members_and_time_cache = TTLCache(maxsize=500, ttl=60 * 60 * 1) # type: ignore
    @cached(get_leaderboard_members_and_time_cache) # type: ignore
    async def get_leaderboard_members_and_time(self, guild_id: int) -> tuple[list[int], list[int]]:
        users: List[int] = []
        times: List[int] = []

        key = f"guild:{guild_id}"

        start = time.perf_counter()
        try:
            if conn_user_stats:

                # Get the top 500 users by time (scores in descending order)
                leaderboard = await asyncio.to_thread(conn_user_stats.zrevrange, key, 0, 199, withscores=True) # type: ignore

                # Loop through the leaderboard and separate the user IDs and times
                for user_id, score in leaderboard: # type: ignore
                    users.append(int(user_id))  # type: ignore # Convert user_id to integer
                    times.append(int(score))    # type: ignore # Convert score (time) to integer

            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
                
        except Exception as e:
            print(f"Error fetching leaderboard data: {e}")

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        from helper import log_info_to_channel
        await log_info_to_channel(1377200295389565020,f"`get_leaderboard_members_and_time` completed in {elapsed_ms:.3f}ms")
            
        return users, times

    async def reset_guild_data(self, guild_id: int) -> None:
        start = time.perf_counter()
        key = f"guild:{guild_id}"
        try:
            if conn_user_stats:
                # await conn_user_stats.delete(str(guild_id))
                await asyncio.to_thread(conn_user_stats.delete, key)
            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
        except Exception as error:
            print(f"Error deleting Valkey data: {error}")

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        from helper import log_info_to_channel
        await log_info_to_channel(1377200295389565020,f"`reset_guild_data` completed in {elapsed_ms:.3f}ms")


    async def reset_user_data(self, guild_id: int, user_id: int) -> None:
        start = time.perf_counter()
        key = f"guild:{guild_id}"
        try:
            if conn_user_stats:
                # conn_user_stats.hdel(str(guild_id), str(user_id))
                await asyncio.to_thread(conn_user_stats.zrem, key, str(user_id))
            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
        except Exception as error:
            print(f"Error deleting user from Valkey: {error}")

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        from helper import log_info_to_channel
        await log_info_to_channel(1377200295389565020,f"`reset_specific_user` completed in {elapsed_ms:.3f}ms")
