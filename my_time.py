import datetime


def get_now_time_string():
    # t = datetime.datetime.utcnow()
    t = datetime.datetime.now()
    return time_to_str(t)


def get_now_time_datetime():
    # t = datetime.datetime.utcnow()
    t = datetime.datetime.now()
    return t


def get_now_time_second():
    # t = datetime.datetime.utcnow()
    t = datetime.datetime.now()
    return time_to_second(t)


def time_to_str(date_time):
    year = date_time.year
    month = date_time.month
    day = date_time.day
    hour = date_time.hour
    minute = date_time.minute
    second = date_time.second
    microsecond = date_time.microsecond

    format_str = '%s/%s/%s %s:%s:%s:%s'
    args = (year, month, day, hour, minute, second, microsecond)

    res = format_str % args
    return res


def str_to_time(datetime_str):
    try:
        t = str.split(datetime_str, ' ')
        date = str.split(t[0], '/')
        tim = str.split(t[1], ':')
        year = int(date[0])
        month = int(date[1])
        day = int(date[2])
        hour = int(tim[0])
        minute = int(tim[1])
        second = int(tim[2])
        microsecond = int(tim[3])
        res = datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second,
                                microsecond=microsecond)
    except:
        res = datetime.datetime.min
    return res


def time_to_second(date_time):
    return (date_time - datetime.datetime.min).total_seconds()


def str_to_second(datetime_str):
    return time_to_second(str_to_time(datetime_str))


def second_to_time(second):
    return datetime.datetime.min + datetime.timedelta(seconds=second)


def second_to_str(second):
    return time_to_str(second_to_time(second))
