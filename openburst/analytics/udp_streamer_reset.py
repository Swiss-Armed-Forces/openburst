from openburst.types import dbpersistentaccess
from openburst.functions import socketfunctions
from openburst.constants import pclconstants
from openburst.functions import basefunctions
from openburst.types import tx as txclass
import logging

# for postgresaccess
dbaccess = dbpersistentaccess.DbConnector(logging.getLogger("SENSOR_CONTROL"), "LIVE_STREAMER")
dbaccess.connect_to_db()

stream_client = socketfunctions.get_client_socket()

# send reset
socketfunctions.send_client_data(stream_client, "RESET") 

# get and send all RX
rxs = dbaccess.get_all_pcl_rx("BLUE")
for j, rx_tup in enumerate(rxs):
    rx = basefunctions.get_pcl_rx_attributes(rx_tup)
    rx_message = "RX " + str(rx.rx_id) + "," + str(rx.lat) + "," + str(rx.lon) + "," + str(rx.masl + rx.ahmagl) 
    socketfunctions.send_client_data(stream_client, rx_message) 

    txs = dbaccess.get_all_pcl_tx_for_rx("BLUE", rx_tup)
    for txx in txs:

        cur_tx = txclass.Tx(
                    txx[0],
                    txx[1],
                    txx[2],
                    txx[4],
                    txx[5],
                    txx[7],
                    txx[8],
                    txx[10],
                    txx[13],
                    txx[11],
                    txx[12],
                    "directional",
                    txx[14],
                    txx[15],
                    txx[16],
                    txx[9],
                    None,
                    1,
                ) 
       
        tx_message = "TX " + str(cur_tx.tx_id) + "," + str(cur_tx.lat) + "," + str(cur_tx.lon) + "," + str(cur_tx.masl + cur_tx.ahmagl) 
        socketfunctions.send_client_data(stream_client, tx_message) 
        sensor_message = "SENSOR " +  str(rx.rx_id) + "/" + str(cur_tx.tx_id) + "," + str(rx.rx_id) + "," + str(cur_tx.tx_id) + "," + str(pclconstants.STD_DEV_BIST_RANGE_FM) + "," + str(pclconstants.STD_DEV_BIST_VEL_FM)
        socketfunctions.send_client_data(stream_client, sensor_message) 


### send ROI over the live stream
roi_message = "ROI 46.8,47.4,8.1,9.6" ## TBD: hardcoded
socketfunctions.send_client_data(stream_client, roi_message) 

# send bistatic window
win_message = "BIST_WND 40000,200" # TBD hardcoded
socketfunctions.send_client_data(stream_client, win_message)


dbaccess.conn.close()
   