
"""
Module for replaying recorded air pictures
"""
from __future__ import division

import json
import time
import os
import os.path
import re
import multiprocessing as mp
import logging
import sys
import numpy as np
import psutil
import tornado.websocket

from openburst.functions import dbfunctions
from openburst.functions import basefunctions
from openburst.types import requestwrapper
from openburst.types.scheduler import Scheduler
from openburst.types.requestwrapper import to_request
from openburst.types.target import Target
from openburst.types import dbpersistentaccess
from openburst.constants import openburst_config
from openburst.types import replayrunner
from openburst.constants import replayconstants


if sys.version_info[0] >= 3:
    Unicode = str


# these two module global arrays will be set during run
test_array = []
ref_array = []


def write_target_db_update(
    dbaccess, data_d, data_type, tgt_rcs=1
):

    """
    writes new targets to DB or updates if existing.
    data_type: 0: test, 1: reference
    """
    data = np.reshape(
        data_d[1], [-1, 11]
    )  # data: ref_id, time, id, lat, lon, alt, speed, heading, vx, vy, vz
    if (data.shape[0]) < 1:
        return

    curr_time = data[0][1]

    test_targ_list = []
    seen = (
        set()
    )  # a set to make sure the same target (id_nr and name) is only added once
    if data_type == 0:  # test data = team = red
        for i in reversed(range(len(data))):

            id_nr = int(
                re.sub("\D", "", str(data[i][2]))
            )  # remove all strings from the id_nr

            # instantiate Target with parameters: id_nr, team, rcs, name, running, velocity, lat, lon, height, vx, vy, vz, corridor_breadth, noftargets, typed, threeD_waypoints_id, status, maneuvring, classification, rec_time
            # indexing in data[i]: #  0: report_ID 1: recording_time, 2: id, 3: lat, 4: lon, 5: alt, 6: speed, 7: heading
            target = Target(
                id_nr,
                "red",
                tgt_rcs,
                "test",
                1,
                data[i][6],
                data[i][3],
                data[i][4],
                data[i][5],
                data[i][8],
                data[i][9],
                data[i][10],
                1,
                1,
                0,
                0,
                1,
                1,
                1,
                data[i][1],
            )
            target.update_time = basefunctions.get_time()  # data[i][1]
            curr_test_targ =  (target.id_nr,
                    target.team,
                    target.rcs,
                    target.name,
                    target.running,
                    target.velocity,
                    target.lat,
                    target.lon,
                    target.height,
                    target.vx,
                    target.vy,
                    target.vz,
                    target.corridor_breadth,
                    target.nofTargets,
                    target.typed,
                    target.threeD_waypoints_id,
                    target.status,
                    target.maneuvring,
                    target.classification,
                    target.waypoints,
                    target.waypoints_index,
                    target.update_time,
                    target.terrainHeight,
                    target.recording_time)
            
            
            curr_targ_id = (curr_test_targ[0], curr_test_targ[3])  # id_nr and name
            if curr_targ_id not in seen:
                test_targ_list.append(curr_test_targ)
                seen.add(curr_targ_id)

    ref_targ_list = []
    seen = (
        set()
    )  # a set to make sure the same target (id_nr and name) is only added once
    if data_type == 1:  # red data = team = blue
        for i in reversed(range(len(data))):
            id_nr = int(
                re.sub("\D", "", str(data[i][2]))
            )  # remove all strings from the id_nr
            # target init params: id_nr, team, rcs, name, running, velocity, lat, lon, height, vx, vy, vz, corridor_breadth, noftargets, typed, threeD_waypoints_id, status, maneuvring, classification, rec_time
            target = Target(
                id_nr,
                "blue",
                tgt_rcs,
                "ref",
                1,
                data[i][6],
                data[i][3],
                data[i][4],
                int(data[i][5]),
                data[i][8],
                data[i][9],
                data[i][10],
                1,
                1,
                0,
                0,
                1,
                1,
                1,
                data[i][1],
            )
            target.update_time = basefunctions.get_time()  # data[i][1]
            curr_ref_targ =  (target.id_nr,
                    target.team,
                    target.rcs,
                    target.name,
                    target.running,
                    target.velocity,
                    target.lat,
                    target.lon,
                    target.height,
                    target.vx,
                    target.vy,
                    target.vz,
                    target.corridor_breadth,
                    target.nofTargets,
                    target.typed,
                    target.threeD_waypoints_id,
                    target.status,
                    target.maneuvring,
                    target.classification,
                    target.waypoints,
                    target.waypoints_index,
                    target.update_time,
                    target.terrainHeight,
                    target.recording_time)
            
            if (curr_ref_targ is not None):
                curr_targ_id = (curr_ref_targ[0], curr_ref_targ[3])  # id_nr and name

                # convert tuple entry: np.float64(x) to float(x), to avoid issues when writing to postgresql DB
                for i in range(len(curr_ref_targ)):
                    if isinstance(curr_ref_targ[i], np.float64):
                        list_curr = list(curr_ref_targ)
                        list_curr[i] = float(curr_ref_targ[i])
                        curr_ref_targ = tuple(list_curr)

                if curr_targ_id not in seen:
                    ref_targ_list.append(curr_ref_targ)
                    seen.add(curr_targ_id)

    #  and then write all the ref targets at once to the DB
    if len(ref_targ_list) > 0:
        dbaccess.write_targets(tuple(ref_targ_list))
    # now write all the test targets at once to the DB
    if len(test_targ_list) > 0:
        dbaccess.write_targets(tuple(test_targ_list))


