""""
Sensor controller module: for retrieving, storing and online running sensors

"""

from __future__ import division

import os
import os.path
import logging
from datetime import datetime, timezone
import json
import multiprocessing as mp
import time
import sys
import numpy as np
import math
import tornado.websocket

from openburst.functions import basefunctions 
from openburst.functions import geofunctions, dbfunctions
from openburst.types import dbpersistentaccess
from openburst.constants import openburst_config, replayconstants

from openburst.types.tx import to_Tx
from openburst.types.rx import to_Rx
from openburst.types.scheduler import Scheduler
from openburst.types.splatmanager import StateManager
from openburst.types.requestwrapper import to_request
from openburst.types.activemonostaticsensor import to_active_rad_params
from openburst.types import pcldetectionrunner
from openburst.types import raddetectionrunner
from openburst.types import waypoint

if sys.version_info[0] >= 3:
    Unicode = str


def update_target_track(tgt_lat, tgt_lon, tgt_alt, tgt_ms_after_midnight, vlc, sampling_time, wayp_lat, wayp_lon, wayp_alt, tgt_vx, tgt_vy, tgt_vz, intended_heading):
    """ 
    Updates a given targets track
    vlc in [m/s] and sampling_time in [s]
    """

    if ((abs(tgt_vx) > 0 ) or (abs(tgt_vy) > 0)):
        alpha = math.degrees(math.atan2(tgt_vx, tgt_vy))
        if alpha < 0:
            alpha = 360 + alpha # now alpha is on degrees from north
        curr_heading = alpha
    else:
        curr_heading = intended_heading
    
    tmp_heading = curr_heading * 0.99 + intended_heading * 0.01 # smoothing

    # make sure that we turn in the shortest direction (work in progress)
    delta_heading = abs(curr_heading - tmp_heading)
    new_heading_one = curr_heading - delta_heading
    if (new_heading_one < 0 ):
        new_heading_one = 360.0 + new_heading_one
    new_heading_two = curr_heading + delta_heading
    if (new_heading_two > 360.0):
        new_heading_two = new_heading_two - 360.0
    if (abs(intended_heading - new_heading_one) < abs(intended_heading - new_heading_two)):
        new_heading = new_heading_one
    else:
        new_heading = new_heading_two

    if ((abs(tgt_vx) > 0 ) or (abs(tgt_vy) > 0) or (tgt_vz > 0)): # when atleast one velocity is non-zero
        
        delta_wayp_xy = geofunctions.get_2d_distance_between_locs(tgt_lat, tgt_lon, wayp_lat, wayp_lon) * 1000.0 # [m]
        delta_z = wayp_alt - tgt_alt # [m]
        elev_angle = np.arctan2(delta_z, delta_wayp_xy)
        vlc_z = vlc * np.sin(elev_angle)
        vlc_xy = vlc * np.cos(elev_angle)

        #print("delta_z = ", delta_z, ", delta_xy = ", delta_wayp_xy, ", elev_angle = ", elev_angle, ", vlc_xy [m/s] = ", vlc_xy, ", vlc_z [m/s] = ", vlc_z, ", vlc = ", vlc)

    else:    # in the beginning when all velocities are zero
        delta_wayp_xy = geofunctions.get_2d_distance_between_locs(tgt_lat, tgt_lon, wayp_lat, wayp_lon) * 1000.0 # [m]
        delta_z = wayp_alt - tgt_alt # [m]
        elev_angle = np.arctan2(delta_z, delta_wayp_xy)
        vlc_z = vlc * np.sin(elev_angle)
        vlc_xy = vlc * np.cos(elev_angle)
        
    new_lat_lon = geofunctions.burstvincentydistance((tgt_lat, tgt_lon), (vlc_xy*sampling_time)/1000, new_heading)
    tgt_new_alt = tgt_alt + vlc_z * sampling_time

    vx = geofunctions.get_2d_distance_between_locs(tgt_lat, new_lat_lon.longitude, tgt_lat, tgt_lon) * 1000.0  / sampling_time # [m/s] on lon axis
    vy = geofunctions.get_2d_distance_between_locs(new_lat_lon.latitude,  tgt_lon, tgt_lat, tgt_lon) * 1000.0  / sampling_time # [m/s] on lat axis 
    vz = (tgt_new_alt - tgt_alt) / sampling_time # vlc_z # [m/s] on z axis
    

    if (new_lat_lon.latitude < tgt_lat):
        vy = -1 * abs(vy)
    if (new_lat_lon.longitude < tgt_lon):
        vx = -1 * abs(vx)
    if (wayp_alt < tgt_alt):
        vz = -1 * abs(vz)
    #print("(new lat/lon: ", new_lat_lon.latitude,new_lat_lon.longitude, ", lat/lon: ", tgt_lat, tgt_lon, "-------vx, vy, vz = ", vx, vy, vz)
    #print("tgt_ms_after_midnight + sampling_time*1000: ", tgt_ms_after_midnight + sampling_time*1000)
    return [tgt_new_alt, (new_lat_lon.latitude, new_lat_lon.longitude), curr_heading, tgt_ms_after_midnight + sampling_time*1000, vx, vy, vz]


