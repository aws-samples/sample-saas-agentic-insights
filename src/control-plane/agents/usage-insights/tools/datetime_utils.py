"""
Datetime Utilities for Usage Insights Tools

Provides timezone-aware datetime handling to avoid comparison errors.
"""

from datetime import datetime, timezone


def utcnow():
    """
    Get current UTC time as timezone-aware datetime.
    
    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)


def parse_iso_datetime(iso_string: str) -> datetime:
    """
    Parse ISO 8601 datetime string to timezone-aware datetime.
    
    Args:
        iso_string: ISO 8601 formatted datetime string (e.g., "2025-10-23T10:30:00Z")
    
    Returns:
        datetime: Timezone-aware datetime object
    """
    # Handle 'Z' suffix (UTC indicator)
    if iso_string.endswith('Z'):
        iso_string = iso_string[:-1] + '+00:00'
    
    # Parse to datetime
    dt = datetime.fromisoformat(iso_string)
    
    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt


def to_iso_string(dt: datetime) -> str:
    """
    Convert datetime to ISO 8601 string with 'Z' suffix.
    
    Args:
        dt: Datetime object (timezone-aware or naive)
    
    Returns:
        str: ISO 8601 formatted string with 'Z' suffix
    """
    # Ensure timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Convert to UTC if not already
    dt_utc = dt.astimezone(timezone.utc)
    
    # Format as ISO string with 'Z' suffix
    return dt_utc.isoformat().replace('+00:00', 'Z')
