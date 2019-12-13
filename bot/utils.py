from datetime import datetime, timedelta

def localize_time(utctime: datetime, offset: int = 0, timezone: str = None):
    if offset:
        if offset >= 0:
            return utctime + timedelta(hours=offset)
        elif offset < 0:
            return utctime - timedelta(hours=abs(offset))
    elif timezone:
        offset = int(timezone[3:])
        if offset >= 0:
            return utctime + timedelta(hours=offset)
        elif offset < 0:
            return utctime - timedelta(hours=abs(offset))
    return utctime
