"""Module providing a class for sensor detections"""

from __future__ import division
import json

import os
import os.path
import multiprocessing as mp
import logging
import tornado.websocket
from openburst.functions import dbfunctions
from openburst.functions import basefunctions
from openburst.types.scheduler import Scheduler
from openburst.types.requestwrapper import to_request
from openburst.types import dbpersistentaccess
from openburst.constants import openburst_config

class SensorControllerSocketHandler(tornado.websocket.WebSocketHandler):
    """Websocket class for scheduling detections"""
    def __init__(self, val1, val2):
        tornado.websocket.WebSocketHandler.__init__(self, val1, val2)
        self.detection_event = mp.Event()
        self.notify_process = None
        self.scheduler = Scheduler(self, 1)
        self.scheduler.schedule_func()
        self.rad_processes = []  # will have one process for each radar
        self.rad_events = []  # will have one event for each radar
        self.rad_process_running = False

        self.dbaccess = dbpersistentaccess.DbConnector(logging.getLogger(__name__), "DETECTION")

    def close_processes(self):
        """closes sensor detection processes"""
        logging.getLogger("DET").debug(
            "-----------------stoppping target notify_process..........."
        )
        self.detection_event.set()
        if (self.notify_process is not None) and (self.notify_process.is_alive()):
            self.notify_process.terminate()
            self.notify_process.join()

        for p in mp.active_children():
            p.terminate()
            p.join()
        if self.scheduler is not None:
            self.scheduler.wait_time_secs = -1

    def check_origin(self, origin):
        return True


    # the client connected
    def open(self):
        logging.getLogger("DET").info("New Detection Sim client connected; ")
        

    # the client sent the message
    def on_message(self, message):
        line = message
        logging.getLogger("DET").debug("line = %s", line)
        if line is None:
            logging.getLogger("DET").debug("line is None...returning")
            return
        if isinstance(line, str):
            request_received = json.loads(line, object_hook=to_request)
            logging.getLogger("DET").debug(
                "------received request to: %s",  request_received.request_type
            )
            nofargs = len(request_received.args)
            #team = request_received.args[nofargs - 1]
            if request_received.request_type == "STOP_DETECTION":
                logging.getLogger("DET").info(
                    ".stopping detection delivery to client.."
                )
                self.detection_event.set()
                if (self.notify_process != None) and (self.notify_process.is_alive()):
                    self.notify_process.join()
                    self.notify_process = None
            elif request_received.request_type == "START_DETECTION":
                logging.getLogger("DET").info(
                    ".starting detection delivery to client.."
                )
                self.detection_event = mp.Event()
                self.notify_process = mp.Process(
                    target=dbfunctions.listen_and_notify,
                    args=(self.scheduler.queue, "blue_live_detection", "db_update", self.detection_event),
                )
                self.notify_process.start()

        else:
            print("ERROR: detection_sim.py: line is not instance str")

    def on_close(self):
        logging.getLogger("DET").debug("in on_close")
        self.detection_event.set()
        self.scheduler.wait_time_secs = -1
        self.close_processes()


class Application(tornado.web.Application):
    """Websocket Application"""
    def __init__(self):
        base_dir = os.path.dirname(__file__)
        settings = {
            "template_path": os.path.join(base_dir, "../templates"),
            "static_path": os.path.join(base_dir, "../static"),
        }

        tornado.web.Application.__init__(
            self,
            [
                (r"/detection_sim", SensorControllerSocketHandler),
            ],
            **settings
        )


def main():
    "main function of module"
    logger_dir = basefunctions.get_openburst_logging_dir()
    logger_file = logger_dir + "burst_det_logging.json"
    logger = basefunctions.setup_logging(logger_file, "DET")

    logger.info(
        "----------------------------------------------------------------------------------------"
    )
    logger.info(
        "-------------------------------------DETECTION Server newly started---------------------------"
    )
    logger.info(
        "----------------------------------------------------------------------------------------"
    )

    myip = basefunctions.get_myip()
    port = openburst_config.DETECTION_SIM_SERVER_PORT
    dbfunctions.write_server_start_to_db("detection_sim", myip, port)

    # try:
    tornado.options.parse_command_line()
    Application().listen(port)
    main_loop = tornado.ioloop.IOLoop.instance()
    logging.getLogger("DET").info(
        "----------------- DETECTION SIM SERVER UP AND RUNNING..."
    )
    main_loop.start()


if __name__ == "__main__":
    main()
