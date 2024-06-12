"""Module providing a class for postgresql DB access"""

import psycopg2
from psycopg2.extensions import AsIs

from openburst.constants import openburst_config
from openburst.constants import pclconstants
from openburst.functions.basefunctions import get_time

class DbConnector():
    """Class for handling all openburst postgresql DB accesses"""

    def __init__(self, logger, conn_name):
        self.logger = logger
        self.conn_name = conn_name
        self.connect_to_db() # initialize self.conn (connection class intantiation); t
        # cursor class is not reeintrant and will not be instantiated
        

    def __del__(self):
        if self.conn is not None:
            self.conn.close()
            self.logger.info("-- destroyed DB connection for  %s", self.conn_name)
        

    def connect_to_db(self):
        """Function for connecting to openburst postgresSQL DB"""
        self.logger.info("**** connecting to DB for  %s", self.conn_name)
        try:
            self.logger.info(
                ">>>>>>>>>>>>>>>>>>> persistant connection to To DB: %s, %s, %s, %s ",
                openburst_config.BURST_DB_NAME,
                openburst_config.BURST_DB_SERVER_USERNAME,
                openburst_config.BURST_DB_SERVER_IP,
                openburst_config.BURST_DB_SERVER_PASSWORD,
            )
            self.conn = psycopg2.connect(
                "dbname=%s user=%s host=%s password=%s"
                % (
                    openburst_config.BURST_DB_NAME,
                    openburst_config.BURST_DB_SERVER_USERNAME,
                    openburst_config.BURST_DB_SERVER_IP,
                    openburst_config.BURST_DB_SERVER_PASSWORD,
                )
            )
            # Setting auto commit to True 
            self.conn.autocommit = True
            self.logger.info("++++++ sucessfully opened DB connection for  %s", self.conn_name)
        except psycopg2.Error:
            self.logger.error("...unable to connect to the psql DB", exc_info=True)



    def trigger_rads_update(self, team):
        """Function for triggering the radar table"""
        self.logger.info("::::::::::::: starting trigger_rads_update")
        table_name = "blue_live.rad"
        if team == "blue":
            table_name = "blue_live.rad"
        elif team == "red":
            table_name = "red_live.rad"

        with self.conn.cursor() as cur:
            cur.execute("""UPDATE %s SET update_time=%s;""", (AsIs(table_name), -1))

        self.logger.info("::::::::::::: finished trigger_rads_update")

    def write_rad_max_range(self, rad_id, max_range, team):
        """Function for twriting radar maximum range"""
        table_name = "blue_live.rad"
        if team == "blue":
            table_name = "blue_live.rad"
        elif team == "red":
            table_name = "red_live.rad"
        # check if this rad already exists
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT * FROM %s WHERE id_nr = %s;""",
                (
                    AsIs(table_name),
                    rad_id,
                ),
                )
            if cur.fetchone() is not None:  # rad exists
                cur.execute(
                    """UPDATE %s SET max_detection_range=%s WHERE id_nr = %s;""",
                    (AsIs(table_name), max_range, rad_id),
                )

    def remove_table_row(self, _, id_nr, table):
        """Function for removing row from DB table"""
        with self.conn.cursor() as cur:
            cur.execute("""DELETE FROM %s WHERE id_nr =%s;""", (AsIs(table), id_nr))

    

    def write_pcl_rx(self, team, rad):
        """! update PCL Rx to DB"""
        table_name = "blue_live.pcl_rx"
        if team == "blue":
            table_name = "blue_live.pcl_rx"
        elif team == "red":
            table_name = "red_live.pcl_rx"

        # rx_id, name, team,lat, lon, status, masl, ahmagl, signal_type, bandwidth, horiz_diagr_att, vert_diagr_att, gain, losses, temp_sys, limit_distance, update_time
        # check if this rad already exists
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT * FROM %s WHERE name = %s;""",
                (
                    AsIs(table_name),
                    rad.name,
                ),
            )          
            if cur.fetchone() is not None:  # rad exists
                self.logger.info(
                    "pcl rx exists..updating, txCallSigns = %s", rad.txcallsigns
                )
                cur.execute(
                    """UPDATE %s SET rx_id=%s, status=%s, lat=%s, lon=%s, bandwidth=%s, masl=%s, ahmagl=%s, horiz_diagr_att=%s, vert_diagr_att=%s, gain=%s, losses=%s, temp_sys=%s, limit_distance=%s, update_time=%s, signal_type=%s, team=%s, txcallsigns=%s WHERE name = %s;""",
                    (
                        AsIs(table_name),
                        rad.rx_id,
                        rad.status,
                        rad.lat,
                        rad.lon,
                        rad.bandwidth,
                        rad.masl,
                        rad.ahmagl,
                        rad.horiz_diagr_att,
                        rad.vert_diagr_att,
                        rad.gain,
                        rad.losses,
                        rad.temp_sys,
                        rad.limit_distance,
                        rad.update_time,
                        rad.signal_type,
                        team,
                        rad.txcallsigns,
                        rad.name,
                    ),
                )        
            else:
                
                cur.execute(
                    """INSERT INTO %s VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                    (
                        AsIs(table_name),
                        rad.rx_id,
                        rad.name,
                        team,
                        rad.lat,
                        rad.lon,
                        rad.status,
                        rad.masl,
                        rad.ahmagl,
                        rad.signal_type,
                        rad.bandwidth,
                        rad.horiz_diagr_att,
                        rad.vert_diagr_att,
                        rad.gain,
                        rad.losses,
                        rad.temp_sys,
                        rad.limit_distance,
                        -1,
                        rad.txcallsigns,
                    ),
                )

    def write_pcl_tx(self, team, tx):
        """! update PCL Tx to DB"""
        table_name = "blue_live.pcl_tx"
        if team == "blue":
            table_name = "blue_live.pcl_tx"
        elif team == "red":
            table_name = "red_live.pcl_tx"
 
        if tx.erp_v == "UNDEFINED":
            tx.erp_v = -1
        if tx.erp_h == "UNDEFINED":
            tx.erp_h = -1

        # tx_id, callsign, sitename, team, lat, lon, status, masl, ahmagl, signal_type, freq, erp_h, erp_v, bandwidth, horiz_diagr_att, vert_diagr_att, pol

        # check if this tx already exists
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT * FROM %s WHERE callsign = %s;""",
                (
                    AsIs(table_name),
                    tx.callsign,
                ),
            )         
            if cur.fetchone() is not None:  # tx exists
                self.logger.info(
                    "pcl tx exists..updating tx with callsign = %s", tx.callsign
                )
                cur.execute(
                    """UPDATE %s SET sitename=%s, team=%s, lat=%s, lon=%s, status=%s, masl=%s, ahmagl=%s, signal_type=%s, freq=%s, erp_h=%s, erp_v=%s, bandwidth=%s, horiz_diagr_att=%s, vert_diagr_att=%s, pol=%s WHERE callsign = %s;""",
                    (
                        AsIs(table_name),
                        tx.sitename,
                        team,
                        tx.lat,
                        tx.lon,
                        tx.status,
                        tx.masl,
                        tx.ahmagl,
                        tx.signal_type,
                        tx.freq,
                        tx.erp_h,
                        tx.erp_v,
                        tx.bandwidth,
                        tx.horiz_diagr_att,
                        tx.vert_diagr_att,
                        tx.pol,
                        tx.callsign,
                    ),
                )             
            else:
                # logging.getLogger(__name__).info("inserting new row with id_nr: ", rad.id_nr)
                cur.execute(
                    """INSERT INTO %s VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                    (
                        AsIs(table_name),
                        tx.tx_id,
                        tx.callsign,
                        tx.sitename,
                        team,
                        tx.lat,
                        tx.lon,
                        tx.status,
                        tx.masl,
                        tx.ahmagl,
                        tx.signal_type,
                        tx.freq,
                        tx.erp_h,
                        tx.erp_v,
                        tx.bandwidth,
                        tx.horiz_diagr_att,
                        tx.vert_diagr_att,
                        tx.pol,
                    ),
                )
                
    def write_rad(self, team, rad):
        """!  update Active radar to DB"""
        table_name = "blue_live.rad"
        if team == "blue":
            table_name = "blue_live.rad"
        elif team == "red":
            table_name = "red_live.rad"
  
        # id_nr | name | status | lat | lon | power | antenna_diam | freq | pulse_width | cpi_pulses | bandwidth | pfa | rotation_time | category | min_elevation | max_elevation | orientation | horiz_aperture | min_detection_range | max_detection_range | min_detection_height | max_detection_height | min_detection_tgt_speed | max_detection_tgt_speed | update_time | team
        # check if this rad already exists
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT * FROM %s WHERE id_nr = %s;""",
                (
                    AsIs(table_name),
                    rad.id_nr,
                ),
            )
            
            if cur.fetchone() is not None:  # rad exists
                cur.execute(
                    """UPDATE %s SET name=%s, status=%s, lat=%s, lon=%s, power=%s, antenna_diam=%s, freq=%s, pulse_width=%s, cpi_pulses=%s, bandwidth=%s, pfa=%s, rotation_time=%s, category=%s, min_elevation=%s, max_elevation=%s, orientation=%s, horiz_aperture=%s, min_detection_range=%s, max_detection_range=%s, min_detection_height=%s, max_detection_height=%s, min_detection_tgt_speed=%s, max_detection_tgt_speed=%s, team=%s WHERE id_nr = %s;""",
                    (
                        AsIs(table_name),
                        rad.name,
                        rad.status,
                        rad.lat,
                        rad.lon,
                        rad.power,
                        rad.antenna_diam,
                        rad.freq,
                        rad.pulse_width,
                        rad.cpi_pulses,
                        rad.bandwidth,
                        rad.pfa,
                        rad.rotation_time,
                        rad.category,
                        rad.min_elevation,
                        rad.max_elevation,
                        rad.orientation,
                        rad.horiz_aperture,
                        rad.min_detection_range,
                        rad.max_detection_range,
                        rad.min_detection_height,
                        rad.max_detection_height,
                        rad.min_detection_tgt_speed,
                        rad.max_detection_tgt_speed,
                        team,
                        rad.id_nr,
                    ),
                )
                
            else:
                # logging.getLogger(__name__).info("inserting new row with id_nr: ", rad.id_nr)
                cur.execute(
                    """INSERT INTO %s VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);""",
                    (
                        AsIs(table_name),
                        rad.id_nr,
                        rad.name,
                        rad.status,
                        rad.lat,
                        rad.lon,
                        rad.power,
                        rad.antenna_diam,
                        rad.freq,
                        rad.pulse_width,
                        rad.cpi_pulses,
                        rad.bandwidth,
                        rad.pfa,
                        rad.rotation_time,
                        rad.category,
                        rad.min_elevation,
                        rad.max_elevation,
                        rad.orientation,
                        rad.horiz_aperture,
                        rad.min_detection_range,
                        rad.max_detection_range,
                        rad.min_detection_height,
                        rad.max_detection_height,
                        rad.min_detection_tgt_speed,
                        rad.max_detection_tgt_speed,
                        -1,
                        team,
                    ),
                )
                
    def trigger_pcl_rx(self, team):
        """!  triggers an update of PCL rx"""
        table_name = "blue_live.pcl_rx"
        tx_table_name = "blue_live.pcl_tx"
        if team == "blue":
            table_name = "blue_live.pcl_rx"
            tx_table_name = "blue_live.pcl_tx"
        elif team == "red":
            table_name = "red_live.pcl_rx"
            tx_table_name = "red_live.pcl_tx"

        with self.conn.cursor() as cur:
            cur.execute("""UPDATE %s SET update_time=%s;""", (AsIs(table_name), -1))
            # now also trigger the Tx for this each Rx
            cur.execute("""SELECT * FROM %s;""", (AsIs(table_name),))
            rxs = cur.fetchall()
        i = 0
        while i < len(rxs):
            curr_rx = rxs[i]
            callsigns = (curr_rx[17]).split(",")
            j = 0
            while j < len(callsigns):
                with self.conn.cursor() as cur:
                    cur.execute(
                        """SELECT * FROM %s WHERE callsign = %s;""",
                        (
                            AsIs(tx_table_name),
                            callsigns[j],
                        ),
                    )            
                    curr_tx = cur.fetchone()
                    if curr_tx is not None:
                        cur.execute(
                            """UPDATE %s SET status=%s WHERE callsign=%s;""",
                            (AsIs(tx_table_name), 1, curr_tx[1]),
                        )                    
                    j = j + 1
            i = i + 1

    def trigger_targets(self, team):
        """!  trigger targets"""
        table_name = "blue_live.target"

        if "blue" in team:
            # print("team blue........")
            table_name = "blue_live.target"
        elif "red" in team:
            print("team red........")
            table_name = "red_live.target"
        # do som update
        with self.conn.cursor() as cur:
            cur.execute("""UPDATE %s SET update_time=%s;""", (AsIs(table_name), -1))    

    def write_pcl_dets(self, tup):
        """! adds a tuple of PCL detections to blue_live.pcl_detection"""
        # rx_id, tx_id, pcl_rx_name, pcl_tx_callsign,targ_id, det_time, range, doppler, tgt_lat, tgt_lon, tgt_height, recording_time, vx, vy, vz, velocity, bistatic_velocity, snr
        with self.conn.cursor() as cur:
            args_str = b",".join(
                cur.mogrify("(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", x)
                for x in tup
            )
            try:
                cur.execute(
                    b"INSERT INTO blue_live.pcl_detection VALUES "
                    + args_str
                    + b" ON CONFLICT (pcl_rx_name, pcl_tx_callsign,targ_id) "
                    b"DO UPDATE SET "
                    b"(rx_id, tx_id, pcl_rx_name, pcl_tx_callsign,targ_id, det_time, range, doppler, "
                    b"tgt_lat, tgt_lon, tgt_height, recording_time, vx, vy, vz, velocity, bistatic_velocity, snr) = "
                    b"(EXCLUDED.rx_id, EXCLUDED.tx_id, EXCLUDED.pcl_rx_name, EXCLUDED.pcl_tx_callsign, EXCLUDED.targ_id, "
                    b"EXCLUDED.det_time, EXCLUDED.range, EXCLUDED.doppler, EXCLUDED.tgt_lat, "
                    b"EXCLUDED.tgt_lon, EXCLUDED.tgt_height, EXCLUDED.recording_time, EXCLUDED.vx, EXCLUDED.vy, EXCLUDED.vz, EXCLUDED.velocity, EXCLUDED.bistatic_velocity, EXCLUDED.snr)"
                )
            except psycopg2.Error as e:
                self.logger.error(e)

    def write_rad_dets(self, tup):
        """! adds a tuple of detections to DB table blue_live.detection"""
        # targ_id, sensor_id, team, pd, plot, track, det_time, lat, lon, height, vx, vy, vz, cpx, cpy, cpz, cvx, cvy, cvz, recording_time
        with self.conn.cursor() as cur:
            args_str = b",".join(
                cur.mogrify(
                    "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    x,
                )
                for x in tup
            )
            try:
                cur.execute(
                    b"INSERT INTO blue_live.detection VALUES "
                    + args_str
                    + b" ON CONFLICT (targ_id, sensor_id) DO UPDATE SET (targ_id, sensor_id, team, pd, plot, track, det_time, lat, lon, height, vx, vy, vz, cpx, cpy, cpz, cvx, cvy, cvz, recording_time) = (EXCLUDED.targ_id, EXCLUDED.sensor_id, EXCLUDED.team, EXCLUDED.pd, EXCLUDED.plot, EXCLUDED.track, EXCLUDED.det_time, EXCLUDED.lat, EXCLUDED.lon, EXCLUDED.height, EXCLUDED.vx, EXCLUDED.vy, EXCLUDED.vz, EXCLUDED.cpx, EXCLUDED.cpy, EXCLUDED.cpz, EXCLUDED.cvx, EXCLUDED.cvy, EXCLUDED.cvz, EXCLUDED.recording_time)"
                )
                
            except psycopg2.Error as e:
                self.logger.error(e)


    def write_targets(self, tup):
        """!  inserts a tuple of target rows as batch to the db"""
        # target.id_nr, target.team, target.rcs, target.name, target.running, target.velocity, target.lat, target.lon, target.height, target.vx, target.vy, target.vz,  target.corridor_breadth, target.nofTargets, target.typed, target.threeD_waypoints_id, target.status, target.maneuvring, target.classification, target.waypoints, target.waypoints_index, target.update_time, target.terrainHeight, target.recording_time
        # there will be conflicts as we are sampling from a recording file with a certain sampling time
        with self.conn.cursor() as cur:
            args_str = b",".join(
                cur.mogrify(
                    "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    x,
                )
                for x in tup
            )
            cur.execute(
                b"INSERT INTO blue_live.target VALUES "
                + args_str
                + b" ON CONFLICT (id_nr, name) DO UPDATE SET (id_nr, team, rcs, name, running, velocity, lat, lon, height, vx, vy, vz,  corridor_breadth, nofTargets, typed, threeD_waypoints_id, status, maneuvring, classification, waypoints, waypoints_index, update_time, terrainHeight, recording_time) = (EXCLUDED.id_nr, EXCLUDED.team, EXCLUDED.rcs, EXCLUDED.name, EXCLUDED.running, EXCLUDED.velocity, EXCLUDED.lat, EXCLUDED.lon, EXCLUDED.height, EXCLUDED.vx, EXCLUDED.vy, EXCLUDED.vz,  EXCLUDED.corridor_breadth, EXCLUDED.nofTargets, EXCLUDED.typed, EXCLUDED.threeD_waypoints_id, EXCLUDED.status, EXCLUDED.maneuvring, EXCLUDED.classification, EXCLUDED.waypoints, EXCLUDED.waypoints_index, EXCLUDED.update_time, EXCLUDED.terrainHeight, EXCLUDED.recording_time)"
            )
            

    
            
    def remove_inactive_replay_targets(self, delta_t, curr_time):
        """! removes replay targets that are inactive """
        with self.conn.cursor() as cur:
            cur.execute(
                """DELETE FROM %s WHERE (%s - update_time) > %s;""",
                (AsIs("blue_live.target"), curr_time, delta_t),
            )
            
    def remove_rad_detections(self, rad_id):
        """! removes all rad detections"""
        with self.conn.cursor() as cur:
            try:
                cur.execute(
                    """DELETE FROM %s WHERE sensor_id = %s;""",
                    (
                        AsIs("blue_live.detection"),
                        rad_id,
                    ),
                )      
            except psycopg2.Error as e:
                self.logger.error(e)


    def remove_inactive_pcl_detections(self, curr_time, rx_id):
        """! removes all pcl detections of given rx that are inactive"""
        with self.conn.cursor() as cur:
            try:
                cur.execute(
                    """DELETE FROM %s WHERE ((%s - det_time) > %s) AND (rx_id = %s);""",
                    (AsIs("blue_live.pcl_detection"), curr_time, pclconstants.PCL_PLOT_LIFETIME * 1000, rx_id),
                )
                
            except psycopg2.Error as e:
                self.logger.error(e)


    def remove_pcl_rx_tx_detections(self, rx_name, tx_callsign):
        """! removes all PCL detections for a given rx-tx pair"""
        with self.conn.cursor() as cur:
            cur.execute(
                """DELETE FROM %s WHERE pcl_rx_name = %s AND pcl_tx_callsign = %s ;""",
                (AsIs("blue_live.pcl_detection"), str(rx_name), str(tx_callsign)),
            )

    def remove_inactive_rad_detections(self, rad_id, rot_time):
        """! removes all detections associated to no track/plot and pd=0, or detections older than 3 times radar rotation time"""

        # delete all detection which do not have a track anymore and not plot to reduce
        with self.conn.cursor() as cur:
            try:
                cur.execute(
                    """DELETE FROM %s WHERE sensor_id = %s AND track<=0 AND plot<=0 AND pd<=0.0;""",
                    (
                        AsIs("blue_live.detection"),
                        rad_id,
                    ),
                )

                # delete all detections that are older than 3 time rad rotation time
                curr_time = get_time()
                cur.execute(
                    """DELETE FROM %s WHERE sensor_id = %s AND ((%s - det_time) > 5000*%s);""",
                    (
                        AsIs("blue_live.detection"),
                        rad_id,
                        curr_time,
                        rot_time,
                    ),
                )
                
            except psycopg2.Error as e:
                self.logger.error(e)

    def get_detection_statistics(self):
        """! returns statistcs of detections"""

        targ_table = "blue_live.target"
        det_table = "blue_live.detection"

        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT targ_id FROM %s WHERE (pd>=0.8);""", (AsIs(det_table),)
            )  # remove duplicate targ_ids, i.e. we only want a target to be detected once           
            dets = cur.fetchall()
            cur.execute("""SELECT * FROM %s WHERE status=1;""", (AsIs(targ_table),))        
            objs = cur.fetchall()
            if len(objs) > 0:
                det_rate = (
                    100.0 * float(len(dets)) / float(len(objs))
                )  # detection rate in percentage
            else:
                det_rate = 0
            return [det_rate, len(objs)]


    def get_all_pcl_tx(self, team):
        """! returns all pcl tx"""
        table_name = "blue_live.pcl_tx"
        if team == "blue":
            table_name = "blue_live.pcl_tx"
        elif team == "red":
            table_name = "red_live.pcl_tx"

        with self.conn.cursor() as cur:
            cur.execute("""SELECT * FROM %s;""", (AsIs(table_name),))
            txs = cur.fetchall()
            return txs


    def get_all_pcl_tx_for_rx(self, team, rx):
        """! returns all pcl tx for given rx"""
        tx_callsigns = rx[17]
        table_name = "blue_live.pcl_tx"
        if team == "blue":
            table_name = "blue_live.pcl_tx"
        elif team == "red":
            table_name = "red_live.pcl_tx"

        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT * FROM %s WHERE position(callsign in %s)>0;""",
                (
                    AsIs(table_name),
                    tx_callsigns,
                ),
            )  
            txs = cur.fetchall()
            return txs


    def get_all_pcl_rx(self, team):
        """! returns all pcl rx"""
        table_name = "blue_live.pcl_rx"
        if team == "blue":
            table_name = "blue_live.pcl_rx"
        elif team == "red":
            table_name = "red_live.pcl_rx"

        with self.conn.cursor() as cur:
            cur.execute("""SELECT * FROM %s;""", (AsIs(table_name),))
            rxs = cur.fetchall()
            return rxs

    def get_all_rads(self, team):
        """! returns all rads"""
        table_name = "blue_live.rad"
        if team == "blue":
            table_name = "blue_live.rad"
        elif team == "red":
            table_name = "red_live.rad"

        with self.conn.cursor() as cur:
            cur.execute("""SELECT * FROM %s;""", (AsIs(table_name),)) 
            rads = cur.fetchall()
            return rads


    def deactivate_rad(self, id_nr, team):
        """! deactivates a given rad"""
        table_name = "blue_live.rad"
        if team == "blue":
            table_name = "blue_live.rad"
        elif team == "red":
            table_name = "red_live.rad"
        
        with self.conn.cursor() as cur:
            cur.execute(
                """UPDATE %s SET status = %s WHERE id_nr = %s;""", (AsIs(table_name), 0, id_nr)
            )

    def activate_rad(self, id_nr, team):
        """! activates a given rad"""
        table_name = "blue_live.rad"
        if team == "blue":
            table_name = "blue_live.rad"
        elif team == "red":
            table_name = "red_live.rad"
        
        with self.conn.cursor() as cur:
            cur.execute(
                """UPDATE %s SET status = %s WHERE id_nr = %s;""", (AsIs(table_name), 1, id_nr)
            )

    def get_all_detections(self, team):
        """! returns all entries from the detection table"""
        table_name = "blue_live.detection"
        if team == "blue":
            table_name = "blue_live.detection"
        elif team == "red":
            table_name = "red_live.detection"

        with self.conn.cursor() as cur:
            cur.execute("""SELECT * FROM %s ;""", (AsIs(table_name),))
            detections = cur.fetchall()
            return detections


    def get_pcl_tx_coordinates(self, callsign):
        """! returns pcl tx lat,lon and alt"""
        tgt_table = "blue_live.pcl_tx"
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT lat,lon,masl,ahmagl FROM %s WHERE (callsign = %s);""", (AsIs(tgt_table), callsign)
            )         
            try:
                res = cur.fetchone()
                return (res[0], res[1], res[2], res[3])
            except psycopg2.Error as e:
                self.logger.error(e)
                return None

    def get_pcl_rx_coordinates(self, name):
        """! returns pcl rx lat,lon and alt"""
        tgt_table = "blue_live.pcl_rx"    
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT lat,lon,masl,ahmagl FROM %s WHERE (name = %s);""", (AsIs(tgt_table), name)
            )
            try:
                res = cur.fetchone()
                return (res[0], res[1], res[2], res[3])
            except psycopg2.Error as e:
                self.logger.error(e)
                return None
        

    def get_targets(self, team):
        """! returns all targets"""
        table_name = "blue_live.target"
        if team == "blue":
            table_name = "blue_live.target"
        elif team == "red":
            table_name = "red_live.target"

        with self.conn.cursor() as cur:     
            try:
                cur.execute(
                    """SELECT * FROM %s WHERE team = %s;""",
                    (
                        AsIs(table_name),
                        team,
                    ),
                ) 
                targets = cur.fetchall()

                return targets
            except psycopg2.Error as e:
                self.logger.error(e)
                return None


    def remove_all_pcl_detections(self, team):
        """! removes all pcl detections"""
        table_name = "blue_live.pcl_detection"
        if team == "blue":
            table_name = "blue_live.pcl_detection"
        elif team == "red":
            table_name = "red_live.pcl_detection"

        with self.conn.cursor() as cur:
            cur.execute("""DELETE FROM %s """, (AsIs(table_name),))

    def remove_all_rad_detections(self, team):
        """! removes all rad detections"""
        table_name = "blue_live.detection"
        if team == "blue":
            table_name = "blue_live.detection"
        elif team == "red":
            table_name = "red_live.detection"

        with self.conn.cursor() as cur:
            try:
                cur.execute(
                    """UPDATE %s SET pd = %s, plot = %s, track = %s WHERE sensor_id < 11112""",
                    (AsIs(table_name), 0, 0, 0),
                )
            except psycopg2.Error as e:
                self.logger.error(e)


