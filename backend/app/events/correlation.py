"""Event correlation with HTTP trace_id (E-00-S07 prep, TDS-005).

Business events (EventType) will carry the same trace_id as the originating HTTP
request or orchestration refresh_id lineage. Downstream epics attach trace_id to
audit and event payloads without changing this module.
"""

from __future__ import annotations

TRACE_ID_LOG_FIELD = "trace_id"
EVENT_TYPE_LOG_FIELD = "event_type"
