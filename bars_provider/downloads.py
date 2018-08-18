"""
Downloads historical data from remote resources defined in config.json
"""

from datetime import datetime, timedelta
import json
from pathlib import Path
from sched import scheduler
from time import sleep, time


from .base import DataObtainError, Bar
from .common import is_not_empty, str2bool
from .log import logger


__all__ = ["Downloads"]


#######################################################################
class Downloads(object):
  """
  Load config.json, Downloads historical data
  """
  #----------------------------------------------------------------------
  def __init__(self, file_name):
    self._load_cfg(file_name)
  #----------------------------------------------------------------------
  @staticmethod
  def save_default_cfg(file_name):
    default_json = """{
    "all":{
        "TIMEOUT":240,
        "TIMEFRAME":"15",
        "CHUNK_IN_DAYS":10,
        "DATETIME_START":"201611010000",
        "DATETIME_END":"201612010000",
        "APPEND_DATA":"yes"
    },
    "resources":{
        "bars_provider.finam":{"FinamProvider":["SPFB.SBRF", "SPFB.RTS"]},
        "bars_provider.quotemedia":{"QuotemediaProvider":["^IN"]}
    }
    }"""
    with open(file_name, 'w') as f_out:
      f_out.write(default_json)
  #----------------------------------------------------------------------
  def _load_cfg(self, file_name):
    with open(file_name) as f_json:
      data = json.load(f_json)
      self.DATETIME_START = datetime.strptime(data['all']['DATETIME_START'], "%Y%m%d%H%M")
      self.DATETIME_END = datetime.strptime(data['all']['DATETIME_END'], "%Y%m%d%H%M")
      self.APPEND_DATA = str2bool(data['all']['APPEND_DATA'])
      self.TIMEFRAME = Bar.str2timedelta(data['all']['TIMEFRAME'])
      self.TIMEOUT = data['all']['TIMEOUT']
      self.CHUNK_IN_DAYS = timedelta(days=data['all']['CHUNK_IN_DAYS'])
      self.RESOURCES = data['resources']
    logger.debug('_load_cfg(): OK')
  #----------------------------------------------------------------------
  @classmethod
  def _periodic(cls, sch, interval, action, actionargs=()):
    """ Infinite loop """
    sch.enter(interval, 1, cls._periodic,
                    (sch, interval, action, actionargs))
    action(*actionargs)
  #----------------------------------------------------------------------
  def startTimer(self):
    try:
      if self.TIMEOUT > 0:
        sch = scheduler(time, sleep)
        Downloads._periodic(sch, self.TIMEOUT * 60, self.download)
        sch.run()
      else:
        self.download()
    except KeyboardInterrupt:
      print("break downloader!")
  #----------------------------------------------------------------------
  def download(self):
    """ Downloads data from all resources (in config.json)."""
    for key, val in self.RESOURCES.items():
      try:
        module = __import__(key)
        for keyc, valc in val.items():
          class_ = getattr(module, keyc)
          self._downloadProvider(symbols=valc, provider=class_(),
                                  dtStart=self.DATETIME_START, dtEnd=self.DATETIME_END,
                                  chunkDays=self.CHUNK_IN_DAYS, timeframe=self.TIMEFRAME,
                                  isAppend=self.APPEND_DATA)
      except ModuleNotFoundError:
        logger.error('error: module "({0})" is not found!'.format(key))
      except DataObtainError as e:
        logger.error('error: module "({0}) has a problem": '.format(key), e)
    if self.TIMEOUT > 0:
      logger.info('')
      logger.info('Next downloading in {0}...'.format(datetime.now() + timedelta(minutes=self.TIMEOUT)))
      logger.info('')
  #----------------------------------------------------------------------
  def _downloadProvider(self, provider, symbols, dtStart, dtEnd, chunkDays, timeframe, isAppend):
    """
    Downloads the stock data for <symbols> from <provider> and put all of this the txt-file
    """
    clsname = provider.__class__.__name__
    logger.info('*' * 40)
    logger.info('{0}: start downloading...'.format(clsname))
    logger.info('*' * 40)
    for symbol in symbols:
      try:
        if not is_not_empty(symbol):
          raise KeyError
        logger.info('{0}: from {1} to {2}'.format(symbol, dtStart, dtEnd))
        # get share
        SHARE = provider[symbol]
        # get last date from the file if possible
        name_s = "{0}_{1}.txt".format(symbol, int(timeframe.total_seconds() / 60))
        path = Path(name_s)
        myf = None
        if isAppend and path.is_file():
          with path.open() as f:
            lines = f.readlines()
            dtStart = datetime.strptime(lines[-1].split(';')[1], '%Y-%m-%d %H:%M:%S') + timeframe if len(lines) > 0 else dtStart
          myf = path.open('a')
          logger.debug('{0}: append it to an existing file'.format(name_s))
        else:
          myf = path.open('w')
          logger.debug('(0): new file was created'.format(name_s))
        
        # get start/end dates for portions downloading in loop
        dtS, dtE = dtStart, min([dtStart + chunkDays, datetime.today()])

        # sequentially extracts portion of the bars and append it into the file
        cnt_all = 0
        while dtEnd > dtS and dtS <= datetime.today():
          logger.info('{0}: {1}: {2}'.format(symbol, dtS, dtE))
          cnt = sum(myf.write('{0}\n'.format(it)) for it in SHARE.get_bars(timeframe, dtS, dtE))
          dtS, dtE = dtS + chunkDays, dtE + chunkDays
          logger.info('--- {0}: write: {1} '.format(symbol, cnt))
          cnt_all += cnt
          
        myf.close()
        logger.info('--- {0}: total: {1}'.format(symbol, cnt_all))
        logger.info('-' * 40)
        
      except KeyError:
        logger.warning('{0}: skip symbol [{1}] because of absent'.format(clsname, symbol))
      except Exception as e:
        logger.error('{0}: skip error; ({1})'.format(clsname, e))

    logger.info('{0}: end'.format(clsname))
