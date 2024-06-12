# 
## Logging

openBURST uses config files to configure logging. 

* see .json logger config files in db/

* for intro to python logging see: [Python Logging](https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/)

* e.g. to configure logging of dem Server change "burst_dem_logging.json" file.
* e.g. to change logging level from CRITICAL to DEBUG, just change to "DEBUG" in the line:

```
"root": {
        "level": "DEBUG",
        "handlers": ["file_handler"]
    }
```
and in
```
"file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "filename": "/tmp/burst_dem.log",
            "maxBytes": 10485760,
            "backupCount": 20,
            "encoding": "utf8"
        }
```

* if you add "console" to the line of handlers, all the logging level output will also be shown on the console.
* the above json file is configured that the logging messages goes to the file /tmp/burst_dem.log

* OPEBURST uses "multitail" to keep reading the logging file

* see the log button in modules_manager GUI