def append_targets(curr_time, prev_time, array_nr, report_ID):
    """
    returns [curr_index, data_msg, noftracks, False]
    where data_msg is a 2D array with 2nd dimension indexing:
    0: report_ID 1: recording_time, 2: id, 3: lat, 4: lon, 5: alt, 6: speed, 7: heading, 8: vx, 9: vy, 10: vz
    
    """

    data_array = []
    if array_nr == 0:
        data_array = test_array
    else:
        data_array = ref_array

    data_msg = []
    noftracks = 0

    if data_array is None:
        return [0, [], 0, True]

    time_array = data_array[:, 9]
    
    mask = np.where((time_array <= curr_time) & (time_array >= prev_time))
    
    if mask[0].size < 1:
        return [0, [], 0, False]

    try:
        start_index = mask[0][0]
        stop_index = mask[0][-1]

        if stop_index >= (data_array.shape[0] - 1):  # all data was scanned
            logging.getLogger("REPLAY").info("all data scanned")
            return [0, [], 0, True]

        noftracks = mask[0].shape[0] #- 1
        #print("noftracks = ", noftracks, "stop/start indices = ", start_index, stop_index, ", data_array.shape[0]: ", data_array.shape[0])
    except: # pylint: disable=bare-except
        return [0, [], 0, False]

    if noftracks == 0:
        logging.getLogger("REPLAY").info("no tracks found...")
        return [0, [], 0, False]

    if start_index==stop_index:
        data_block = np.array([data_array[ start_index, [9, 2, 3, 4, 7, 6, 5, 10, 11, 12]]]  )
    else:
        data_block = data_array[
            start_index:stop_index, [9, 2, 3, 4, 7, 6, 5, 10, 11, 12]
        ]  # recording_time[ms], id, lat, lon, alt, speed, heading, vx, vy, vz 
    
    #print("data_block = ", data_block)

    if array_nr == 1:
        prog = round(float(stop_index) / float(data_array.shape[0]), 3)
    else:
        prog = round(float(stop_index) / float(data_array.shape[0]), 3)

    reports_id_column = int(report_ID) * np.ones([data_block.shape[0], 1])
    data_msg_2d = np.hstack((reports_id_column, data_block))
    data_msg = data_msg_2d.ravel()
    curr_index = stop_index
    return [curr_index, data_msg, noftracks, False]



