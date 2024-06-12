"""Module for running target replay"""

import multiprocessing as mp
import select
import logging
import json
import psycopg2

from openburst.constants import openburst_config
from openburst.types.dbpersistentaccess import DbConnector
from openburst.types import requestwrapper


class ReplayTargetNotifyRunnerClass(mp.Process):
    """Class for a single process for running replay"""
    def __init__(self, queue):
        # must call this before anything else
        mp.Process.__init__(self)
        self.daemon = False
        self.alive = mp.Event()
        self.alive.set()

        self.queue = queue
        self.dbconn = DbConnector(logging.getLogger(__name__), "RADTERRAIN")
        self.conn = self.dbconn.conn
        self.conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        self.curs = self.conn.cursor()
        # listen on mulitple channels: ie for blue and red targets
        self.curs.execute("LISTEN red_live_target;")
        self.conn.commit()
        self.curs.execute("LISTEN blue_live_target;")
        self.conn.commit()
        self.logger = logging.getLogger(__name__)

    def run(self):
        conn = self.conn
        logger = self.logger
        logger.info(
            "Waiting for notifications on channels.. blue_live_target AND red_live_target"
        )

        while self.alive.is_set():
            # print("target_notify_event not...in while loop ")
            if select.select([conn], [], [], 1) == ([], [], []):
                pass
            else:
                try:
                    conn.poll()
                except psycopg2.Error as e:
                    logger.info(e)
                    break
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    json_notice = json.loads(notify.payload)
                    snd_msg = json_notice
                    nbr_args = 1
                    args = [snd_msg]
                    response = requestwrapper.RequestWrapper("db_update", nbr_args, args)
                    response_json = json.dumps(response.__dict__)
                    self.queue.put(response_json)

        self.logger.info(
            "........................ReplayTargetNotifyRunnerClass: exiting WHILE loop"
        )

    def stop_targets_replay(self):
        self.logger.info(
            "........................ReplayTargetNotifyRunnerClass: stop_targets_replay called"
        )
        self.conn.commit()
        self.curs.close()
        self.conn.close()
        self.alive.clear()
        self.logger.info(
            "........................ReplayTargetNotifyRunnerClass: stop_targets_replay finised"
        )

  