from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
import asyncio


@dataclass
class Event:
    type: str
    payload: Dict[str, Any]


class EventBus:
    def __init__(self):
        self.subscribers: List[Callable[[Event], None]] = []
        self.loop = None

    def subscribe(self, callback: Callable[[Event], None]):
        self.subscribers.append(callback)

    def publish(self, event_type: str, **kwargs):
        event = Event(type=event_type, payload=kwargs)
        for callback in self.subscribers:
            # If callback is a coroutine, schedule it
            if asyncio.iscoroutinefunction(callback):
                # We need a running loop to schedule
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(callback(event))
                except RuntimeError:
                    # No running loop, can't schedule async callback
                    pass
            else:
                callback(event)


# Global event bus
event_bus = EventBus()