class ReplayRunnerClass(mp.Process):
    # Class to collect and replay targets, ie write targets to the DB
    # the queue is used to send just replay statistics to the client
    def __init__(self, npr_test, npr_ref, start_time, queue, tgt_rcs, sampling_time):
        mp.Process.__init__(self)
        self.daemon = False
        self.alive = mp.Event()
        self.alive.set()
        self.npr_test = npr_test
        self.npr_ref = npr_ref
        self.start_time = (
            start_time  # this is the start time of the first track in reference file
        )
        self.queue = queue
        self.tgt_rcs = tgt_rcs
        self.sampling_time = sampling_time

        self.dbaccess = dbpersistentaccess.DbConnector(logging.getLogger(__name__), "REPLAY")

    def run(self):
        curr_time = (
            self.start_time
        )  # [ms after midnight: this is the start time of the first track in reference file]
        prev_time = curr_time - (self.sampling_time * 1000.0)  # [ms after midnight]
        logging.getLogger("REPLAY").info("prev_time = %s ", prev_time)

       

        global test_array
        test_array = self.npr_test
        global ref_array
        ref_array = self.npr_ref

        #test_done = False
        ref_done = False

        count = 1.0
        mean_det = 0.0
        total_det = 0.0
        #mean_plot = 0.0
        #mean_track = 0.0
        first_ref_time = 0
        replay_start_time = time.time()  # [s]
        replay_speed = 0

        #elapsed = 0
        replay_speed = 0
        while self.alive.is_set():

            rt = time.time()  # [s]

            # -----------------------------get test data in this time window
            ind_data = append_targets(
                curr_time, prev_time, 0, replayconstants.TEST_REPLAY_REPORT
            )  # curr_time and prev_time in [ms after midnight]

            # ------------------------------get ref data in this time window
            ind_data2 = append_targets(
                curr_time, prev_time, 1, replayconstants.REF_REPLAY_REPORT
            )  # curr_time and prev_time in [ms after midnight]
            ref_done = ind_data2[3]

            try:
                if (
                    first_ref_time == 0
                ):  # set the very first time of the replay file (ms after midnight of that day when recording was done)
                    first_ref_time = ind_data2[1][1] / 1000.0  # [s]
            except: # pylint: disable=bare-except
                pass

            # write replay data to DB
            logging.getLogger("REPLAY").info(
                "going to write to DB: test tracks = %s, ref tracks = %s ",
                ind_data[2],
                ind_data2[2],
            )
            write_target_db_update(self.dbaccess, ind_data, 0, self.tgt_rcs)  # test
            write_target_db_update(self.dbaccess, ind_data2, 1, self.tgt_rcs)  # ref

            if ind_data2[2] > 0:  # if more than 0 replay targets in this time window
                rtime = ind_data2[1][1]  # [ms after midnight]
                ref_time = rtime / 1000.0  # [s]
                ref_time = ref_time - first_ref_time

                # detection statistics
                stats = self.dbaccess.get_detection_statistics()
                logging.getLogger("REPLAY").info(
                    "DISTINCT DETECTIONS = %s FROM total objects in sky = %s",
                    stats[0],
                    stats[1],
                )
                total_det = total_det + stats[0]
                mean_det = (total_det) / count
                count = count + 1.0

                # compute replay speed
                replay_runtime = round(rt - replay_start_time, 2)  # [s]

                # send replay stats to client
                mean_cpu_load = psutil.cpu_percent()
                tmp_msg = [
                    replay_speed,
                    round(mean_det, 2),
                    stats[0],
                    stats[1],
                    mean_cpu_load,
                    round(ref_time, 2),
                    replay_runtime,
                    rt * 1000.0,
                ]

                nbr_args = 1
                args = [json.dumps(tmp_msg)]
                response = requestwrapper.RequestWrapper("REPLAY_STATS", nbr_args, args)
                response_json = json.dumps(response.__dict__)
                self.queue.put(response_json)
                logging.getLogger("REPLAY").info(
                    "put to scheduler queue; %s ", response_json
                )

            if ref_done:
                logging.getLogger("REPLAY").info(
                    "***************** REF FILE OVER...STOPPING REPLAY..."
                )
                # tell client that replay is completed, then the client will ask to stop replay again
                response = "REPLAY_COMPLETED"
                response_json = json.dumps(response)
                logging.getLogger("REPLAY").info(
                    "going to send to client: %s", response_json
                )
                ###socket.write_message(response_json)
                self.queue.put(response_json)
                self.alive.clear()

            prev_time = curr_time  # this is time in reference file [ms after midnight]
            curr_time = curr_time + (self.sampling_time * 1000.0)
            # millisecs, this is time in reference file

            processing_time = time.time() - rt
            if (
                processing_time < replayconstants.REPLAY_DATA_DB_WRITE_INTERVAL
            ):  # just sleep if necessary
                logging.getLogger("REPLAY").info(
                    "sleeping for: %s (REPLAY_DATA_DB_WRITE_INTERVAL = %s)",
                    replayconstants.REPLAY_DATA_DB_WRITE_INTERVAL - processing_time,
                    replayconstants.REPLAY_DATA_DB_WRITE_INTERVAL,
                )
                time.sleep(
                    replayconstants.REPLAY_DATA_DB_WRITE_INTERVAL - processing_time
                )  # indentation of time.sleep : one intendation under while loop

            loop_time = (time.time() - rt) * 1000.0  # [ms]
            logging.getLogger("REPLAY").info(
                "data sampling replay file at [ms] = %s, elapsed loop time [ms] = %s, speed = %s ",
                curr_time - prev_time,
                loop_time,
                (curr_time - prev_time) / loop_time,
            )
            replay_speed = (curr_time - prev_time) / loop_time

            # remove targets that are too old from DB (older than loop_time * 3 [ms])
            now = basefunctions.get_time()
            self.dbaccess.remove_inactive_replay_targets((loop_time * 10) / replay_speed, now)

        logging.getLogger("REPLAY").info(
            "got out of the REPLAY while loop..........................."
        )
        
    
    def stop_replay(self):
        """
        stops replaying targets
        """
        self.alive.clear()
        self.dbaccess.conn.close()