def create_target_replay_track(target, waypoint_dct):
    """
    Creates target replay track
    """
    target_locations = waypoint_dct['targetLocationArray']
    datetime_ind = datetime.now(timezone.utc)
    track_quality = 1
    ms_after_midnight = 0
    tgt_id = target["id"]
    
    tgt_lat = float(target_locations[0]['lat'])
    tgt_lon = float(target_locations[0]['lon'])
    tgt_alt = float(target_locations[0]['flightHeight']) # [masl]

    vlc = target["velocity"] # [m/s]
    speed = vlc * 3.6 # [km/h]

    tgt_vlx = 0 # [m/s] on lon axis
    tgt_vly = 0 # [m/s] on lat axis
    tgt_vlz = 0 # [m/s] on z axis
    
    tgt_track_arr = [datetime_ind, 0, tgt_id, tgt_lat, tgt_lon, 0, speed, tgt_alt, track_quality, ms_after_midnight, tgt_vlx, tgt_vly, tgt_vlz]
    
    sampling_time = replayconstants.NEW_TARGET_SAMPLING_TIME # [s] 
    tgt_vx = 0 
    tgt_vy = 0 
    tgt_vz = 0

    for j in range(1, len(target_locations)):
        try:
            loc = target_locations[j]
            wayp_lat = float(loc['lat'])
            wayp_lon = float(loc['lon'])
            #wayp_terrainHeight = float(loc['terrainHeight'])
            wayp_alt = float(loc['flightHeight'])
            dist_to_wayp = 10000 # [km]
            max_dist_per_sample = 200* speed * sampling_time/3600.0 # [km]  # we change waypoint before reaching the waypoint, to have smoothe curves
            #print(":::::::::::: max_dist_per_sample [km] = ", max_dist_per_sample, ", dist_to_wayp [km]: ", dist_to_wayp )
            
            

            while (dist_to_wayp > (max_dist_per_sample)): # [km]
                dist_to_wayp = geofunctions.get_2d_distance_between_locs_heights(tgt_lat, tgt_lon, tgt_alt, wayp_lat, wayp_lon, wayp_alt) # [km]
                intended_heading = geofunctions.calculate_initial_compass_bearing((tgt_lat, tgt_lon), (wayp_lat, wayp_lon))
                [tgt_new_alt, new_lat_lon, heading, new_ms_after_mid, tgt_vx, tgt_vy, tgt_vz] = update_target_track(tgt_lat, tgt_lon, tgt_alt, ms_after_midnight, vlc, sampling_time, wayp_lat, wayp_lon, wayp_alt, tgt_vx, tgt_vy, tgt_vz, intended_heading)
                
                tgt_lat = new_lat_lon[0]
                tgt_lon = new_lat_lon[1]
                tgt_alt = tgt_new_alt
                ms_after_midnight = new_ms_after_mid
                newrow =  [datetime_ind, 0, tgt_id, tgt_lat, tgt_lon, heading, speed, tgt_alt, track_quality, ms_after_midnight, tgt_vx, tgt_vy, tgt_vz]                
                tgt_track_arr = np.vstack([tgt_track_arr, newrow])
            
        except Exception as e: # pylint: disable=bare-except # pylint: disable=bare-except
            logging.getLogger("SENSOR_CONTROL").info("warning: key error in waypoint target_locations...: %s ", e)
            

        logging.getLogger("SENSOR_CONTROL").info("finished logging wayp: %s, for target: %s", j, tgt_id)

    np_arr = np.array(tgt_track_arr)
    return np_arr
    


