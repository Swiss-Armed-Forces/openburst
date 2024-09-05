"""
test reading and plotting PCL detections from the DB every second
"""

import time
import pytest
from openburst.functions import dbfunctions

def test_read_pcl_detections():
    try:
        conn = dbfunctions.connect_to_db()
    except Exception:
        pytest.fail("Could not connecto db ..")

    cur = conn.cursor()

    try:
        # will read the PCL detections for 30 seconds
        j = 0
        while (j < 3):
            cur.execute("""SELECT * from blue_live.pcl_detection;""",)
            conn.commit()
            rows = cur.fetchall()
            print("----------- RX_ID | TX_ID | TGT_ID | TIME[ms] | BISTATIC_RANGE [km] | BISTATIC_DOPPLER [Hz] --------")
            for i in range(len(rows)):
                assert len(rows[i]) == 18 # a row should have 16 elements
                print(rows[i][0],"|",  rows[i][1],"| ", rows[i][2],"| ", rows[i][3],"| ",  rows[i][4], "| ", rows[i][5])
            time.sleep(1)
            j = j + 1
                    
    except Exception:
        pytest.fail("Could not read pcl detections ..")
        

    assert True
