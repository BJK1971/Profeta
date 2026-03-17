import datetime


def encode_datetime(o):
    """Encodes a datetime object to a string in ISO 8601 format.
    This function is used for JSON serialization of datetime objects.

    :param o: the object to be serialized
    :raises TypeError: if the object is not a JSON-serializable type
    :return: a string representation of the datetime object in ISO 8601 format
    """
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")
