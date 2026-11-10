from collections import defaultdict

from ..domain.event import Event
from ..domain.video_part import VideoPart


def build_events(parts: list[VideoPart]) -> list[Event]:
    grouped = defaultdict(list)
    for part in parts:
        grouped[part.source_event_id].append(part)
    events = []
    for eid, items in grouped.items():
        items.sort(key=lambda p: p.part_number)
        first = items[0]
        events.append(
            Event(
                eid, first.station_name, first.event_start_time, first.event_detection_time, items
            )
        )
    return sorted(events, key=lambda e: e.event_start_time)
