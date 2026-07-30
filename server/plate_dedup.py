from __future__ import annotations

import json
import os
from typing import Optional, Set


class AlprEventDeduper:
    """Prevent repeated ALPR payloads for the same detection event from being recorded twice."""

    def __init__(self, parsed_output_file: Optional[str] = None):
        self._processed_event_keys: Set[str] = set()
        self.parsed_output_file = parsed_output_file

        if self.parsed_output_file and os.path.exists(self.parsed_output_file):
            self._load_existing_keys()

    def _load_existing_keys(self) -> None:
        try:
            with open(self.parsed_output_file, 'r', encoding='utf-8') as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    event_key = payload.get('event_key')
                    if event_key:
                        self._processed_event_keys.add(event_key)
        except Exception:
            self._processed_event_keys = set()

    def _event_key(self, data: dict) -> Optional[str]:
        best_uuid = data.get('best_uuid')
        if best_uuid:
            return f"uuid:{best_uuid}"

        best_plate = data.get('best_plate') or {}
        plate = (best_plate.get('plate') or '').upper()
        region = (best_plate.get('region') or '').upper()
        camera_id = data.get('camera_id')
        epoch_start = data.get('epoch_start')
        epoch_end = data.get('epoch_end')

        if not any([plate, region, camera_id, epoch_start, epoch_end]):
            return None

        return f"fallback:{epoch_start}:{epoch_end}:{camera_id}:{plate}:{region}"

    def should_record(self, data: dict) -> bool:
        event_key = self._event_key(data)
        if not event_key:
            return True

        if event_key in self._processed_event_keys:
            return False

        self._processed_event_keys.add(event_key)
        return True

    def mark_recorded(self, data: dict, parsed_record: dict) -> None:
        event_key = self._event_key(data)
        if event_key:
            parsed_record['event_key'] = event_key
            self._processed_event_keys.add(event_key)
