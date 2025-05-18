import aiosqlite
import os
from typing import List, Optional

DATABASE_NOT_CONNECTED_MESSAGE = "Database is not connected..."

class DatabaseHandler:

    DATABASE_FILE_NAME = "database.db"

    # __init__ can't be async
    def __init__(self):
        self.conn: Optional[aiosqlite.Connection] = None

    async def init(self):
        if not os.path.exists(self.DATABASE_FILE_NAME):
            try:
                with open(self.DATABASE_FILE_NAME, "w"):
                    pass
                print(f"File created: {self.DATABASE_FILE_NAME}")
            except IOError as e:
                print(f"An error occurred while creating the file: {e}")
        # else:
        #     print("File already exists.")
        
        self.conn = await aiosqlite.connect(self.DATABASE_FILE_NAME)
        await self.conn.execute("PRAGMA journal_mode=WAL;")  # Improves concurrency
        await self.conn.execute("PRAGMA synchronous=NORMAL;")
        await self.conn.commit()
        await self.create_new_table()

    async def uninitialize(self):
        if self.conn:
            try:
                await self.conn.commit()
                await self.conn.close()
                print("Database connection closed.")
            except aiosqlite.Error as e:
                print(f"Error closing the database connection: {e}")
            finally:
                self.conn = None

    async def create_new_table(self):
        create_stats_table = """
        CREATE TABLE IF NOT EXISTS stats (
            userID INTEGER NOT NULL DEFAULT 0, 
            time INTEGER NOT NULL DEFAULT 0, 
            serverID INTEGER NOT NULL DEFAULT 0, 
            PRIMARY KEY (userID, serverID), 
            UNIQUE (userID, serverID)
        );
        """
        try:
            if self.conn is not None:
                await self.conn.execute(create_stats_table)
                await self.conn.commit()
            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
                exit()
        except aiosqlite.Error as error:
            print(f"Database error: {error}")


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


    async def bulk_insert(self, user_ids: List[int], time_differences: List[int], server_ids: List[int]):
        try:
            if self.conn is not None:
                for user_id, time, server_id in zip(user_ids, time_differences, server_ids):
                    await self.conn.execute("""
                    INSERT INTO stats (userID, serverID, time) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(userID, serverID) 
                    DO UPDATE SET time = time + ?;
                    """, (user_id, server_id, time, time))
                await self.conn.commit()
            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
        except aiosqlite.Error as error:
            print(f"Error performing bulk insert: {error}")


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
        UPDATE stats SET time = 0 WHERE serverID = ? AND userID = ?;
        """
        try:
            if self.conn is not None:
                await self.conn.execute(sql_command, (guild_id,user_id))
                await self.conn.commit()
            else:
                print(DATABASE_NOT_CONNECTED_MESSAGE)
        except aiosqlite.Error as error:
            print(f"Error inserting data: {error}")
