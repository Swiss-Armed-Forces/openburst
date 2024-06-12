""" 
openburst pcl detection reader for Stone Soup. 
This allows reading pcl detections from openburst postgres DB for Stone Soup integration.
Stonesoup package should be installed.
"""

import psycopg2
import time
import datetime
import matplotlib.pyplot as plt
import time

from openburst.functions import dbfunctions
from openburst.functions import basefunctions

from stonesoup.reader.base import Reader, DetectionReader
from stonesoup.buffered_generator import BufferedGenerator
from stonesoup.types.detection import Detection

class _OpenburstPCLReader(Reader):
    """Openburst PCL detections reader

    This reader uses the postgreSQL python API
    to fetch pcl detections data.

    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timestep = 1000 # ms

    def data_gen(self):
        try:
            conn = dbfunctions.connect_to_db() 
            cur = conn.cursor()
        except Exception:
            print("Error: openburst postgreSQL connection error")
            
        while True:
            detections = []
            start_time =  int(round(time.time() * 1000)) # ms
            if cur is None:
                raise ValueError("Error: connection to openburst DB not open!")  
            
            cur.execute("""SELECT * from blue_live.pcl_detection;""",)
            conn.commit()
            rows = cur.fetchall()
            print("----------- checking detections --------")
            for i, row in enumerate(rows):
                detections.append(row)
                
            yield detections
            while ((start_time + self.timestep) > int(round(time.time() * 1000))):
                time.sleep(0.1)
                    
class OpenBurstPCLDetectionReader(_OpenburstPCLReader, DetectionReader):
    """OpenBurst PCL detection reader

    This reader uses the postgreSQL python API
    to fetch pcl detections data.


    """

    @BufferedGenerator.generator_method
    def detections_gen(self):
        for pcl_detections in self.data_gen():
            curr_time = basefunctions.get_time()
            # returns utcnow, pcl_det, pcl_det_time_ms_after_midnight
            yield {(curr_time, Detection(pcl_det, pcl_det[3])) for pcl_det in pcl_detections} 

if __name__ == "__main__":
    fig = plt.figure()
    ax1 = fig.add_subplot(1,1,1)
    plt.axis([0,45, 0, 50])

    fig.show() #shows the figure object

    reader = OpenBurstPCLDetectionReader()
    for n, (detections) in enumerate(reader):
        for pcl_det in detections:
            print("range, doppler = ", pcl_det[1].state_vector[6], pcl_det[1].state_vector[7])
            ax1.plot(float(pcl_det[1].state_vector[6]), float(pcl_det[1].state_vector[7]), 'b.')
    
            fig.canvas.draw()
            fig.canvas.flush_events()
