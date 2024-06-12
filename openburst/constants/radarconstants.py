"""This module defines project-level constants for using RAD."""

RADAR_Z_OFFSET = 10 # mAGL (active radar antenna above ground level)
PET_Z_OFFSET = 10 # mAGL (PET above ground level)

RAD_COVERAGE_DISTANCE_STEP = 0.5  # [km], range resolution for radar coverage computation 
RAD_COVERAGE_THETA_STEP = 0.1 # [deg], azimuth resolution for radar coverage computation 

PET_COVERAGE_DISTANCE_STEP = 5.0  # [km], range resolution for radar coverage computation
PET_COVERAGE_THETA_STEP = 0.9  # [deg], azimuth resolution for radar coverage computation
