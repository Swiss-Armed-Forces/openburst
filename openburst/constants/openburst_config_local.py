""" this module defines postgresql DB parameters, server paths and websocket ports constants"""
import os
import inspect
import openburst

########################################################################################
### ---- shall be configured by the user for the setup being used
########################################################################################

#---- set python version
PYTHON_VERSION = "python3.10"

# directory where KML files are saved on the machine of the geoplot server
KML_FILE_PATH = "/home/red3/Documents/OPENBURST/KML/"

# postgresql DB parameters
BURST_DB_NAME = "red"
BURST_DB_SERVER_IP = "172.20.10.5"
BURST_DB_SERVER_USERNAME = "red3"
BURST_DB_SERVER_PASSWORD = "red"

########################################################################################
### ---- following constants are automatically set and shall no be configured by user
########################################################################################

# --- set root and server directories for openburst
ROOT_DIR = os.path.dirname(os.path.abspath(inspect.getsourcefile(openburst)))

# servers will read the appropriate port numbers from here, before they start
# servers will then write their ip and port into the burst postgres DB, so that clients of these servers can access them
DEM_SERVER_PORT = "9978"  # ws://ip:9978/dem
RAD_SERVER_PORT = "3333"  # octave active radar equation computation port  ws://ip:9978/rad
PET_SERVER_PORT = "7824"  # pet computations
GEOPLOT_SERVER_PORT = "9943"  # geoplot server port  ws://ip:9943/geoplot
DB_SERVER_PORT = "7234"  # here a server will work to read and write to DB
SENSOR_CONTROL_SERVER_PORT = "7982"  # a server to control sensors
DETECTION_SIM_SERVER_PORT = "7983"  # a server to simulate detections
REBOUND_SERVER_PORT = "7112"  # a server for notify/listen clients on the DB
PCL_SERVER_PORT = "7999"  # pcl computations
REPLAY_SERVER_PORT = "9945"  # replay computations
RADIOPROP_SERVER_PORT = "9980"  # radio propagation


server_fields = (
    "radterrain",
    "webserver",
    "geoplot",
    "detection",
    "sensorcontrol",
    "pcl",
    "pet",
    "replay",
)


radterrain_dir = ROOT_DIR + "/radterrain/"
radterrain_server_app = "radterrain.py"


web_dir = ROOT_DIR + "/webserver/"
web_server_app = "webserver.py"

geoplot_dir = ROOT_DIR + "/geoplot/"
geoplot_server_app = "geoplotserver.py"


detection_dir = ROOT_DIR + "/detection/"
detection_server_app = "detection.py"

sensor_control_dir = ROOT_DIR + "/sensorcontrol/"
sensor_control_app = "sensorController.py"


pcl_dir = ROOT_DIR + "/pcl/"
pcl_server_app = "pclserver.py"

pet_dir = ROOT_DIR + "/pet/"
pet_server_app = "petserver.py"

replay_dir = ROOT_DIR + "/replay/"
REPLAY_DATA_PATH = replay_dir + "DATA/"
replay_server_app = "replayServer.py"