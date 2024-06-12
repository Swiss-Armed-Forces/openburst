"""openburst pcl detection reader for Stone Soup. This allows reading pcl detections from openburst postgres DB for Stone Soup
"""

import time
from datetime import datetime, timezone
import logging
import psycopg2

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
        """ connects to DB and collects detections """
        try:
            conn = psycopg2.connect("dbname=red user=red3 host=localhost password=red")
            cur = conn.cursor()
        except psycopg2.Error as e:
            logging.getLogger(__name__).info(e)
            
        while True:
            detections = []
            start_time =  int(round(time.time() * 1000)) # ms
            if cur is None:
                raise ValueError("Error: connection to openburst DB not open!")  
            
            cur.execute("""SELECT * from blue_live.pcl_detection;""",)
            conn.commit()
            rows = cur.fetchall()
            print("----------- checking detections --------")
            for i in enumerate(rows):
                detections.append(rows[i])
                
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
        for detections in self.data_gen():
            curr_time = datetime.now(timezone.utc)
            yield {(curr_time, Detection(pcl_det, pcl_det[3])) for pcl_det in detections} # returns utcnow, pcl_det, pcl_det_time_ms_after_midnight