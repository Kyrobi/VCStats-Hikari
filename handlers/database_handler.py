import sqlite3
import os
from typing import List, Optional

class DatabaseHandler:

    DATABASE_FILE_NAME = "database.db"

    def __init__(self):
        if not os.path.exists(self.DATABASE_FILE_NAME):
            try:
                with open(self.DATABASE_FILE_NAME, "w"):
                    pass
                print(f"File created: {self.DATABASE_FILE_NAME}")
            except IOError as e:
                print(f"An error occurred while creating the file: {e}")
        # else:
        #     print("File already exists.")
        
        self.create_new_table()

    def create_new_table(self):
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
            with sqlite3.connect(self.DATABASE_FILE_NAME) as conn:
                conn.execute(create_stats_table)
        except sqlite3.Error as error:
            print(f"Database error: {error}")

    @staticmethod
    async def insert(user_id: int, time_difference: int, server_id: int):
        sql_command = """
        INSERT INTO stats (userID, serverID, time) 
        VALUES (?, ?, ?) 
        ON CONFLICT(userID, serverID) 
        DO UPDATE SET time = time + ?;
        """
        try:
            with sqlite3.connect(DatabaseHandler.DATABASE_FILE_NAME) as conn:
                conn.execute(sql_command, (user_id, server_id, time_difference, time_difference))
        except sqlite3.Error as error:
            print(f"Error inserting data: {error}")

    @staticmethod
    async def bulk_insert(user_ids: List[int], time_differences: List[int], server_ids: List[int]):
        try:
            with sqlite3.connect(DatabaseHandler.DATABASE_FILE_NAME) as conn:
                for user_id, time, server_id in zip(user_ids, time_differences, server_ids):
                    conn.execute("""
                    INSERT INTO stats (userID, serverID, time) 
                    VALUES (?, ?, ?) 
                    ON CONFLICT(userID, serverID) 
                    DO UPDATE SET time = time + ?;
                    """, (user_id, server_id, time, time))
        except sqlite3.Error as error:
            print(f"Error performing bulk insert: {error}")

    @staticmethod
    async def get_user_time(user_id: int, server_id: int) -> int:
        try:
            with sqlite3.connect(DatabaseHandler.DATABASE_FILE_NAME) as conn:
                cursor = conn.execute(
                    "SELECT time FROM stats WHERE userID = ? AND serverID = ?",
                    (user_id, server_id)
                )
                result = cursor.fetchone()
                return result[0] if result else 0
        except sqlite3.Error as error:
            print(f"Error fetching time: {error}")
            return 0
    
    @staticmethod
    async def get_player_leaderboard_position(guild_id: int, user_id: int) -> Optional[int]:
        try:
            with sqlite3.connect(DatabaseHandler.DATABASE_FILE_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    WITH getServerMembers AS (
                    SELECT userID, time,
                            ROW_NUMBER() OVER (ORDER BY time DESC) AS row_num
                    FROM stats
                    WHERE serverID = ?
                    )
                    SELECT row_num
                    FROM getServerMembers
                    WHERE userID = ?;
                """, (guild_id, user_id))
                
                result = cursor.fetchone()
                print(f"DB result: {result[0]}")
                return result[0] if result else None
            
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
            return None
        
    @staticmethod
    async def get_user_time_and_position(user_id: int, server_id: int) -> tuple[int, Optional[int]]:
        try:
            with sqlite3.connect(DatabaseHandler.DATABASE_FILE_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("""
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
                """, (server_id, user_id))
                
                result = cursor.fetchone()
                print(f"Result[0] = {result[0]}, result[1] = {result[1]}")
                return (result[0], result[1]) if result else (0, None)
                
        except sqlite3.Error as error:
            print(f"Error fetching time and position: {error}")
            return (0, None)
