"""
common function definitions.
"""
    
from __future__ import division


from math import atan2, sqrt
import socket
import time
import sys
import os
import json
import logging
import logging.config
import numpy as np
from websocket import create_connection
from openburst.functions import dbfunctions
from openburst.types import rx as rxclass
from openburst.constants import openburst_config


if sys.version_info[0] >= 3:
    Unicode = str

def get_openburst_root_dir():
    "returns openburst root dir"
    # find out the absolute path where openburst is installed locally
    # openburst_root_dir = os.path.dirname(os.path.abspath(inspect.getsourcefile(openburst)))
    openburst_root_dir = openburst_config.ROOT_DIR
    return openburst_root_dir

def get_openburst_logging_dir():
    "returns openburst logging dir"
    return get_openburst_root_dir() + "/logger_config/"

def set_openburst_system_path():
    """ sets system path so that libsplathd can be imported""" 
    sys_append_dir = get_openburst_root_dir() + '/radterrain/SPLAT_RADIOPROP'
    sys.path.append(sys_append_dir)
    return sys_append_dir

def set_openburst_linked_lib_path(): 
    """ sets the LD_LIBRARY_PATH so that the linked splat! libraries  are found """
    sys_append_dir = get_openburst_root_dir() + '/radterrain/SPLAT_RADIOPROP'  
    os.environ['LD_LIBRARY_PATH'] = sys_append_dir

def get_tx_folder(): 
    """ returns the folder where the tx (ToO) for PCL are stored """
    return get_openburst_root_dir() + "/pcl/ToO/"

def get_replay_data_folder():
    """ returns the folder where the target replay files are stored """
    return get_openburst_root_dir() + "/replay/DATA/"


def setup_logging(path, loggerName):
    """ returns logger """
    if os.path.exists(path):
        with open(path, "rt", encoding="utf-8") as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level="INFO")
    return logging.getLogger(loggerName)


def ensure_utf(s):
    """ensures the given string in unicode

    Parameters
    ----------
    s : string

    Returns
    -------
    : s
        unicode string

    """
    try:
        if isinstance(s, Unicode):
            return s.encode("utf8", "ignore")
        
        return str(s)
    except UnicodeEncodeError:
        return str(s)



def to_radians(theta):
    """converts the given angle in degrees to radians

    Parameters
    ----------
    theta : angle in degrees

    Returns
    -------
    : 
        float in radians
    """

    return np.divide(np.dot(theta, np.pi), np.float32(180.0))


def to_degrees(theta):
    """converts the given angle in radians to degrees

    Parameters
    ----------
    theta : angle in radians

    Returns
    -------
    : 
        float in degrees
    """
    return np.divide(np.dot(theta, np.float32(180.0)), np.pi)



def totuple(a):
    """converts array to tuple

    Parameters
    ----------
    a : array

    Returns
    -------
    : a
        tuple
    """
    try:
        return tuple(totuple(i) for i in a)
    except TypeError:
        return a


def py_ang(v1, v2):
    """Returns the angle in radians between vectors 'v1' and 'v2'"""
    cosang = np.dot(v1, v2)
    sinang = np.linalg.norm(np.cross(v1, v2))
    return np.arctan2(sinang, cosang)


def project_vector_u_on_v(u, v):
    """returns projection of vector u on vector v, u and v given as numpy arrays"""
    # finding norm of the vector v
    v_norm = np.sqrt(sum(v**2))
    proj_of_u_on_v = (np.dot(u, v) / v_norm**2) * v
    return proj_of_u_on_v


def get_myip():
    """!  returns the ip of the current machine"""
    myip = [
        l
        for l in (
            [
                ip
                for ip in socket.gethostbyname_ex(socket.gethostname())[2]
                if not ip.startswith("127.")
            ][:1],
            [
                [
                    (s.connect(("8.8.8.8", 53)), s.getsockname()[0], s.close())
                    for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]
                ][0][1]
            ],
        )
        if l
    ][0][0]
    return myip


def get_proxy_server_ws(ip_str, port_str):
    """! returns a string like 'ws://10.42.0.100:9978/proxy' o that the client can communicate with this proxy server to get other server ips"""
    retstr = "ws://" + ip_str + ":" + port_str + "/proxy"
    return retstr


def get_time():
    """! get the current time in milliseconds since the UNIX epoch (January 1, 1970 00:00:00 UTC) see: https://currentmillis.com/"""
    return int(round(time.time() * 1000))

def get_target_attributes(target):
    """returns target attributes"""
    # id_nr |  team  | rcs | name | running | velocity | lat | lon | height | vx | vy | vz | corridor_breadth | noftargets |  typed  | threed_waypoints_id | status | maneuvring | classification | waypoints | waypoints_index | update_time | terrainHeight | recording_time
    if target is not None:

        return [
            target[0],
            target[1],
            target[2],
            target[3],
            target[4],
            target[5],
            target[6],
            target[7],
            target[8],
            target[9],
            target[10],
            target[11],
            target[12],
            target[13],
            target[14],
            target[15],
            target[16],
            target[17],
            target[18],
            target[19],
            target[20],
            target[21],
            target[22],
            target[23],
        ]
    else:
        return None


