"""
This module contains FinamProvider which automatically load data from finam.ru web site.
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path
import re

from .base import DataProvider, InvalidDataFormatError, Ticker, \
  DataNotFoundError, DataObtainError, Bar
from .common import requests_retry_session, Singleton
from .log import logger

__all__ = ["FinamProvider"]

########################################################################
class FinamSymbols(object, metaclass=Singleton):
  """
  Symbols dictionary will be download once.
  """
  #----------------------------------------------------------------------
  def __init__(self):
    logger.debug("FinamSymbols.init")
    # Download once
    try:
      self.resolutions = None
      self.aEmitentCodes, self.aEmitentIds, self.aEmitentMarkets = None,None,None
      with requests_retry_session() as sess:
        response = sess.get('https://www.finam.ru/cache/icharts/icharts.js',)
        for it in response.iter_lines():
          line = it.decode("utf-8", "ignore")
          m = re.match(r"var\s+(\w+)\s*=\s*new\s*Array\s*(.*)", line)
          if m is None:
            m = re.match(r"var\s+(\w+)\s*=\s*\s*\[(.*)", line)
          if m is not None:
            varname = m.group(1)
            varval = m.group(2)
            if varname == "aEmitentIds":
              self.aEmitentIds = self._parsetuple(varval.replace("'", ""))
            elif varname == "aEmitentCodes":
              self.aEmitentCodes = self._parsetuple(varval.replace("'", ""))
            elif varname == "aEmitentMarkets":
              self.aEmitentMarkets = self._parsetuple(varval.replace("'", ""))
       
        self.resolutions = {
          timedelta(minutes=1):  2,
          timedelta(minutes=5):  3,
          timedelta(minutes=10): 4,
          timedelta(minutes=15): 5,
          timedelta(minutes=30): 6,
          timedelta(hours=1):    7,
          timedelta(days=1):     8,
          timedelta(weeks=1):    9,
        }
    except Exception as e:
      raise DataObtainError("FinamSymbols - Finam symbols dictionary", e);
  #----------------------------------------------------------------------
  @staticmethod
  def _parsetuple(s, trans=str):
    # Don't use 'eval'. Cause it's dangerous!
    return [trans(val) for val in (s.strip(" \t()")).split(",")]

########################################################################
class FinamProvider(DataProvider):
  """
  Loads data from finam.ru.
  """
  __slots__ = ()
  def __init__(self):
    FinamSymbols()
  #----------------------------------------------------------------------
  def __getattr__(self, name):
    """transfer attr ref"""
    try:
      return getattr(FinamSymbols(), name)
    except AttributeError:
      raise AttributeError("object has no attribute '{0}'".format(name))
  #----------------------------------------------------------------------
  def _generator(self, ticker, lines, start, end, period):
    """ Wrap responsed data with CSV parser and return elements in the order. """
    for datalist in csv.reader(lines.splitlines(), delimiter=';', quotechar='"'):
      try:
        d, t, o, h, l, c, v = datalist
        o, h, l, c, v = float(o), float(h), float(l), float(c), int(v)
        stamp = datetime.strptime(d + t, "%Y%m%d%H%M%S")
      except ValueError:
        raise InvalidDataFormatError(ticker, str(datalist))
      if stamp < start:
        continue
      elif stamp > end:
        return# raise StopIteration
      yield Bar(ticker, stamp, period, o, h, l, c, v)
  #----------------------------------------------------------------------
  def find(self, query):
    result = []
    if self.aEmitentCodes == None:
      return result
    for i, code in enumerate(self.aEmitentCodes):
      if query.lower() == code.lower():
        result.append(Ticker(self, code, market=self.aEmitentMarkets[i], id=self.aEmitentIds[i]))
    if not result:
      raise DataNotFoundError(query)
    return result
  #----------------------------------------------------------------------
  def save_codes(self, file_name):
    with Path(file_name).open() as f:
      for i, code in enumerate(self.aEmitentCodes):
        f.write('{0};{1};{2};{3}\n'.format(code, self.aEmitentIds[i], self.aEmitentNames[i], self.aEmitentMarkets[i]))
  #----------------------------------------------------------------------
  def bars(self, ticker, start, end, period):
    """
    Finds ticker in the finam's database stored in export.js file which parsed before
    and download data from a remote service
    """
    fmt = "%y%m%d"  # Date format of request
    dfrom = start.date()
    dto = end.date()
    fname = "{0}_{1}_{2}".format(ticker.symbol, dfrom.strftime(fmt), dto.strftime(fmt))
    fext = ".csv"
    try:
      p = self.resolutions[period]
    except KeyError:
      raise ValueError("Illegal value of period.")
    rdict = dict(d='d',
                 market=ticker.data['market'],
                 cn=ticker.symbol,
                 em=ticker.data['id'],
                 p=p,
                 yf=dfrom.year,
                 mf=dfrom.month - 1,  # In service month's numbers starts from 0
                 df=dfrom.day,
                 yt=dto.year,
                 mt=dto.month - 1,
                 dt=dto.day,
                 dtf=1,  # Equals %Y%m%d
                 tmf=1,  # Equals %M%H%S
                 MSOR=1,  # end of candles
                 sep=3,  # Semicolon ';'
                 sep2=1,  # Not set a digit position delimiter
                 datf=5,  # Format: DATE, TIME, OPEN, HIGH, LOW, CLOSE, VOL
                 f=fname,
                 e=fext,
                 at=0,  # No header
                 )
    
    # http://export.finam.ru/SBER_080521_080531.csv?d=d&market=517&em=419750&df=21&mf=4&yf=2008&dt=31&mt=4&yt=2008&p=2&f=SBER_080521_080531&e=.csv&cn=SBER&dtf=1&tmf=1&MSOR=1&sep=3&sep2=1&datf=5&at=0
    # url = ("http://195.128.78.52/{f}{e}?" + 
    url = ("http://export.finam.ru/{f}{e}?" + 
          "d=d&market={market}&em={em}&df={df}&" + 
          "mf={mf}&yf={yf}&dt={dt}&mt={mt}&yt={yt}&" + 
          "p={p}&f={f}&e={e}&cn={cn}&dtf={dtf}&tmf={tmf}&" + 
          "MSOR={MSOR}&sep={sep}&sep2={sep2}&datf={datf}&at={at}").format(**rdict)
    try:
      with requests_retry_session()as sess:
        response = sess.get(url, headers = {'Referer': "http://www.finam.ru/analysis/export/default.asp"})
        decoded = response.content.decode('utf-8', "ignore")
        return self._generator(ticker, decoded, start, end, period) # Return generator which parses data
    except Exception as e:
      raise DataObtainError(ticker, e)
    else:
      logger.debug('request OK: {0}'.format(response.status_code))
