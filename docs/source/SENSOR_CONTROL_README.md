# 
## Sensor Control

See source code in source/sensorcontrol

### Active Radar
* only targets inside RAD max range is considered for detection. see function: run_rad in sensorcontrol.py.
This means that only detections with pd greater than 0.8 are written to the DB detection_table as the sensor max range is defined by the fact that pd >= 0.8