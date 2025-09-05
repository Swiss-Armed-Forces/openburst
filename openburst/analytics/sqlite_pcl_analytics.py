"""
    Module providing an example of exporting openBURST simulation data for analytics.
    passive radar detections are plotted and exported. 

    This module exports PCL detections from openBURST postgreSQL DB
    to an sqlite file for sharing. 
    
    creates one sqlite file with the following tables:
        - PCL detection (table_name: pcl_plot)
        - PCL transmitters (table_name: transmitter)
        - PCL receivers (table_name: receiver)

    Further, a live bistatic range-Doppler map is plotted and 
    saved as a png file. 

    The Listen/Notify mechanism of postgreSQL is used to note changes 
    in the pcl_detection table during the simulation. 

"""

import select
import json
import sqlite3
import psycopg2

from openburst.functions import dbfunctions

plot_id = 0 # pcl plot table has no id, so we have on here

def pcl_det_to_sqlite(pcl_det_payload, sqcur, sqcon, plotid):
    """
    function to write sqlite db with a given PCL detection
    """
    
    # write the openburst pcl detections
    payload = json.loads(pcl_det_payload)
    rx_id = payload.get("data").get("rx_id")
    tx_id = payload.get("data").get("tx_id")
    targ_id = payload.get("data").get("targ_id")
    bi_range = payload.get("data").get("range") * 1000 # bistatic range in [m] (see pcldetectionrunner.py)
    bistatic_doppler = payload.get("data").get("doppler") # [dB]
    #det_time = payload.get("data").get("det_time") # [milliseconds since the UNIX epoch January 1, 1970 00:00:00 UTC)
    det_time = payload.get("data").get("target_time") # [milliseconds since the UNIX epoch January 1, 1970 00:00:00 UTC), we are using the target tables update_time and not the sensor time
    
    #det_time = math.floor(float(det_time)/1000.0) # [s] floored
    #bi_range = payload.get("data").get("range")
    snr = payload.get("data").get("snr") # [db] 
    bistatic_velocity = payload.get("data").get("bistatic_velocity") # [m/s]
    query = """INSERT INTO plot VALUES (?,?,?,?,?,?,?,?,?)"""
    # needed: id INTEGER, range REAL, velocity REAL, SNR REAL, rangeStd REAL, velocityStd REAL, rxId INTEGER, txId INTEGER, timestamp INTEGER NOT NULL, 
    dat = ([plot_id, bi_range, bistatic_velocity, snr, 0, 0, rx_id, tx_id, det_time])
    #print("sqllite_pcl_analytics pcl_dat: ", dat)
    sqcur.execute(query, dat)
    sqcon.commit()
    print(dat)
   

if __name__ == "__main__":
    ## start a sqlite db
    sqlite_con = sqlite3.connect("passive_data.db")
    sqlite_cur = sqlite_con.cursor()

    ## create a pcl plots table

    plots_table = """
        CREATE TABLE IF NOT EXISTS plot (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            range REAL NOT NULL,       
            velocity REAL NOT NULL,
            SNR REAL,
            rangeStd REAL,
            velocityStd REAL,
            rxId INTEGER,
            txId INTEGER,
            timestamp INTEGER NOT NULL,
            FOREIGN KEY(rxId) REFERENCES receiver(id)
            FOREIGN KEY(txId) REFERENCES transmitter(id)
        );"""

   
    sqlite_cur.execute(plots_table)

    transmitter_table = """
        CREATE TABLE IF NOT EXISTS transmitter (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            longitude REAL NOT NULL,
            latitude REAL NOT NULL,
            altitude REAL NOT NULL,
            frequency REAL NOT NULL,
            bandwidth REAL NOT NULL,
            type TEXT NOT NULL,
            name TEXT NOT NULL
        );"""
  
    sqlite_cur.execute(transmitter_table)

    ## create a receiver table
    receiver_table = """
        CREATE TABLE IF NOT EXISTS receiver (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            longitude REAL NOT NULL,
            latitude REAL NOT NULL,
            altitude REAL NOT NULL,	
            name TEXT NOT NULL,	
            direction REAL NOT NULL,
            beamwidth REAL NOT NULL
        );"""
    sqlite_cur.execute(receiver_table)

    # now listen on openburst pcl detections table and write detections and targets 
    conn = dbfunctions.connect_to_db()
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    curs = conn.cursor()

    # read from postgresql and write to sqlite all transmitters
    curs.execute("SELECT * FROM blue_live.pcl_tx")
    for tx in curs.fetchall():
        print("tx = ", tx)
        sql = """INSERT OR REPLACE INTO transmitter VALUES (?,?,?,?,?,?,?,?)"""
        # postgresql table: 0: tx_id, 1: callsign, 2: sitename, 3: team, 4: lat, 5: lon, 6: status, 7: masl, 8: ahmagl, 9: signal_type, 10: freq, 11: erp_h, 12: erp_v, 13: bandwidth, 14: horz_att, 15: vert_att, 16: pol
        # needed: id, lon, lat, alt, freq, bw, type, name  
        data = ([tx[0], tx[5], tx[4], tx[7]+tx[8], tx[10], tx[13], tx[9], tx[1]])
        #print("tx_data = ", data)
        sqlite_cur.execute(sql, data)
        sqlite_con.commit()

    # read from postgresql and write to sqlite all receivers
    curs.execute("SELECT * FROM blue_live.pcl_rx")
    for rx in curs.fetchall():
        sql = """INSERT OR REPLACE INTO receiver VALUES (?,?,?,?,?,?,?)"""
        # postgresql table: 0:rx_id, 1: name, 2: team, 3: lat, 4: lon, 5: status, 6: masl, 7: ahmagl
        # 8: signal_type, 9: bw, 10: h_atten, 11: v_atten, 12: gain, 13: losses, 14: temp_sys, 15: limit_dist
        # 16: update_time, 17: tx_callsigns
        # needed: id, lon, lat, alt, name, direction, beamwidth

        data = ([rx[0], rx[4], rx[3], rx[6]+rx[7], rx[1],  0, rx[9]]) # we are using bandwidth (and not beamwidth)
        sqlite_cur.execute(sql, data)
        sqlite_con.commit()  

    listen_query = "LISTEN " + "blue_live_pcl_detection" + ";"
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
                    pcl_det_to_sqlite(notify.payload, sqlite_cur, sqlite_con, plot_id)
                    plot_id = plot_id + 1
                
                    

    except KeyboardInterrupt:

        sqlite_con.commit()
        sqlite_cur.close()
        sqlite_con.close()

        conn.commit()
        curs.close()
        conn.close()

        ## now read and plot databank to check if sqlite db file was written
        print("-------------------------- printing and plotting all PCL detections in sqlite DB------------ ")
        con = sqlite3.connect("passive_data.db")
        cur = con.cursor()
        res = cur.execute("SELECT * FROM plot")
        for row in res:
            print(row)

        print("-------------------------- printing and plotting all receivers sqlite DB------------ ")
        res = cur.execute("SELECT * FROM receiver")
        for row in res:
            print(row)

        print("-------------------------- printing and plotting all transmitters sqlite DB------------ ")
        res = cur.execute("SELECT * FROM transmitter")
        for row in res:
            print(row)
    
        con.close()

        # save range-dopller plot
        # plt.savefig("range_doppler_map.png") 