def insert_air_target_tracks(request_received): 
    """
    Inserts Air Target Tracks
    """
    logging.getLogger("SENSOR_CONTROL").info("insert_AIR received...")
    nofargs = len(request_received.args)
    team = request_received.args[nofargs-1]

    target_array = json.loads(request_received.args[0])
    waypoint_array = json.loads(request_received.args[1])
    
    all_tgts_np_arr = np.empty([0,13])
    #for i in range(0, len(target_array)):
    print("target_array = ", target_array)
    
    for i, tgt in enumerate(target_array):
        #tgt = target_array[i]
        print("target = ", tgt)
        #-------- traverse and create single target tracks
        #for i in range(0, len(waypoint_array)):
        for j, wayp in enumerate(waypoint_array):
            print("wayp = ", wayp)
            #wypoint = waypoint_array[i]
            waypointt = waypoint.to_waypoint_params(wayp)

            waypointt.team = team
            if (tgt["threeD_waypoints_id"] != waypointt.id_nr):
                continue
            else:
                tgt_np_arr = create_target_replay_track(tgt, wayp)
                all_tgts_np_arr = np.vstack([all_tgts_np_arr, tgt_np_arr])
            
    # sort array by ms_after_midnight
    # DateTimeIndex, millisecs, converted_integer_id, lat, lon, heading[0 = north..180 = south..360 = north], speed[km / h], altitude[m], track_quality, milli_secs_after_midnight, tgt_vx [vel m/s on lon axis], tgt_vy [vel m/s on lat axis], tgt_vz [vel m/s on z axis]
    all_tgts_np_arr = all_tgts_np_arr[all_tgts_np_arr[:,9].argsort()] # sort with time milli_secs_after_midnight
    

    try:
        # the user input targets are saved as a replay file as "user_targets_datetime.npy" in the replay/DATA folder
        replay_data_folder = basefunctions.get_replay_data_folder()
        file_name = replay_data_folder  + "user_targets_" + time.strftime("%Y%m%d-%H%M%S") + ".npy"
        np.save(file_name, all_tgts_np_arr)   
        logging.getLogger("SENSOR_CONTROL").info("numpy replay file saved")
    except: # pylint: disable=bare-except
        logging.getLogger("SENSOR_CONTROL").info(">> numpy replay file saving error !")


