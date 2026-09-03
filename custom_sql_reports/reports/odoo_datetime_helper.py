from dateutil import parser
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, time, date


def set_local_time(dt, tz, hour, minute, second):
    """
    convert datetime string in utc to local time with hour, minute, second and return respective utc time
    dt - datetime string
    tz - timezone string (e.g. 'Asia/Yangon')
    """
    obj = parser.parse(dt)
    # set naive datetime to utc. this isn't needed in python3.6. but server is python3.5
    obj = pytz.utc.localize(obj)
    obj = obj.astimezone(pytz.timezone(tz))
    obj = obj.replace(hour=hour, minute=minute, second=second)
    obj = obj.astimezone(pytz.utc)
    obj = datetime.strftime(obj, DEFAULT_SERVER_DATETIME_FORMAT)
    return obj

def local_time(dt, tz):
    """
    convert utc time to tz time str
    dt - datetime object
    tz - timezone string (e.g. 'Asia/Yangon')
    """
    # set naive datetime to utc. this isn't needed in python3.6. but server is python3.5
    datetime_obj = pytz.utc.localize(dt)
    local_tz = pytz.timezone(tz)
    local_datetime = datetime_obj.astimezone(local_tz)
    return datetime.strftime(local_datetime, DEFAULT_SERVER_DATETIME_FORMAT)


def local_date_range_to_utc(start_date, end_date, tz_name='Asia/Yangon'):
    """
    Convert a local calendar date range to naive UTC datetimes for create_date filters.

    Example (Asia/Yangon, UTC+6:30):
      31 Jul local 00:00:00 -> 30 Jul 17:30:00 UTC
      31 Jul local 23:59:59 -> 31 Jul 17:29:59 UTC
    """
    if not isinstance(start_date, date) or not isinstance(end_date, date):
        raise ValueError('start_date and end_date must be date objects')

    local_tz = pytz.timezone(tz_name or 'Asia/Yangon')
    start_local = local_tz.localize(datetime.combine(start_date, time.min))
    end_local = local_tz.localize(datetime.combine(end_date, time.max))
    start_utc = start_local.astimezone(pytz.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(pytz.utc).replace(tzinfo=None)
    return start_utc, end_utc
