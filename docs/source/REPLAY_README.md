# 

## REPLAY Server

See source code in openburst/replay.
### Target replay file

* openBURST target replay files have to be provided in the folder openburst/replay/DATA
* openBURST expects a python numpy target replay file of the following format:
```
DateTimeIndex, millisecs, converted_integer_id, lat, lon, heading[0 = north..180 = south..360 = north], speed[km / h], altitude[m], track_quality, milli_secs_after_midnight
```
* sample content of such a replay file:
```
[DatetimeIndex(['2019-11-18 14:44:51'], dtype='datetime64[ns]', freq=None)
  140.0 6565515248 47.56412 8.92061 249.0 701.908 9400.0 9400.0
  56691140.0]
 [DatetimeIndex(['2019-11-18 14:44:51'], dtype='datetime64[ns]', freq=None)
  140.0 6566495449 46.55311 4.79929 330.0 831.548 10300.0 10400.0
  56691140.0]
 [DatetimeIndex(['2019-11-18 14:44:51'], dtype='datetime64[ns]', freq=None)
  140.0 6566544951 43.94304 8.01493 56.0 916.74 10000.0 10000.0
  56691140.0]
 [DatetimeIndex(['2019-11-18 14:44:51'], dtype='datetime64[ns]', freq=None)
  140.0 6565515351 44.71892 8.96076 44.0 881.552 11000.0 11000.0
  56691140.0]
 [DatetimeIndex(['2019-11-18 14:44:51'], dtype='datetime64[ns]', freq=None)
  140.0 6566524854 45.0078 10.7949 278.0 616.716 0.0 0.0 56691140.0]
 [DatetimeIndex(['2019-11-18 14:44:51'], dtype='datetime64[ns]', freq=None)
  140.0 6567525350 48.03627 9.72522 32.0 224.092 1000.0 1000.0 56691140.0]
 [DatetimeIndex(['2019-11-18 14:44:51'], dtype='datetime64[ns]', freq=None)
  140.0 6565485551 47.83844 11.78225 174.0 614.864 6000.0 6000.0
  56691140.0]
```


* the following line in replayServer.py is hardcoded. The loop_time * X has to be changed for each computer (TBD how to generelize this)
```
remove_inactive_replay_targets((loop_time * 10)/replay_speed, now)
```


## TODO:

* replay seems to work using Tracks as ref file for the following config params in the browser client:
 - sampling time: 1s
 - replay update rate: 1s
 - ref track deletion time: 10s
 - test track delettion time: 10s

 - PROBLEM: when using a sampling time higher than replay update rate...the client air picture is empty
 ---> so no speeded display of air picture possible