def get_rad_attributes(rad):
    """returns rad attributes"""
    # id_nr |  name | status |       lat        |       lon        | power | antenna_diam | freq | pulse_width | cpi_pulses | bandwidth |  pfa  | rotation_time | category | min_elevation | max_elevation | orientation | horiz_aperture | min_detection_range | max_detection_range | min_detection_height | max_detection_height | min_detection_tgt_speed | max_detection_tgt_speed | update_time | team
    if rad is not None:

        return [
            rad[0],
            rad[1],
            rad[2],
            rad[3],
            rad[4],
            rad[5],
            rad[6],
            rad[7],
            rad[8],
            rad[9],
            rad[10],
            rad[11],
            rad[12],
            rad[13],
            rad[14],
            rad[15],
            rad[16],
            rad[17],
            rad[18],
            rad[19],
            rad[20],
            rad[21],
            rad[22],
            rad[23],
            rad[24],
            rad[25],
        ]
    
    return None


def get_pcl_rx_attributes(rxx):
    """returns pcl rx attributes"""
    rx = rxclass.Rx(
        rxx[0],
        rxx[6],
        rxx[3],
        rxx[4],
        rxx[7],
        rxx[8],
        rxx[15],
        rxx[16],
        rxx[2],
        rxx[9],
        rxx[10],
        rxx[11],
        rxx[12],
        rxx[13],
        rxx[14],
        rxx[1],
        rxx[17],
    )
    # Rx class expected format: ID,masl,lat,lon,ahmagl,signal_type,limit_distance,lostxids,status, bandwidth, horiz_diagr_att, vert_diagr_att, gain, losses, temp_sys, name="", txcallsigns=""
    # rxx format (DB rx): 1, "PCL_SENSOR_1", "blue", 47.310116034673, 8.57377319335937, 0, 402, 15, "FM", 8000.0, "0", "", 0.0, 0.0, 300.0, 10000, -1.0, "HOBE1013,MEHI0986"
    return rx


def cross_prod(v1, v2):  
    """ returns cross product between vector v1 and v2 (3D) """
    return [
        v1[1] * v2[2] - v1[2] * v2[1],
        v1[2] * v2[0] - v1[0] * v2[2],
        v1[0] * v2[1] - v1[1] * v2[0],
    ]


def dot_prod(v1, v2):  
    """ returns dot/scalar product between vector v1 and v2 (3D) """
    return v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]


def norm(v1):  
    """ returns Euclidean-norm / 2-norm (3D) of vector"""
    return sqrt(v1[0] ** 2 + v1[1] ** 2 + v1[2] ** 2)


def calc_angle_from_vecs(v1, v2):  
    """ returns the inner angle between two vectors """
    return atan2(norm(cross_prod(v1, v2)), dot_prod(v1, v2))


def open_connection_to_dem_server():
    """ opens and returns websocket connection to DEM server"""
    [ip, port] = dbfunctions.read_server_ip_port_from_db("dem")
    ws_str = "ws://" + ip + ":" + str(port) + "/" + "dem"
    ws_dem_server = create_connection(ws_str)
    return ws_dem_server


def open_connection_to_geoplot_server():
    """ opens and returns websocket connection to geoplot server"""
    [ip, port] = dbfunctions.read_server_ip_port_from_db("geoplot")
    ws_str = "ws://" + ip + ":" + str(port) + "/" + "geoplot"
    ws_geoplot_server = create_connection(ws_str)
    return ws_geoplot_server

def close_connection_to_dem_server(ws_dem_server):
    """ closes websocket connection to dem server"""
    ws_dem_server.close()

def close_connection_to_geoplot_server(ws_geoplot_server):
    """ closes websocket connection to geoplot server """
    ws_geoplot_server.close()

def write_pet_send_list_to_file(send_list, int_name):
    """  used by PET coverage in radterrain.py when large area coverages are to be computed"""
    filename = "/tmp/petfile" + str(int_name) + ".txt"
    with open(filename, "w",  encoding="utf-8") as filehandle:
        for listitem in send_list:
            filehandle.write("%s\n" % listitem)


def send_all_pet_lists(queue):
    """! used by PET coverage in demServer.py when large area coverages are to be computed"""
    for i in range(1, 5):
        sendlist = []
        filename = "/tmp/petfile" + str(i) + ".txt"
        with open(filename, "r", encoding="utf-8") as filehandle:
            for line in filehandle:
                # remove linebreak which is the last character of the string
                currentPlace = line[:-1]
                # add item to the list
                sendlist.append(currentPlace)
        # now send sendlist
        queue.put(json.dumps(sendlist))
        time.sleep(5)


def send_pet_list(queue, i):
    """! used by PET coverage in demServer.py when large area coverages are to be computed"""
    sendlist = []

    filename = "/tmp/petfile" + str(i) + ".txt"
    with open(filename, "r", encoding="utf-8") as filehandle:
        for line in filehandle:
            # remove linebreak which is the last character of the string
            current_place = line[:-1]
            # add item to the list
            sendlist.append(current_place)
    # now send sendlist
    queue.put(json.dumps(sendlist))
