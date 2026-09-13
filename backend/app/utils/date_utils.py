import datetime
from typing import Optional, Union

def format_relative_time(dt: Optional[Union[datetime.datetime, str]]) -> str:
    """
    Returns a human-readable relative time string such as:
    - "Just now"
    - "5 mins ago"
    - "2 hours ago"
    - "Yesterday"
    - "9 days ago"
    - "2 months ago"
    """
    if not dt:
        return ""
    
    if isinstance(dt, str):
        try:
            # Handle ISO formatted strings
            dt = datetime.datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return ""

    # Ensure timezone awareness
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    
    now = datetime.datetime.now(datetime.timezone.utc)
    diff = now - dt
    total_seconds = int(diff.total_seconds())

    if total_seconds < 0:
        return "Just now"
    if total_seconds < 60:
        return "Just now"
    
    minutes = total_seconds // 60
    if minutes < 60:
        return "1 min ago" if minutes == 1 else f"{minutes} mins ago"
    
    hours = minutes // 60
    if hours < 24:
        return "1 hour ago" if hours == 1 else f"{hours} hours ago"
    
    days = hours // 24
    if days == 1:
        return "Yesterday"
    if days < 30:
        return f"{days} days ago"
    
    months = days // 30
    if months < 12:
        return "1 month ago" if months == 1 else f"{months} months ago"
    
    years = days // 365
    return "1 year ago" if years == 1 else f"{years} years ago"

def format_friendly_date(dt: Optional[Union[datetime.datetime, str]]) -> str:
    """
    Formats a datetime into a clean display date like "Sep 03, 2026".
    """
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return dt[:10]
    return dt.strftime("%b %d, %Y")
