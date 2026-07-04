import asyncio
from dataclasses import dataclass, field


@dataclass
class BargeInEvents:
    bot_speaking: asyncio.Event = field(default_factory=asyncio.Event)
    interrupt: asyncio.Event = field(default_factory=asyncio.Event)
