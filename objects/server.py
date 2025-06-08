from typing import Optional


class Server:
    def __init__(self, logging_channel: Optional[int]):
        self._logging_channel = logging_channel

    def set_logging_channel_id(self, channel_id: int) -> None:
        self._logging_channel = channel_id
    
    def get_logging_channel_id(self) -> Optional[int]:
        return self._logging_channel