##----------------------------------


class ReplayWebSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, val1, val2):
        tornado.websocket.WebSocketHandler.__init__(self, val1, val2)
        self.scheduler = None  # Scheduler(self, 0.01)
        self.target_notify_scheduler = None
        self.rc = None
        self.rc_notify = None
        self.npr_ref = None
        self.npr_test = None

    def check_origin(self, origin):
        return True

    # the client connected
    def open(self):
        logging.getLogger("REPLAY").info("New Replay client connected; ")

    # the client sent the message
    # we use memory profiler to check the memory usage

    # @profile
    def on_message(self, message):

        logging.getLogger("REPLAY").info(
            "-------------------------MESSAGE RECEIVED FROM CLIENT-----------------------"
        )

        line = message
        if line is None:
            logging.getLogger("REPLAY").info("line is None...returning")
            return
        if isinstance(line, Unicode):
            logging.getLogger("REPLAY").info("line = %s", line)
            request_received = json.loads(line, object_hook=to_request)

            if request_received.request_type == "REPLAY_START_SEND_TEST_DATA_FLOW":
                logging.getLogger("REPLAY").info(
                    "-------------------------REPLAY_START_SEND_TEST_DATA_FLOW-----------------------"
                )
                # parse data:
                ref_file_name = json.loads(request_received.args[0])
                ref_file_name = openburst_config.REPLAY_DATA_PATH + ref_file_name
                logging.getLogger("REPLAY").info("ref_file_name: %s", ref_file_name)

                test_file_name = json.loads(request_received.args[1])
                test_file_name = openburst_config.REPLAY_DATA_PATH + test_file_name
                logging.getLogger("REPLAY").info("test_file_name: %s", test_file_name)

                tmp_json = json.loads(request_received.args[2])
                replayconstants.SAMPLING_TIME = int(tmp_json)
                logging.getLogger("REPLAY").info("SAMPLING_TIME = %s", replayconstants.SAMPLING_TIME)

                tmp_json = json.loads(request_received.args[3])
                replayconstants.REPLAY_DATA_DB_WRITE_INTERVAL = float(tmp_json)
                logging.getLogger("REPLAY").info(
                    "REPLAY_DATA_DB_WRITE_INTERVAL = %s", replayconstants.REPLAY_DATA_DB_WRITE_INTERVAL
                )

                tmp_json = tmp_json = json.loads(request_received.args[6])
                tgt_rcs = float(tmp_json)
                print("received RCS of tgt = ", tgt_rcs)

                # ----------------open the test data
                try:
                    print("test file: ", test_file_name)
                    self.npr_test = np.load(
                        test_file_name, encoding="latin1", allow_pickle=True
                    )
                    test_start_time = self.npr_test[0, 9]

                except: # pylint: disable=bare-except
                    logging.getLogger("REPLAY").info(
                        "test file not found..just replaying ref file"
                    )
                    self.npr_test = None

                self.npr_ref = np.load(
                    ref_file_name, encoding="latin1", allow_pickle=True
                )
                ref_start_time = self.npr_ref[0, 9]

                # ----------------get the lowest time
                start_time_np = ref_start_time

                logging.getLogger("REPLAY").info("ref_start_time = %s", ref_start_time)
                logging.getLogger("REPLAY").info("start_time_np = %s", start_time_np)

                if self.npr_test is not None:
                    logging.getLogger("REPLAY").info(
                        "test_start_time = %s", test_start_time
                    )

                logging.getLogger("REPLAY").info("ref_start_time = %s", ref_start_time)
                logging.getLogger("REPLAY").info("start_time_np = %s", start_time_np)

                #self.dbaccess.remove_pcl_detections()
                dbfunctions.remove_pcl_detections()
                #dbfunctions.startReplayConn()

                self.scheduler = Scheduler(
                    self, 1.0
                )  # the queue is just used to send the REPLAY STATS to the client, so a low freq of 1s is ok
                self.scheduler.schedule_func()
                self.rc = ReplayRunnerClass(
                    self.npr_test,
                    self.npr_ref,
                    start_time_np,
                    self.scheduler.queue,
                    tgt_rcs,
                    replayconstants.SAMPLING_TIME,
                )  # writes REPLAY targets to DB target table
                self.rc.start()

                self.target_notify_scheduler = Scheduler(
                    self, replayconstants.REPLAY_DATA_DB_WRITE_INTERVAL
                )  # this queue is used to send the REPLAY targets from DB to the client, here we use the same freq as the DB update rate
                self.target_notify_scheduler.schedule_func()
                self.rc_notify = replayrunner.ReplayTargetNotifyRunnerClass(
                    self.target_notify_scheduler.queue
                )  ## sends changes on DB target table to client (ie to browser)
                self.rc_notify.start()
                logging.getLogger("REPLAY").info(
                    "**********************REPLAY PROCESS STARTED...**************************"
                )

            elif request_received.request_type == "REPLAY_STOP_SEND_TEST_DATA_FLOW":

                logging.getLogger("REPLAY").info(
                    "***************************************************************************"
                )
                logging.getLogger("REPLAY").info(
                    "-------------------------terminating replay process-----------------------"
                )
                logging.getLogger("REPLAY").info(
                    "***************************************************************************"
                )
                try:

                    if self.scheduler != None:
                        self.scheduler.wait_time_secs = -1

                    if self.target_notify_scheduler != None:
                        self.target_notify_scheduler.wait_time_secs = -1

                    if self.rc != None:
                        self.rc.stop_replay()  # stops writing targets to target DB table
                        self.rc.terminate()
                        self.rc.join()
                        del self.rc

                    if self.rc_notify != None:
                        self.rc_notify.stop_targets_replay()  # stops sending changes of DB target table to the websocket client (ie to browser)
                        self.rc_notify.terminate()
                        self.rc_notify.join()
                        del self.rc_notify

                    del self.npr_ref

                    del self.npr_test

                    dbfunctions.remove_team_from_table("blue", "target")

                    self.scheduler = None  # Scheduler(self, 0.01)
                    self.target_notify_scheduler = None
                    self.rc = None
                    self.rc_notify = None
                    self.npr_ref = None
                    self.npr_test = None

                    logging.getLogger("REPLAY").info(
                        "%%%%%%%%%%%%%%%%%%%%%%%%%% termination of all replay processes completed %%%%%%%%%%%%"
                    )

                except Exception as e:  # pylint: disable=broad-except
                    logging.getLogger("REPLAY").info(
                        "exception happened while stopping RC. Exc = %s ", str(e)
                    )
                    pass

            elif request_received.request_type == "GET_REPLAY_REF_DATA":

                replay_ref_files = []

                replay_ref_files = next(os.walk(openburst_config.REPLAY_DATA_PATH))[2]

                tmp_msg = replay_ref_files
                nbr_args = 1
                args = [json.dumps(tmp_msg)]
                response = requestwrapper.RequestWrapper(
                    request_received.request_type + "_response", nbr_args, args
                )
                response_json = json.dumps(response.__dict__)
                logging.getLogger("REPLAY").info(
                    "going to send to client: %s", response_json
                )
                self.write_message(response_json)

            elif request_received.request_type == "GET_REPLAY_TEST_DATA":
                logging.getLogger("REPLAY").info("get test replay data query")
                replay_test_files = []
                replay_test_files = next(os.walk(openburst_config.REPLAY_DATA_PATH))[2]

                tmp_msg = replay_test_files
                nbr_args = 1
                args = [json.dumps(tmp_msg)]
                response = requestwrapper.RequestWrapper(
                    request_received.request_type + "_response", nbr_args, args
                )
                response_json = json.dumps(response.__dict__)
                logging.getLogger("REPLAY").info(
                    "going to send to client: %s", response_json
                )
                self.write_message(response_json)


