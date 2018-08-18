"""
Module for common functions
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

__all__ = ["Singleton", "is_float", "is_not_empty", "str2bool", "requests_retry_session"]

#----------------------------------------------------------------------  
def is_float(value):
  try:
    float(value)
    return True
  except ValueError:
    return False
#----------------------------------------------------------------------
def is_not_empty(s):
  return bool(s and s.strip())
#----------------------------------------------------------------------
def str2bool(v):
  return v.lower() in ("yes", "true", "t", "1")
#----------------------------------------------------------------------
def requests_retry_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None,):
  session = session or requests.Session()
  retry = Retry(
      total=retries,
      read=retries,
      connect=retries,
      backoff_factor=backoff_factor,
      status_forcelist=status_forcelist,
  )
  adapter = HTTPAdapter(max_retries=retry)
  session.mount('http://', adapter)
  session.mount('https://', adapter)
  return session

#######################################################################
class Singleton(type):
  _instance = None
  #----------------------------------------------------------------------
  def __call__(self, *args, **kw):
    if not self._instance:
      self._instance = super(Singleton, self).__call__(*args, **kw)
    return self._instance