class SensorControllerSocketHandler(tornado.websocket.WebSocketHandler):

    """
    Tornado Sensor Controller Socker Handler
    
    """
    def __init__(self, val1, val2):
        tornado.websocket.WebSocketHandler.__init__(self, val1, val2)

        self.rad_processes = []  # will have one process for each radar
        self.rad_process_running = False
        self.rad_scheduler = None  # this is necessary to fetch the RADs from the DB to the client browser: see start_rad_notify

        self.pcl_process_running = False
        self.pcl_processes = []  # will have one process for each pcl rx
        self.pcl_scheduler = None  # Scheduler(self, 0.01)  # 1s wait time

        ## for sharing SPLAT
        self.manager = None  # StateManager()
        self.pcl_splat_manager = None

        self.use_prop = 1  # this should always be one, beacuse we want to consider splat and prop losses always

        # for postgresaccess
        self.dbaccess = dbpersistentaccess.DbConnector(logging.getLogger("SENSOR_CONTROL"), "SENSOR_CONTROL")
        self.dbaccess.connect_to_db()

        self.splat_obj =  None # will ne initialized later
        self.pcl_splat_obj = None # will ne initialized later
        self.rad_notify_event = None # will ne initialized later
        self.rad_scheduler = None # will ne initialized later
        self.notify_process_rad = None # will ne initialized later
        self.pcl_rx_tx_notify_event = None # will ne initialized later
        self.notify_process_pcl_rx = None # will ne initialized later
        self.pcl_scheduler = None # will ne initialized later
        self.notify_process_pcl_tx = None # will ne initialized later

    
    def start_rad_notify(
        self,
    ):  
        """ fetches radars from the DB and delivers to the client """

        logger = logging.getLogger("SENSOR_CONTROL")
        logger.info("++++++++++++++++++++++++starting rad notify process..")
        self.rad_scheduler = Scheduler(
            self, 2.0
        )  # here a large time of 2seconds is ok because this is just to fetch and insert the RADs from and to the DB
        self.rad_scheduler.schedule_func()
        self.rad_notify_event = mp.Event()
        self.notify_process_rad = mp.Process(
            target=dbfunctions.listen_and_notify,
            args=(self.rad_scheduler.queue, "blue_live_rad","db_update", self.rad_notify_event),
        )
        self.notify_process_rad.start()

    def stop_rad_notify(self):
        """
        stops rad db change notifications
        """
        logger = logging.getLogger("SENSOR_CONTROL")
        logger.info("------------stoppping rad notify process ...........")
        self.rad_notify_event.set()
        self.notify_process_rad.terminate()
        self.notify_process_rad.join()
        self.rad_scheduler.wait_time_secs = -1

    def start_pcl_notify(self):

        logger = logging.getLogger("SENSOR_CONTROL")
        logger.info("++++++++++++++++++++++++starting PCL notify process..")
        self.pcl_scheduler = Scheduler(
            self, 2.0
        )  # here a large time of 2seconds is ok becuase this is just to fetch and insert the RADs from and to the DB
        self.pcl_scheduler.schedule_func()
        # self.pcl_notify_event = mp.Event()
        self.pcl_rx_tx_notify_event = mp.Event()
        self.notify_process_pcl_rx = mp.Process(
            target=dbfunctions.listen_and_notify,
            args=(self.pcl_scheduler.queue, "blue_live_pcl_rx", "db_update_pcl_rx_tx", self.pcl_rx_tx_notify_event),
        )
        self.notify_process_pcl_tx = mp.Process(
            target=dbfunctions.listen_and_notify,
            args=(self.pcl_scheduler.queue, "blue_live_pcl_tx", "db_update_pcl_rx_tx", self.pcl_rx_tx_notify_event),
        )
        self.notify_process_pcl_rx.start()
        self.notify_process_pcl_tx.start()

    def stop_pcl_notify(self):
        """
        stops pcl notifications
        """
        logger = logging.getLogger("SENSOR_CONTROL")
        logger.info("------------stoppping PCL Rx Tx notify process ...........")
        self.pcl_rx_tx_notify_event.set()
        self.notify_process_pcl_rx.terminate()
        self.notify_process_pcl_rx.join()
        self.notify_process_pcl_tx.terminate()
        self.notify_process_pcl_tx.join()
        if self.pcl_scheduler != None:
            self.pcl_scheduler.wait_time_secs = -1

    def start_rad_runners(self, team, rcs):

        ## for sharing SPLAT
        self.manager = StateManager()
        # start manager
        self.manager.start()
        self.splat_obj = self.manager.radrunnersplat()#splatmanager.SharedSPLAT()

        if self.rad_process_running:
            logger = logging.getLogger("SENSOR_CONTROL")
            logger.info("rad processes already running...please stop first")
            return

        rads = self.dbaccess.get_all_rads(team)
        rad_start_time = basefunctions.get_time()

        for j in range(len(rads)):

            logger = logging.getLogger("SENSOR_CONTROL")
            logger.info("++++++++++++++++++++++++ starting rad process nr %d", j)
            rc = raddetectionrunner.RADRunnerClass(
                rads[j], rad_start_time, self.splat_obj, rcs, self.use_prop
            )
            rc.start()
            self.rad_processes.append(rc)

        self.rad_process_running = True

    def stop_rad_runners(self, team):
        for j in range(len(self.rad_processes)):
            logger = logging.getLogger("SENSOR_CONTROL")
            logger.info("----------------stopping rad process nr... %d", j)
            self.rad_processes[j].alive.set()
            self.rad_processes[j].stop()
            self.rad_processes[j].terminate()
            self.rad_processes[j].join()

        self.rad_processes = []
        self.rad_process_running = False
        dbfunctions.remove_team_from_table(team, "detection")

        self.manager.shutdown()

    def start_pcl_runners(self, team, rcs):
        ## for sharing SPLAT between all PCL sensors
        self.pcl_splat_manager = StateManager()
        self.pcl_splat_manager.start()
        self.pcl_splat_obj = self.pcl_splat_manager.pclrunnersplat() #SharedSPLAT()
        

        if self.pcl_process_running:
            logger = logging.getLogger("SENSOR_CONTROL")
            logger.info("PCL processes already running...please stop first")
            return

        rxs = self.dbaccess.get_all_pcl_rx(team)
        pcl_start_time = basefunctions.get_time()

        #for j in range(len(rxs)):
        for j, rx in enumerate(rxs):
            logger = logging.getLogger("SENSOR_CONTROL")
            logger.info("++++++++++++++++++++++++ starting PCL process nr %d", j)
            txs = self.dbaccess.get_all_pcl_tx_for_rx(team, rx)
            rc = pcldetectionrunner.PCLRunnerClass(
                rx,
                txs,
                pcl_start_time,
                self.pcl_splat_obj,
                rcs,
                self.use_prop,
                team,
            )
            rc.start()
            self.pcl_processes.append(rc)

        self.pcl_process_running = True

    def stop_pcl_runners(self):  
        
        #for j in range(len(self.pcl_processes)):
        for j, proc in enumerate(self.pcl_processes):
            logger = logging.getLogger("SENSOR_CONTROL")
            logger.info("----------------stopping pcl rx process nr... %d", j)
            if proc != None:
                # self.pcl_events[j].set()
                proc.alive.set()
                proc.stop()
                proc.terminate()
                proc.join()

        self.pcl_processes = []
        self.pcl_process_running = False
        try:
            self.pcl_splat_manager.shutdown()
        except Exception:
            pass
        
        
    # the client connected
    def open(self):
        logger = logging.getLogger("SENSOR_CONTROL")
        logger.info(
            "############################# New Target Sim client connected ############################"
        )
        self.start_rad_notify()
        self.start_pcl_notify()
       

    def ignore_rad(
        self, team
    ):  
        """
        this will set the rad changes to be ignored as the rad status was set to zero by user
        """

        if (self.notify_process_rad != None) and (self.notify_process_rad.is_alive()):
            logger = logging.getLogger("SENSOR_CONTROL")
            logger.info("first triggering a dummy RAD update")
            #dbfunctions.trigger_rads_update(team)
            self.dbaccess.trigger_rads_update(team)
            time.sleep(2.0)
            self.stop_rad_notify()

        else:
            self.start_rad_notify()
            #dbfunctions.trigger_rads_update(team)
            self.dbaccess.trigger_rads_update(team)
            time.sleep(2.0)
            self.stop_rad_notify()

    def check_origin(self, origin):
        return True

    def on_close(self):

        logger = logging.getLogger("SENSOR_CONTROL")
        logger.info("in on_close")

        if self.pcl_scheduler != None:
            self.pcl_scheduler.wait_time_secs = -1

    # the client sent the message
    def on_message(self, message):
        line = message

        if line is None:
            logger = logging.getLogger("SENSOR_CONTROL")
            logger.info("line is None...returning")
            return
        if isinstance(line, Unicode):

            request_received = json.loads(line, object_hook=to_request)
            logger = logging.getLogger("SENSOR_CONTROL")
            logger.info("------received request to: %s", request_received.request_type)
            nofargs = len(request_received.args)

            if request_received.request_type == "RAD_START":
                logger = logging.getLogger("SENSOR_CONTROL")
                logger.info(
                    "-------------------------rad start: %d", len(request_received.args)
                )
                if self.rad_process_running is True:
                    logger = logging.getLogger("SENSOR_CONTROL")
                    logger.info("rad processing running...please stop it first")
                    return
                team = request_received.args[nofargs - 2]
                rcs = float(request_received.args[nofargs - 1])
                print("starting Rad Processes......... with team, rcs = ", team, rcs)
                self.start_rad_runners(team, rcs)

            elif request_received.request_type == "RAD_STOP":
                team = request_received.args[nofargs - 1]
                self.stop_rad_runners(team)
                self.dbaccess.remove_all_rad_detections(team)

            elif request_received.request_type == "PCL_START":
                logger = logging.getLogger("SENSOR_CONTROL")
                logger.info(
                    "-------------------------pcl start: %d", len(request_received.args)
                )
                if self.pcl_process_running == True:
                    logger = logging.getLogger("SENSOR_CONTROL")
                    logger.info("pcl processing running...please stop it first")
                    return
                team = request_received.args[nofargs - 2]
                rcs = float(request_received.args[nofargs - 1])
                self.stop_pcl_notify()
                self.start_pcl_runners(team, rcs)

            elif request_received.request_type == "PCL_STOP":

                team = request_received.args[nofargs - 1]
                self.stop_pcl_runners()
                # self.start_pcl_notify()
                self.dbaccess.remove_all_pcl_detections(team)


            elif request_received.request_type == "insert_AIR":
                insert_air_target_tracks(request_received)

            elif (
                request_received.request_type == "ignore_rad"
            ):  # this is to say that the client is not interested in RADINT update
                team = json.loads(request_received.args[nofargs - 1])
                logger = logging.getLogger("SENSOR_CONTROL")
                logger.info("......ignoring radint !!!!!!!!!!!!!!!!!!!!")
                self.ignore_rad(team)

            elif request_received.request_type == "insertRADINT":
                team = json.loads(request_received.args[nofargs - 1])
                if nofargs > 1:
                    for i in range(0, nofargs - 1):
                        rad = json.loads(
                            request_received.args[i], object_hook=to_active_rad_params
                        )
                        self.dbaccess.write_rad(team, rad)
                        # writes this RAD to DB

            elif request_received.request_type == "insertPCLRx":
                team = json.loads(request_received.args[nofargs - 1])
                print("inserting pcl rx")
                if nofargs > 1:
                    for i in range(0, nofargs - 1):
                        rx = json.loads(request_received.args[i], object_hook=to_Rx)
                        print("rx.callSigns = ", rx.txcallsigns, "rx.name = ", rx.name)
                        self.dbaccess.write_pcl_rx(team, rx)
                        # writes this PCL Rx to DB

            elif request_received.request_type == "insertPCLTx":
                team = json.loads(request_received.args[nofargs - 1])
                print("inserting pcl Tx")
                if nofargs > 1:
                    for i in range(0, nofargs - 1):
                        tx = json.loads(request_received.args[i], object_hook=to_Tx)
                        print("tx.callsign = ", tx.callsign)
                        self.dbaccess.write_pcl_tx(team, tx)
                        # writes this PCL Tx to DB

            elif request_received.request_type == "fetchRADINT":
                team = json.loads(request_received.args[nofargs - 1])
                logger = logging.getLogger("SENSOR_CONTROL")
                logger.info("......fetching radint with team: %s", team)
                self.dbaccess.trigger_rads_update(team)
                logger.info("......finished fetching radint")

            elif request_received.request_type == "fetchPCLRx":
                team = json.loads(request_received.args[nofargs - 1])
                logger = logging.getLogger("SENSOR_CONTROL")
                logger.info("......fetching PCL Rx")
                self.dbaccess.trigger_pcl_rx(team)

            elif request_received.request_type == "inactivateRADINT":
                team = json.loads(request_received.args[nofargs - 1])
                id_nr = json.loads(request_received.args[nofargs - 2])
                logger = logging.getLogger("SENSOR_CONTROL")
                logger.info(".....inactivating radint")
                self.dbaccess.deactivate_rad(id_nr, team)

            elif request_received.request_type == "activateRADINT":
                team = json.loads(request_received.args[nofargs - 1])
                id_nr = json.loads(request_received.args[nofargs - 2])
                logger = logging.getLogger("SENSOR_CONTROL")
                logger.info(".....activating radint")
                self.dbaccess.activate_rad(id_nr, team)

            elif request_received.request_type == "clearRADINT":
                team = json.loads(request_received.args[nofargs - 1])
                dbfunctions.remove_team_from_table(team, "rad")  # removes all RAD from the DB
            elif request_received.request_type == "clearDETECTION":
                team = json.loads(request_received.args[nofargs - 1])
                dbfunctions.remove_team_from_table(team, "detection")  # removes all detections from the DB
            elif request_received.request_type == "removeRADINT":
                team = json.loads(request_received.args[nofargs - 1])
                rad_id = json.loads(request_received.args[nofargs - 2])
                self.dbaccess.remove_table_row(team, rad_id, "rad")  # removes RAD  with id from the DB


