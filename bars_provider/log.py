"""
logging setup module
"""

import json
import logging.config
import os

logger = logging.getLogger(__package__)
if logger.level == logging.NOTSET:
  logger.setLevel(logging.WARN)

def setup_logging(
    default_path='logging.json',
    default_level=logging.INFO,
    env_key='LOG_CFG'
):
  """Setup logging configuration"""
  value = os.getenv(env_key, None)
  path = value if value else default_path
  if os.path.exists(path):
    with open(path, 'rt') as f:
      config = json.load(f)
    logging.config.dictConfig(config)
  else:
    logging.basicConfig(level=default_level)
