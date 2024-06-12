
import multiprocessing as mp
import tornado
import time
import logging

class Scheduler:
    """! scheduler will sent all entries in the queue every wait_time_secs through the given sock"""

    def __init__(self, sock, wait_time_secs):
        self.wait_time_secs = wait_time_secs
        self.sock = sock
        self.queue = mp.Queue()

    # the following will run asynchronously in regular intervals (wait_time_secs) to empty a queue that will be written by a regular process
    def schedule_func(self):
        # do something
        while not self.queue.empty():
            ret = None
            try:
                ret = self.queue.get()
                try:
                    #print(" ------------ scheduler queue writing: ", ret)
                    self.sock.write_message(ret)
                except Exception as e:
                    if ret is not None:
                        print(" +++++++++++++++++ scheduler queue adding due to exception: ", e)
                        self.queue.put(ret)
            except Exception as e:
                #print(" !!! scheduler queue exception: ", e)
                pass        

        # Schedule next cycle in wait_time_secs seconds (if wait_time_secs is set to -1 it exits)
        if self.wait_time_secs != -1.0:
            tornado.ioloop.IOLoop.instance().add_timeout(
                time.time() + self.wait_time_secs, lambda: self.schedule_func()
            )
        else:
            print("EXITING SCHEDULER as wait_time_secs set to -1")
            logging.getLogger("DEM").info(
                "==================== >EXITING SCHEDULER as wait_time_secs set to -1"
            )
            return
