"""
Common types for providers.
"""

from datetime import datetime, date, time, timedelta
from functools import partial
from inspect import signature


########################################################################
class DataError(Exception):
  """ Base class for different classes of exceptions raising in providers. """

  #----------------------------------------------------------------------
  def __init__(self, hid):
    self.hid = hid


########################################################################
class DataNotFoundError(DataError):
  """ Raise it when data not exists for the provider. """

  #----------------------------------------------------------------------
  def __str__(self):
    return "Can't find any data for ({0}). Try other id.".format(self.hid)

  #----------------------------------------------------------------------
  def __repr__(self):
    return str(self)


########################################################################
class DataObtainError(DataError):
  """ Raise it when data was found but can't be loaded. """

  #----------------------------------------------------------------------
  def __init__(self, hid, exc):
    super(DataObtainError, self).__init__(hid)
    self.base = exc

  #----------------------------------------------------------------------
  def __str__(self):
    return "Can't fetch data for ({0}). Raised:\n{1}".format(self.hid, self.base)

  #----------------------------------------------------------------------
  def __repr__(self):
    return str(self)

  
########################################################################
class InvalidDataFormatError(DataError):
  """ Raise it when data not exists for the provider."""

  #----------------------------------------------------------------------
  def __init__(self, hid, sample):
    super(InvalidDataFormatError, self).__init__(hid)
    self.sample = sample

  #----------------------------------------------------------------------
  def __str__(self):
    return "Invalid data for ({0}): ({1})".format(self.hid, self.sample)

  #----------------------------------------------------------------------
  def __repr__(self):
    return str(self)


#######################################################################
class Ticker(object):
  """ Stock symbol."""
  __slots__ = ("provider", "symbol", "data")

  #----------------------------------------------------------------------
  def __init__(self, provider, symbol, **data):
    self.provider = provider      
    self.symbol = symbol
    self.data = data

  #----------------------------------------------------------------------
  def __getattr__(self, name):
    attr = getattr(self.provider, name)
    try:
      if 'ticker' in signature(attr).parameters:
        attr = partial(attr, self)
    except TypeError:
      pass  # Not a callable or have not args
    return attr

  #----------------------------------------------------------------------
  def __repr__(self):
    return "Ticker:({0};{1};{2})".format(self.provider.__class__.__name__, self.symbol, self.data)


#######################################################################
class Bar(object):
  """
  Represents classical bar with open, high, low and close prices
  during fixed interval inclusive data from stamp to till.
  """
  __slots__ = ("ticker", "timestamp", "period", "open", "high", "low", "close", "volume", "interest")

  #----------------------------------------------------------------------
  def __init__(self,
               ticker,
               timestamp,
               period,
               open_,
               high,
               low,
               close,
               volume=None,
               interest=None,):
    self.ticker = ticker
    self.timestamp = timestamp
    self.period = Bar.timedelta2str(period)
    self.open = open_
    self.high = high
    self.low = low
    self.close = close
    self.volume = volume
    self.interest = interest

  #----------------------------------------------------------------------
  @staticmethod
  def timedelta2str(period):
    return 'D' if period == timedelta(days=1) else \
           'W' if period == timedelta(weeks=1) else \
           'H' if period == timedelta(hours=1) else \
           '{0}'.format(int(period.total_seconds() / 60))

  #----------------------------------------------------------------------
  @staticmethod
  def str2timedelta(v):
    """
    Creates timedelta from parameter;
       numeric value to minutes
       'd' to day
       'w' to week
       'h' to hour
    """
    if type(v) is int:
      return timedelta(minutes=v)
    try:
      return timedelta(days=1) if v.lower() in ("d", "day") else\
             timedelta(weeks=1) if v.lower() in ("w", "week") else\
             timedelta(hours=1) if v.lower() in ("h", "hour") else\
             timedelta(minutes=int(v))
    except ValueError:
      raise InvalidDataFormatError(v, 'TIMEFRAME can be only "D"/"W"/"H" or numeric value, for ex."5"'.format(v))

  #----------------------------------------------------------------------
  def __eq__(self, other):
    """Checks equals of all fields even if they are equals None."""
    if not isinstance(other, Bar):
      return False
    if self.ticker != other.ticker:
      return False
    if self.timestamp != other.timestamp:
      return False
    if self.period != other.period:
      return False
    if self.open != other.open:
      return False
    if self.high != other.high:
      return False
    if self.low != other.low:
      return False
    if self.close != other.close:
      return False
    if self.volume != other.volume:
      return False
    if self.interest != other.interest:
      return False
    return True

  #----------------------------------------------------------------------
  def __ne__(self, other):
    return not self.__eq__(other)

  #----------------------------------------------------------------------
  def __repr__(self):
    return "{ticker.symbol};{timestamp};{period};{open};{high};{low};{close};{volume};{interest}".format(**{a: self.__getattribute__(a) for a in self.__slots__})    


########################################################################
class DataProvider(object):
  """
  Base class for extra providers.
  Derived provider should contains functions:
    1. def bars(self, ticker, start, end, period):
      return Bar list
    2. def find(self, query):
      return Ticker list
  """
  __slots__ = ()
  #----------------------------------------------------------------------
  def __getitem__(self, key):
    values = self.find(key)
    if values:
      return values[-1]
    else:
      raise KeyError("Not found ticker: " + str(key))

  #----------------------------------------------------------------------
  def __contains__(self, key):
    return key in self.find(key)

  #----------------------------------------------------------------------
  def find(self, query):
    """ Method returns only available string keys for identify queried ticker. """
    raise NotImplementedError("Method 'find' not implemented.")        

  #----------------------------------------------------------------------
  def get_bars(self, ticker, delta, start=1, end=None):
    """ Creates a generator which return requested data in minutely bars."""
    if not end:
      # Expects trader get new data in the next morning not immediate right after trading session
      end = datetime.now()  # Because providers will return data until but exclude end
    if type(end) is date:
      end = datetime.combine(end, time())  # Datetime flooring
    elif type(end) is time:
      end = datetime.combine(date.today(), end)  # Convert to today's time
    if type(end) is datetime:
      end = end.replace(second=0, microsecond=0)  # Datetime flooring
    else:
      raise TypeError("Unknown type ({0}) of a end datetime.".format(type(end)))
    
    if not start:
      start = date.today()  # From start of this day
    elif isinstance(start, int):
      start = end - delta  # Will be a datetime
    if type(start) is date:
      start = datetime.combine(start, time())  # Datetime flooring
    elif type(start) is time:
      start = datetime.combine(date.today(), start)  # Converts to today's time
    if type(start) is datetime:
      if start.second or start.microsecond:
        start += delta  # Increase for ceiling
      start = start.replace(second=0, microsecond=0)  # Datetime ceiling
    else:
      raise TypeError("Unknown type ({0}) of a start datetime.".format(type(start)))

    if start > end:
      raise ValueError("Start datetime is after end.")

    return self.bars(ticker, start, end, delta)

