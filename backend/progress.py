from threading import Lock

_events: dict = {}
_lock = Lock()

def init_session(session_id: str):
    with _lock:
        _events[session_id] = []

def emit(session_id: str, agent: str, status: str, message: str = "", short: str = ""):
    with _lock:
        if session_id in _events:
            _events[session_id].append({
                "agent": agent,
                "status": status,
                "message": message,
                "short": short or message[:25],
            })

def mark_done(session_id: str):
    with _lock:
        if session_id in _events:
            _events[session_id].append({"done": True})

def get_events(session_id: str, from_index: int = 0):
    with _lock:
        return list(_events.get(session_id, [])[from_index:])

def cleanup(session_id: str):
    with _lock:
        _events.pop(session_id, None)
