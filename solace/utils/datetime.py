from datetime import datetime
from typing import Tuple

FMT = "%Y-%m-%d %H:%M"


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, FMT)


def format_timestamp(dt: datetime) -> str:
    return dt.strftime(FMT)


def request_timestamp() -> str:
    """Prompt user for a timestamp and validate."""
    while True:
        ts = input("Enter date and time (YYYY-MM-DD HH:MM): ").strip()
        try:
            parse_timestamp(ts)
            return ts
        except Exception:
            print("Invalid timestamp. Please try again.")


def prompt_timestamp() -> str:
    """Ask whether to use the current time or request a timestamp."""
    use_now = input("Use current date/time? [Y/n]: ").strip().lower()
    if not use_now or use_now.startswith("y"):
        return datetime.now().strftime(FMT)
    return request_timestamp()


def ts_to_filename(ts: str) -> str:
    return ts.replace(":", "-").replace(" ", "_")
