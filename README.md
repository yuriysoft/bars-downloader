# bars-downloader

This program allows you to download bars from the remote resources in the network.

Parameters with default values:

        "TIMEOUT": 240,
        
              - timeout (minutes) between auto updating OHLC data (if it's '0' then auto updating isn't used)
              
        "TIMEFRAME": "15",
        
              - timeframe; available values are minutes or 'D' for day, 'H' for hour and 'W' for week
              
        "CHUNK_IN_DAYS": 10,
        
              - OHLC data portion for one request (days)
              
        "DATETIME_START": "201612010000",
        
              - start date
              
        "DATETIME_END": "201612300000",
        
              - end date (can be much more than the current date)
              
        "APPEND_DATA": "yes"
        
              - if 'yes' data will be appended to existing file
              

To use own data provider in the project you need:
  1. create new module with class inside.
     New provider class should contains functions:
     - def bars(self, ticker, start, end, period):
         return Bar list
     - def find(self, query):
         return Ticker list
  2. add class name import in file _init__.py
  3. add module & class names in configuration file (config.json), like that:
  
    "bars_provider.finam":{"FinamProvider":["SPFB.SBRF", "SPFB.RTS"]}
            |                    |                   |
      python module name     class name            symbols


By default there are Finam provider (Russin stock: 1,5,15,30,hour,day,week) and Quotemedia provider (US stock: day)

Versions

0.0.1 
