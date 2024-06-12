"""
    Module providing an example of exporting openBURST simulation data for analytis.
    passive radar detections are plotted and exported. 

    This module exports PCL detections from openBURST postgreSQL DB
    to an sqlite file for sharing. 
    
    creates one sqlite file with following tables:
        - PCL detection (table_name: pcl_plot)
        - target positions ground truth (table_name: target)
        - PCL transmitters (table_name: transmitter)
        - PCL receivers (table_name: receiver)

    Futher, a live bistatic range-Doppler map is plotted.
    In the end, the range-Doppler map ist saved as a png file. 

    The Listen/Notify mechanism of postgreSQL is used to note changes 
    in the pcl_detection table during the simulation. 

"""
import select
import json
import sqlite3
import psycopg2

import matplotlib.pyplot as plt
from openburst.functions import dbfunctions

plt.ion()

fig = plt.figure()
ax = fig.add_subplot(111)
ax.plot([], [], lw=2)
ax.set_ylim(-100, 100) # doppler [Hz]
ax.set_xlim(0, 100) # range [km]
plt.xlabel('bistatic range [km]') 
plt.ylabel('bistatic Doppler shift [Hz]') 
ax.grid()
range_data, doppler_data = [], []
line1, = ax.plot(range_data, doppler_data, 'r.')
plt.show()

def pcl_det_to_sqlite(pcl_det_payload, sqcur, sqcon, plotid):
    """
    function to write sqlite db with a given PCL detection
    """
    
    # write the openburst pc detections
    payload = json.loads(pcl_det_payload)
    rx_id = payload.get("data").get("rx_id")
    tx_id = payload.get("data").get("tx_id")
    range = payload.get("data").get("range") # bistatic range in [kms] (see pcldetectionrunner.py)
    doppler = payload.get("data").get("doppler") # [dB]
    det_time = payload.get("data").get("det_time") # [milliseconds since the UNIX epoch January 1, 1970 00:00:00 UTC)
    range = payload.get("data").get("range")
    snr = payload.get("data").get("snr") # [db] 
    bistatic_velocity = payload.get("data").get("snr") # [m/s]
    query = """INSERT INTO pcl_plot VALUES (?,?,?,?,?,?,?,?,?,?)"""
    dat = ([range, doppler, bistatic_velocity, snr, 0, 0, plotid, rx_id, tx_id, det_time])
    sqcur.execute(query, dat)
    sqcon.commit()
    
    # write target ground truth
    target_id = payload.get("data").get("targ_id") # target_id
    target_lat = payload.get("data").get("tgt_lat") # target_lat
    target_lon = payload.get("data").get("tgt_lon") # target_lon
    target_height = payload.get("data").get("tgt_height") # target_height
    query = """INSERT INTO target VALUES (?,?,?,?,?)"""
    dat = ([target_id, det_time,target_lat, target_lon, target_height])
    sqcur.execute(query, dat)
    sqcon.commit()

    global range_data
    range_data.append(range)
    global doppler_data
    doppler_data.append(doppler)
    global line1
    line1.set_ydata(doppler_data)
    line1.set_xdata(range_data)
    global fig
    fig.canvas.draw()
    fig.canvas.flush_events()

    

if __name__ == "__main__":
    ## start a sqlite db
    sqlite_con = sqlite3.connect("passive_data.db")
    sqlite_cur = sqlite_con.cursor()

    ## create a pcl plots table
    plot = """ CREATE TABLE IF NOT EXISTS pcl_plot (
            range REAL NOT NULL,
            doppler REAL NOT NULL,
            velocity REAL NOT NULL,
            SNR REAL,
            rangeSTD REAL,
            velocitySTD REAL,
            plotid INTEGER,
            rxid INTEGER,
            txid INTEGER,
            timestamp INTEGER NOT NULL
        ); """
    sqlite_cur.execute(plot)

    ## create a targets table (ground truth)
    target = """ CREATE TABLE IF NOT EXISTS target (
            targetid INTEGER NOT NULL,
            timestamp INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            height REAL NOT NULL
        ); """
    sqlite_cur.execute(target)

    ## create a transmitter table
    transmitter = """ CREATE TABLE IF NOT EXISTS transmitter (
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            height REAL NOT NULL,
            frequency REAL NOT NULL,
            bandwidth REAL NOT NULL,
            type character varying(50) NOT NULL,	
            name character varying(50) NOT NULL,	
            txId INTEGER NOT NULL
        ); """
    sqlite_cur.execute(transmitter)

    ## create a receiver table
    receiver = """ CREATE TABLE IF NOT EXISTS receiver (
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            height REAL NOT NULL,	
            name character varying(50) NOT NULL,	
            rxId INTEGER NOT NULL,
            direction REAL NOT NULL,
            bandwidth REAL NOT NULL
        ); """
    sqlite_cur.execute(receiver)

    # now listen on openburst pcl detections table and write detections and targets 
    conn = dbfunctions.connect_to_db()
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    curs = conn.cursor()

    # read from postgresql and write to sqlite all transmitters
    curs.execute("SELECT * FROM blue_live.pcl_tx")
    for tx in curs.fetchall():
        sql = """INSERT INTO transmitter VALUES (?,?,?,?,?,?,?,?)"""
        data = ([tx[4], tx[5], tx[7]+tx[8], tx[1], tx[10], tx[9], tx[1], tx[0]])
        sqlite_cur.execute(sql, data)
        sqlite_con.commit()

    # read from postgresql and write to sqlite all receivers
    curs.execute("SELECT * FROM blue_live.pcl_rx")
    for rx in curs.fetchall():
        sql = """INSERT INTO receiver VALUES (?,?,?,?,?,?,?)"""
        data = ([rx[3], rx[4], rx[6]+rx[7], rx[1], rx[0], 0, rx[9]])
        sqlite_cur.execute(sql, data)
        sqlite_con.commit()  

    listen_query = "LISTEN " + "blue_live_pcl_detection" + ";"
    curs.execute(listen_query)
    conn.commit()
    plot_id = 0

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
        res = cur.execute("SELECT * FROM pcl_plot")
        for row in res:
            print(row)

        print("-------------------------- printing and plotting all targets sqlite DB------------ ")
        res = cur.execute("SELECT * FROM target")
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
        plt.savefig("range_doppler_map.png") 