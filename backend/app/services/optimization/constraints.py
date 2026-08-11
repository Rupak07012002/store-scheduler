from datetime import date, datetime, time


def duration_minutes(start: time, end: time) -> int:
    return int((datetime.combine(date.min, end) - datetime.combine(date.min, start)).total_seconds() // 60)


def rest_gap_hours(prev_date: date, prev_end: time, next_date: date, next_start: time) -> float:
    end_dt = datetime.combine(prev_date, prev_end)
    start_dt = datetime.combine(next_date, next_start)
    return (start_dt - end_dt).total_seconds() / 3600
