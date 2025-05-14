class User:
    def __init__(self, user_id: int, guild_id: int, current_time_seconds: int):
        self._user_id = user_id
        self._guild_id = guild_id
        self._joined_time = current_time_seconds

    def get_user_id(self) -> int:
        return self._user_id
    
    def get_guild_id(self) -> int:
        return self._guild_id

    def get_joined_time(self) -> int:
        return self._joined_time
    
    def set_joined_time(self, new_time: int) -> None:
        self._joined_time = new_time