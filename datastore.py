import config
import valkey
import asyncio
import time

from typing import List, Optional, Dict
from objects.user import User
from asyncache import cached # type: ignore
from cachetools import TTLCache
from helper import log_info_to_channel

DATABASE_NOT_CONNECTED_MESSAGE = "Database is not connected..."

tracking_queue: Dict[str, User] = {}
tracking_queue_lock = asyncio.Lock()

# Define the connection pools
connection_pool_0 = None
connection_pool_1 = None

# Establish the actual connections
conn_user_stats = None
conn_server_settings = None

class Datastore:

    DATABASE_FILE_NAME = "database.db"

    # __init__ can't be async
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


    async def insert(self, user_id: int, time_difference: int, server_id: int):
        sql_command = """
        INSERT INTO stats (userID, serverID, time) 
        VALUES (?, ?, ?) 
        ON CONFLICT(userID, serverID) 
        DO UPDATE SET time = time + ?;
        """
        try:
            if self.conn is not None:
                await self.conn.execute(sql_command, (user_id, server_id, time_difference, time_difference))
                await self.conn.commit()
            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
        except aiosqlite.Error as error:
            print(f"Error inserting data: {error}")


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
                pipe.hset(str(server_ids[j]), str(user_ids[j]), str(time_differences[j])) # type: ignore
            await pipe.execute() # type: ignore

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        await log_info_to_channel(1377200295389565020,f"`bulk_insert` completed in {elapsed_ms:.3f}ms")



    async def get_user_time(self, user_id: int, server_id: int) -> Optional[int]:
        try:
            if self.conn is not None:
                async with self.conn.execute(
                    "SELECT time FROM stats WHERE userID = ? AND serverID = ?",
                    (user_id, server_id)
                ) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else 0
            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
                return None
        except aiosqlite.Error as error:
            print(f"Error fetching time: {error}")
            return None
        
    async def get_user_time_and_position(self, user_id: int, server_id: int) -> tuple[int, Optional[int]]:
        try:
            if self.conn is not None:
                async with self.conn.execute("""
                    WITH leaderboard AS (
                        SELECT 
                            userID, 
                            time,
                            ROW_NUMBER() OVER (ORDER BY time DESC) AS position
                        FROM stats
                        WHERE serverID = ?
                    )
                    SELECT 
                        time,
                        position
                    FROM leaderboard
                    WHERE userID = ?
                """, (server_id, user_id)) as cursor:
                    result = await cursor.fetchone()
                    return (result[0], result[1]) if result else (0, None)
            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
                return (0, None)
        except aiosqlite.Error as error:
            print(f"Error fetching time and position: {error}")
            return (0, None)
        

    get_leaderboard_members_and_time_from_database_cache = TTLCache(maxsize=500, ttl=60 * 60 * 1) # type: ignore
    @cached(get_leaderboard_members_and_time_from_database_cache) # type: ignore
    async def get_leaderboard_members_and_time_from_database(self, guild_id: int) -> tuple[list[int], list[int]]:
        users: List[int] = []
        times: List[int] = []
        
        try:
            if self.conn is not None:
                async with self.conn.execute(
                    "SELECT userID, time FROM stats WHERE serverID = ? ORDER BY time DESC LIMIT 500",
                    (guild_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    
                    for row in rows:
                        user_id = row[0]
                        time = row[1]

                        users.append(user_id)
                        times.append(time)
            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
                        
        except aiosqlite.Error as e:
            print(f"Database error: {e}")
            
        return users, times
    

    async def reset_all_database(self, guild_id: int) -> None:
        sql_command = """
        DELETE FROM stats WHERE serverID = ?;
        """
        try:
            if self.conn is not None:
                await self.conn.execute(sql_command, (guild_id,))
                await self.conn.commit()
            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
        except aiosqlite.Error as error:
            print(f"Error inserting data: {error}")

    async def reset_specific_user_database(self, guild_id: int, user_id: int) -> None:
        sql_command = """
        DELETE FROM stats WHERE serverID = ? AND userID = ?;
        """
        try:
            if self.conn is not None:
                await self.conn.execute(sql_command, (guild_id,user_id))
                await self.conn.commit()
            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
        except aiosqlite.Error as error:
            print(f"Error inserting data: {error}")