class Application(tornado.web.Application):
    """
    Tornado Application class for Sensor Control
    """
    def __init__(self):
        base_dir = os.path.dirname(__file__)
        settings = {
            "template_path": os.path.join(base_dir, "../templates"),
            "static_path": os.path.join(base_dir, "../static"),
        }

        tornado.web.Application.__init__(
            self,
            [
                (r"/sensor_control", SensorControllerSocketHandler),
            ],
            **settings
        )


def main():
    """
    Main function
    """
    try:
        
        logger_dir = basefunctions.get_openburst_logging_dir()
        logger_file = logger_dir + "burst_sensor_control_logging.json"
        logger = basefunctions.setup_logging(logger_file, "SENSOR_CONTROL")

        logger.info(
            "----------------------------------------------------------------------------------------"
        )
        logger.info(
            "-------------------------------------SENSOR CONTROL Server newly started---------------------------"
        )
        logger.info(
            "----------------------------------------------------------------------------------------"
        )

        myip = basefunctions.get_myip()
        port = openburst_config.SENSOR_CONTROL_SERVER_PORT
        dbfunctions.write_server_start_to_db(
            "sensor_control", myip, port
        )  # write to db that server started (this name should be the same as the opened port ending "/geoplot" !!)

        # try:
        tornado.options.parse_command_line()
        Application().listen(port)
        main_loop = tornado.ioloop.IOLoop.instance()
        logger.info("----------------- SENSOR CONTROL SERVER UP AND RUNNING...")
        main_loop.start()

    except: # pylint: disable=bare-except
        logger.error(
            "SENSOR CONTROL initialization error! check 1) ip or port setting in servers.py (in module 'constants'), 2) check if DB-server running 3) and if DB schema and tables initiated correctly"
        )


if __name__ == "__main__":

    main()
