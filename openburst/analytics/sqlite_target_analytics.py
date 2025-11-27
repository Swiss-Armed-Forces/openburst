"""
    Module providing an example of exporting openBURST simulation data for analytics.
    target data are plotted and exported. 

    This module exports target simulation data from openBURST postgreSQL DB
    to an sqlite file for sharing. 
    
    creates one sqlite file with the following tables:
        - target positions ground truth (table_name: target)


"""
import math
import json
import sqlite3
import select
import psycopg2
from openburst.functions import dbfunctions
   

target_row = 0 

def target_to_sqlite(target_payload, sqcur, sqcon):
    """
    function to write sqlite db with a given target update
    """
    
    # write the openburst target 


    payload = json.loads(target_payload)

    query = """INSERT INTO target VALUES (?,?,?,?,?,?,?,?)"""
    # [target_id, det_time,target_lat, target_lon, target_height, alpha, target_speed]
    target_id = payload.get("data").get("id_nr")
    #det_time = payload.get("data").get("update_time") # update_time is the time when replay writes to DB
    det_time = payload.get("data").get("recording_time") # recording_time is the orginal target time


    target_lat = payload.get("data").get("lat")
    target_lon = payload.get("data").get("lon")
    target_height = payload.get("data").get("height")
    vx = payload.get("data").get("vx")
    vy = payload.get("data").get("vy")
    alpha = math.degrees(math.atan2(vx, vy))
    if alpha < 0:
        alpha = 360 + alpha # now alpha is on degrees from north
    target_speed = payload.get("data").get("velocity") # [km/h]
    target_speed_m_s = target_speed * 1000.0/3600 # [m/s]
    global target_row
    dat = ([target_row, target_id, det_time, target_lon, target_lat, target_height, alpha, target_speed_m_s ])
    target_row = target_row + 1
    #print("sqllite_pcl_analytics pcl_dat: ", dat)
    sqcur.execute(query, dat)
    sqcon.commit()
    print(dat)



if __name__ == "__main__":
    ## start a sqlite db
    sqlite_con = sqlite3.connect("target_data.db")
    sqlite_cur = sqlite_con.cursor()


    ## create a targets table (ground truth)
    ground_truth_targets_table = """
        CREATE TABLE IF NOT EXISTS target (
            row INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            id INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            longitude REAL NOT NULL,
            latitude REAL NOT NULL,
            altitude REAL NOT NULL,
            heading REAL NOT NULL,
            speed REAL NOT NULL
        );"""

    
    sqlite_cur.execute(ground_truth_targets_table)

    # now listen on openburst pcl detections table and write detections and targets 
    conn = dbfunctions.connect_to_db()
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    curs = conn.cursor()

    listen_query = "LISTEN " + "blue_live_target" + ";"
    curs.execute(listen_query)
    conn.commit()

    try:
        while True:
            if select.select([conn],[],[],1) == ([],[],[]):
                pass
            else:
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    target_to_sqlite(notify.payload, sqlite_cur, sqlite_con)
                    
                
    except KeyboardInterrupt:

        sqlite_con.commit()
        sqlite_cur.close()
        sqlite_con.close()

        conn.commit()
        curs.close()
        conn.close()

     