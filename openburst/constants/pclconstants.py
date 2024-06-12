"""This module defines project-level constants for using PCL"""

PCL_PLOT_LIFETIME = 2 # [s] a pcl plot lives for max this much time if not updated

MAX_TGT_RX_RANGE = 180 # [km] , max range considered between target and Rx for detection
MAX_TGT_TX_RANGE = 180 # [km] , max range considered between target and Tx for detection


SNR_THRESHOLD = 15.0  # [dB], SNR threshold for detection
DOPPLER_THRESHOLD = 2.0  # [dB], for detection
MIN_RCS_THRESHOLD = 150.0  # [m2], for detection

SENSOR_UPDATE_TIME = 1 # [s], update rate for pcl detection

# maximum coherent integration time in [s] (use appropriate values for different signals)
MAX_COHERENT_INTEGRATION_TIME_FM = 0.5

# we set a minimal bistatic rcs for online detection (i.e. the target is only detected if its bistatic RCS is above this value)
MIN_BISTATIC_RCS_ONLINE_DETECTION = 10.0 # [m]
