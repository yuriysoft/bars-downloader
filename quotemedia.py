"""
This module contains QuotemediaProvider which automatically load data from quotemedia.com web site.
Daily only.
"""

import csv
from datetime import datetime, timedelta

from .base import DataProvider, InvalidDataFormatError, Bar, \
  DataNotFoundError, Ticker, DataObtainError
from .common import is_float, requests_retry_session
from .log import logger


__all__ = ["QuotemediaProvider"]

########################################################################
class QuotemediaProvider(DataProvider):
  """
  Loads data from resource.
  """
  __slots__ = ()
  #----------------------------------------------------------------------
  def _generator(self, ticker, lines, start, end, period):
    """ Wrap responsed data with CSV parser and return elements in the order. """
    for datalist in csv.reader(reversed(lines.splitlines()), delimiter=',', quotechar='"'):
      try:
        # date,open,high,low,close,volume,changed,changep,adjclose,tradeval,tradevol
        d, o, h, l, c, v = datalist[:6]
        if not is_float(o):
          continue
        o, h, l, c, v = float(o), float(h), float(l), float(c), int(v)
        stamp = datetime.strptime(d, "%Y-%m-%d")
      except ValueError:
        raise InvalidDataFormatError(ticker, str(datalist))
      if stamp < start:
        continue
      elif stamp >= end:
        return #raise StopIteration
      yield Bar(ticker, stamp, period, o, h, l, c, v)
  #----------------------------------------------------------------------
  def find(self, query):
    if not query:
      raise DataNotFoundError("Not found tickers for " + query)
    return [Ticker(self, query.lower())]
  #----------------------------------------------------------------------
  def bars(self, ticker, start, end, period):
    """Download ticker' data from a remote service"""
    period = timedelta(days=1) # only days can used
    dfrom = start.date()
    dto = end.date()
    rdict = dict(
                 symbol=ticker.symbol,
                 startYear=dfrom.year,
                 startMonth=dfrom.month - 1,  # In service month's numbers starts from 0
                 startDay=dfrom.day,
                 endYear=dto.year,
                 endMonth=dto.month - 1,
                 endDay=dto.day,
                 )
    
    # https://app.quotemedia.com/quotetools/getHistoryDownload.csv?&webmasterId=501
    # &startDay=17&startMonth=1&startYear=2017&endDay=27
    # &endMonth=3&endYear=2017&isRanged=false
    # &symbol=^IN:US
    url = ("https://app.quotemedia.com/quotetools/getHistoryDownload.csv?" + 
          "webmasterId=501&startDay={startDay}&" +
          "startMonth={startMonth}&startYear={startYear}&" +
          "endDay={endDay}&endMonth={endMonth}&endYear={endYear}&" +
          "isRanged=false&symbol={symbol}").format(**rdict)
    try:
      response = requests_retry_session().get(url)#, headers = {'Referer': "http://www.finam.ru/analysis/export/default.asp"})
      decoded = response.content.decode('utf-8', "ignore")
      return self._generator(ticker, decoded, start, end, period) # Return generator which parses data
    except Exception as e:
      raise DataObtainError(ticker, e)
    else:
      logger.debug('request OK: {0}'.format(response.status_code))
