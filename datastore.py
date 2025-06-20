import config
import asyncio
import valkey.asyncio as valkey
import time

from typing import List, Optional, Dict
from objects.user import User

DATABASE_NOT_CONNECTED_MESSAGE = "Database is not connected..."

tracking_queue: Dict[str, User] = {}
tracking_queue_lock = asyncio.Lock()


# Define the connection pools
connection_pool = None

# Establish the actual connections
connection = None

class Datastore:

    async def initialize(self):
        global connection_pool
        global connection

        # Define the connection pools
        connection_pool = valkey.ConnectionPool(
            host=config.VALKEY_HOST, 
            port=config.VALKEY_PORT, 
            db=0,
            retry_on_timeout=True,
            socket_timeout=30,
            socket_connect_timeout=30,
            max_connections=20,
            )
        

        # Establish the actual connections
        connection = valkey.Valkey(connection_pool=connection_pool)


    async def uninitialize(self):
        # Close the clients
        if connection:
            await connection.aclose()

        # Close the connection pools
        if connection_pool:
            await connection_pool.aclose()


    def get_tracking_queue(self) -> Dict[str, User]:
        return tracking_queue
    
    def get_tracking_queue_lock(self) -> asyncio.Lock:
        return tracking_queue_lock


    async def insert(self, user_id: int, time_difference: int, server_id: int):
        """Do not call this method directly. It's used by functions liked save_single()"""
        try:
            if connection:
                key = f"guild:{server_id}"

                await connection.zadd(
                    key, 
                    {str(user_id): time_difference}, 
                    incr=True
                )
            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)

        except Exception as error:
            print(f"Error inserting data: {error}")


    async def save_single(self, user_id1: int, guild_id1: int) -> None:
        from helper import make_key

        dict_key: str = make_key(user_id1, guild_id1)

        if dict_key not in tracking_queue:
            return

        user_from_tracking_queue: User = tracking_queue[dict_key]

        user_id: int = user_from_tracking_queue.get_user_id()
        time_difference: int = int(time.time() - user_from_tracking_queue.get_joined_time())
        guild_id: int = user_from_tracking_queue.get_guild_id()

        if time_difference <= 0:
            return

        # Save the time, and then update the time to current so that
        # the difference calculation doesn't break
        if connection is not None:
            try:
                start = time.perf_counter()
                await self.insert(user_id, time_difference, guild_id)
                end = time.perf_counter()
                elapsed_ms = (end - start) * 1000
                from helper import log_info_to_channel
                await log_info_to_channel(1377205400981602334,f"`insert` completed in {elapsed_ms:.3f}ms")
            finally:
                user_from_tracking_queue.set_joined_time(int(time.time()))


    async def save_all(self, guild_id: Optional[int]) -> None:
        """
        Pass in a guild_id if you want to only bulk save a specific guild
        """
        if not connection:
            print(DATABASE_NOT_CONNECTED_MESSAGE)
            return
        
        user_ids: List[int] = []
        time_differences: List[int] = []
        server_ids: List[int] = []


        current_time = int(time.time())

        # Iterate through a copy of the list to avoid size changing while iterating 
        for user in tracking_queue.copy().values():
            if guild_id is None or guild_id == user.get_guild_id():
                time_difference: int = current_time - user.get_joined_time()

                if(time_difference <= 0):
                    continue

                time_differences.append(time_difference)
                user_ids.append(user.get_user_id())
                server_ids.append(user.get_guild_id())

                # Make sure to update the time delta once saving
                user.set_joined_time(current_time)

        # Assumes there nothing to save, so don't run the rest of the code
        if not user_ids: 
            return

        start = time.perf_counter()
        
        BATCH_SIZE = 100

        for i in range(0, len(user_ids), BATCH_SIZE):
            pipe = None
            try:
                await connection.ping() # type: ignore If the ping fails (i.e can't contact server), it raises and exception
                async with asyncio.timeout(30):
                    async with connection.pipeline(transaction=False) as pipe:
                        for j in range(i, min(i + BATCH_SIZE, len(user_ids))):
                            key = f"guild:{server_ids[j]}"
                            pipe.zadd(key, {str(user_ids[j]): time_differences[j]}, incr=True)
                        
                        await pipe.execute()

            except Exception as error:
                print(f"Error in batch {i//BATCH_SIZE + 1} {error}")

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        from helper import log_info_to_channel
        await log_info_to_channel(1377200295389565020,f"`save_all` completed in {elapsed_ms:.3f}ms")
        

    async def get_user_time_and_position(self, user_id: int, server_id: int) -> tuple[int, Optional[int]]:
        
        try:
            if connection:
                start = time.perf_counter()

                # Get the user's time from the sorted set (zscore returns the score, i.e., time)
                # user_time = await asyncio.to_thread(conn_user_stats.zscore, leaderboard_key, str(user_id))
                key = f"guild:{server_id}"

                async with connection.pipeline(transaction=False) as pipe:
                    pipe.zscore(key, str(user_id))
                    pipe.zrevrank(key, str(user_id))
                    results = await pipe.execute() # type: ignore

                user_time = results[0] # type: ignore
                user_position = results[1] # type: ignore
                
                # user_time = await asyncio.to_thread(conn_user_stats.zscore, key, str(user_id))

                if user_time is None:
                    print("None user time")
                    return (0, None)  # If user doesn't have time, return default values

                # Get the user's position from the sorted set (zrank returns the 0-based index)
                # user_position = await asyncio.to_thread(conn_user_stats.zrevrank, key, str(user_id))
                # print(f"{user_position}")

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
        
        
    async def get_leaderboard_members_and_time(self, guild_id: int) -> tuple[list[int], list[int]]:
        users: List[int] = []
        times: List[int] = []

        key = f"guild:{guild_id}"

        start = time.perf_counter()
        try:
            if connection:

                # Get the top 500 users by time (scores in descending order)
                leaderboard = await connection.zrevrange(key, 0, 199, withscores=True) # type: ignore

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
            if connection:
                await connection.delete(key)
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
            if connection:
                await connection.zrem(key, str(user_id))
            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
        except Exception as error:
            print(f"Error deleting user from Valkey: {error}")

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        from helper import log_info_to_channel
        await log_info_to_channel(1377200295389565020,f"`reset_specific_user` completed in {elapsed_ms:.3f}ms")