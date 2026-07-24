"""
class for bistatic sensor detection frame handling
https://pypi.org/project/sort-tracker/
"""

from openburst.types import sort
import numpy as np
from openburst.constants import pclconstants
from openburst.functions import socketfunctions
import math 
import time
import multiprocessing as mp
import random

v_association_bbox = 10 # a vel window of this size will be used for data association
range_association_bbox = 1000 # a range window of this size will be used for data association
max_age = 20 # wait this many frames without update (i.e. max age)
min_hits = 2 # before instantiating a track (i.e min age)


class SensorFrame:
    """
    class for handling PCL sensor detection frame activities
    """
    def __init__(self, id_nr):
        self.id = id_nr
        
        self.frame = None
        self.reset_frame() 
        self.tracker = sort.Sort(max_age, min_hits)
        self.tracked = None
        self.live_bist_track_stream_client = socketfunctions.get_client_socket()
       
        self.tr_time = -1
        self.tr_send_time = 0
        self.queue = mp.Queue()
        
    def insertnoise(self):
        """
        inserts noise into the detections frame
        """
        for i in range(int(self.frame.size * pclconstants.NOISE_RATE)):
            row_ind = random.randint(0, self.frame.shape[0]-1)
            col_ind = random.randint(0, self.frame.shape[1]-1)
            self.frame[row_ind, col_ind] = 1
            



    def callback(self):
        """
        this function should be called back regularly
        """
        while True:
            self.tr_time += pclconstants.PCL_FRAME_MAX_AGE
            #print("called back: ", self.id, ", tr_time: ", self.tr_time)
            while not self.queue.empty():
                msg = self.queue.get()
                #print("self.id: ", self.id, ", queue elem: ", msg[0], msg[1], msg[2])
                plot_time = float(msg[0])
                bi_range = float(msg[1])
                bi_vel = float(msg[2])
                self.insert_bistatic_plot_to_frame(plot_time, bi_range, bi_vel)

            # update all tracks
            track_bbs_ids = self.track_update()

            # check if we need to send the tracks
            delta_track_send_time = self.tr_time - self.tr_send_time
            if (delta_track_send_time > pclconstants.PCL_SEND_BIST_TRACK_INTERVAL):
                if (track_bbs_ids is not None):
                    print("############################################sending to cartesian tracker...........: ", self.id)
                    self.send_frame(track_bbs_ids)
                    self.tr_send_time = self.tr_time

            # sleep
            time.sleep(pclconstants.PCL_FRAME_MAX_AGE)
           
        

    def send_to_cartesian_tracker(self, tr_time, tr_id, rn, vel, targ_id):
        """
        send live bistatic tracks over socket to cartesian tracker
        """
        live_stream_str = "PLOT " + str(tr_time) + "," + self.id + "," + str(rn) + "," + str(vel) + "," + str(targ_id)
        socketfunctions.send_client_bistatic_track_data(self.live_bist_track_stream_client, live_stream_str) 

    def set_detection_in_frame(self, bi_range, bi_vel):
        """
        sets the array element in the frame
        """
        #bi_vel = bi_vel + pclconstants.PCL_MAX_V # makes computing easier as no negative vel
        a = int(pclconstants.PCL_MAX_V/pclconstants.V_BIN_SIZE)
        frame_x = 0
        if bi_vel >= 0: 
            frame_x = a + int(math.fabs(bi_vel) / pclconstants.V_BIN_SIZE) 
        else:
            frame_x = a - int(math.fabs(bi_vel) / pclconstants.V_BIN_SIZE) 
        
        
        #print("bi_vel, bin, a : ", bi_vel, frame_x, a)

        frame_y = int(bi_range/pclconstants.RANGE_BIN_SIZE)
        self.frame[frame_x, frame_y] = 1

    def reset_frame(self):
        """
        resets the sensors frame
        """
        self.frame =  np.zeros([int(pclconstants.PCL_MAX_V/pclconstants.V_BIN_SIZE)*2, int(pclconstants.PCL_MAX_RANGE_M/pclconstants.RANGE_BIN_SIZE)]) # create the zero matrix
        # noise
        if (pclconstants.NOISE_MODEL_ON):
            self.insertnoise()

        #self.latest_plot_time = -1.0

    def track_update(self):
        """
        updates the tracks of the frame
        """
        # track update
        # get the indices of the detections
        
        dots = np.argwhere(self.frame == 1)
        #print("dots = ", dots)
        detections = [0,0,0,0]
        got_plots = False

        a = int(pclconstants.PCL_MAX_V/pclconstants.V_BIN_SIZE)
        # insert detections into a bounding box array for SORT
        for u in dots:
            # sort needs a bounding box as detection
            try:
                if u[0] > a:
                    bistat_vel = (u[0] - a) * pclconstants.V_BIN_SIZE
                else:
                    bistat_vel = -1 * (a - u[0]) * pclconstants.V_BIN_SIZE
                
                bistat_range = u[1] * pclconstants.RANGE_BIN_SIZE
                #print("recomputed bi_vel, range: ", bistat_vel, bistat_range)
                newrow = [bistat_vel-int(v_association_bbox/2), bistat_range-int(range_association_bbox/2), bistat_vel+int(v_association_bbox/2), bistat_range+int(range_association_bbox/2)]
                detections = np.vstack([detections, newrow])
                got_plots = True
            except Exception as e:
                print("exception = ", e)

        #print("detections = ", detections)
        if (got_plots):
            track_bbs_ids = self.tracker.update(detections)
            # track_bbs_ids is a numpy array where each row contains a valid bounding box and track_id (last column)
            #print("***********sensor:  ", self.id, " ***************** #tracks =  ", len(track_bbs_ids))
            # reset frame
            self.reset_frame() 
            return track_bbs_ids

        else:
            self.reset_frame() 
            return None
        

    def send_frame(self, track_bbs_ids):
        """
        sends the sensors frame
        """
        # track_bbs_ids is a numpy array where each row contains a valid bounding box and track_id (last column)
        print("***********sensor:  ", self.id, " ***************** #tracks =  ", len(track_bbs_ids), ", tr_time: ", self.tr_time)
    
        for track in track_bbs_ids:
            #print("track = ", track, ", info = ", track[4], track[0:4])
            xy = sort.convert_bbox_to_z(track[0:4])
            #center = (xy[1],xy[0])
            center = (xy[1][0],xy[0][0])
            
            print("track id: ", str(int(track[4])), ", vel/range: ", center)
            # args: time[s], plot_id, range[m], vel[m/s], targ_id
            if (math.isnan(center[0]) or math.isnan(center[1])):
                continue
            else:
                self.send_to_cartesian_tracker(self.tr_time, int(track[4]), center[0], center[1], -1)
        
       

    def insert_bistatic_plot_to_frame(self, plot_time, bi_range, bi_vel):
        """
        inserts plot to frame
        """
        #print("frame id: ", self.id, ", plot received: ", plot_time, bi_range, bi_vel)

        
        self.tr_time = float(plot_time)
 
        # error
        if pclconstants.ERROR_MODEL_ON:
            range_error = random.gauss(mu=0.0,sigma=pclconstants.STD_DEV_BIST_RANGE_FM)
            vel_error = random.gauss(mu=0.0,sigma=pclconstants.STD_DEV_BIST_VEL_FM)
            print("error: ", range_error, vel_error)
        else:
            range_error = 0.0
            vel_error = 0.0

        bi_range += range_error
        bi_vel += vel_error

        # now place the new plot
        self.set_detection_in_frame(float(bi_range), float(bi_vel))
        
        

        