class Application(tornado.web.Application):
    def __init__(self):
        base_dir = os.path.dirname(__file__)
        settings = {
            "template_path": os.path.join(base_dir, "../templates"),
            "static_path": os.path.join(base_dir, "../static"),
        }
        tornado.web.Application.__init__(
            self,
            [
                (r"/replay", ReplayWebSocketHandler),
            ],
            **settings
        )


def main():
    logger_dir = basefunctions.get_openburst_logging_dir()
    logger_file = logger_dir + "burst_replay_logging.json"
    logger = basefunctions.setup_logging(logger_file, "REPLAY")
    logger.info(
        "----------------------------------------------------------------------------------------"
    )
    logger.info(
        "-------------------------------------REPLAY Server newly started---------------------------"
    )
    logger.info(
        "----------------------------------------------------------------------------------------"
    )

    myip = basefunctions.get_myip()
    port = openburst_config.REPLAY_SERVER_PORT
    dbfunctions.write_server_start_to_db(
        "replay", myip, port
    )  # write to db that server started (this name should be the same as the opened port ending "/replay" !!)
    try:
        tornado.options.parse_command_line()
        Application().listen(port)
        main_loop = tornado.ioloop.IOLoop.instance()
        logging.getLogger("REPLAY").info(
            "-----------------REPLAY SERVER UP AND RUNNING..."
        )
        main_loop.start()

    except: # pylint: disable=bare-except
        logging.getLogger("REPLAY").error(
            "REPLAY Server initialization error! check 1) ip or port setting in servers.py, 2) check if DB-server running 3) and if DB schema and tables initiated correctly"
        )


if __name__ == "__main__":
    main()
