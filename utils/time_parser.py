from datetime import datetime, timedelta

def _parse_when_to_dt(time_str: str) -> datetime:
    try:
        dt = datetime.strptime(time_str, "%I:%M %p")
    except ValueError:
        raise ValueError("Invalid time format. Use something like 7:00 PM.")

    now = datetime.now()

    dt = dt.replace(
        year=now.year,
        month=now.month,
        day=now.day
    )

    if dt < now:
        dt += timedelta(days=1)

    return dt