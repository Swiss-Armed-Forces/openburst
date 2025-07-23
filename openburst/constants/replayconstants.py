"""This module defines constants for using REPLAY Server"""
import os


TEST_REPLAY_REPORT = int(os.environ.get("TEST_REPLAY_REPORT", 5469)) # communication key with the client
REF_REPLAY_REPORT = int(os.environ.get("REF_REPLAY_REPORT", 5471)) # communication key with the client

# [s] default replay data DB write interval, this will be overwritten by client entry
REPLAY_DATA_DB_WRITE_INTERVAL = float(os.environ.get("REPLAY_DATA_DB_WRITE_INTERVAL", 1.0))

# [s] default sampling from the track file (ref and test), this will be overwritten by the client
SAMPLING_TIME = float(os.environ.get("SAMPLING_TIME", 0.1)) # 2

# [s] sampling time when writing new user designed targets
NEW_TARGET_SAMPLING_TIME = float(os.environ.get("NEW_TARGET_SAMPLING_TIME", 0.1)) # 10
