"""
Module to load PCL Transmitters of Opportunity (ToO). 
ToO are also simply named Transmitters (Tx).

"""

import random
import csv
import math
import logging
import logging.config

from openburst.functions import basefunctions
from openburst.types.tx import to_Tx
from openburst.functions import geofunctions
basefunctions.set_openburst_system_path()
basefunctions.set_openburst_linked_lib_path()
import libsplathd as splat

folder_name = basefunctions.get_tx_folder() # gets the folder name where ToO information resides


def get_los_tx(rx, all_tx, tx_callsign_mapper, consider_non_los_tx):
    """ Returns transmitters (tx) for a given receiver(rx). The returned tx 
    are within limit_distance from the rx 
    """

    signal_type = rx.signal_type

    # Depending on signal_type, will choose the correct file_name
    if signal_type == "FM":  # "UKW_concess":
        file_name = "FM/FM_CH_SAMPLE.CSV"
        # indices = (2,11,10,12,13,14,15,23,19,20,24,25, 5)
        indices = (2, 9, 8, 12, 13, 14, 15, 23, 19, 20, 24, 25, 5)
        erp_unit = "W"
    else:
        logging.getLogger("PCL").error("Invalid 'signal_type', namely: %s", signal_type)
        return rx, all_tx, tx_callsign_mapper

    # open websocket
    ws_dem_server = basefunctions.open_connection_to_dem_server()

    if rx.masl == -1:
        rx.masl = geofunctions.get_terrain_height(splat, rx.lat, rx.lon) 

    # Load .csv file
    with open(folder_name + file_name, "r", encoding="ISO-8859-1") as csvfile:
        input_data = csv.reader(csvfile, delimiter=";", quotechar="|")

        print("input_data = ", input_data)

        next(input_data, None)  # skip the headers
        # Loop through the rows in the csv file
        for row in input_data:

            try:
                Tx_pot_dict = {}
                Tx_pot_dict["lat"] = float(row[indices[1]])
                Tx_pot_dict["lon"] = float(row[indices[2]])
                Tx_pot_dict["masl"] = float(row[indices[3]])
                Tx_pot_dict["ahmagl"] = float(row[indices[4]])
                Tx_pot_dict["callsign"] = row[indices[12]]
                Tx_pot_dict["status"] = 1
            except Exception as e:
                logging.getLogger("PCL").error(e)
                continue


            horiz_dist = (
                geofunctions.get_2d_distance_between_locs(
                    Tx_pot_dict["lat"], Tx_pot_dict["lon"], rx.lat, rx.lon
                )
                * 1000.0
            )

            if horiz_dist > rx.limit_distance:
                continue
                # if its not, continue with next potentially interesting transmitter

            if consider_non_los_tx:
                is_los = 1
            else:
                pass
                # we consider all Tx, not just the LoS ones

            was_incl = tx_callsign_mapper.is_included(
                Tx_pot_dict["callsign"]
            )  # this is to keep track which transmitter might have already been loaded for a previous rx

            tx_callsign_mapper.add_if_not_incl(
                Tx_pot_dict["callsign"], len(tx_callsign_mapper)
            )
            tx_id = tx_callsign_mapper[Tx_pot_dict["callsign"]]
            # make sure the tx_id is not longer that 8 characters (otehrwise e will have problems with storing rx with max 1000 Txs, as max size is 8000bytes)

            rx.lostxids.append(
                tx_id
            )  # link the already loaded transmitter to the receiver within the rx

            
            if (was_incl is True):  # This Tx has already been loaded once, for a different rx.
                logging.getLogger("PCL").info(
                    "link the receiver to the already loaded transmitter within the all_tx.size = %s, tx_id = %s",
                    len(all_tx),
                    tx_id,
                )
                curr_tx_id = 0
                for txxx in all_tx:
                    if txxx.callsign == tx_id:
                        logging.getLogger("PCL").info(
                            "...................succeeded reusing Tx"
                        )
                        all_tx[curr_tx_id].LOSRxIDs.append(
                            rx.rx_id
                        )  # link the receiver to the already loaded transmitter within the Tx
                        break
                    curr_tx_id = curr_tx_id + 1
                continue  # with next potential Tx
            else:

                # the transmitter is no longer only 'potentially' interesting, but really interesting
                tx_dict = Tx_pot_dict
                tx_dict["tx_id"] = tx_id
                tx_dict["losrxids"] = [
                    rx.rx_id
                ]  # link the receiver to the already loaded transmitter within the Tx

                tx_dict["sitename"] = basefunctions.ensure_utf(
                    row[indices[0]]
                ).decode("utf-8", "ignore")
                #print("site name = ", tx_dict["sitename"])  # non-utf8 chars (>128) would provoke errors, upon encoding them normally
                # unicode(row[indices[0]].sitename, errors='ignore')  # this would simply remove the char >128, whereas with 'replace' the U+FFFD 'REPLACEMENT CHARACTER' is used

                tx_dict["freq"] = float(row[indices[5]])

                if signal_type == "DVB":
                    tx_dict["bandwidth"] = 8000  # kHz
                elif signal_type == "DAB":
                    tx_dict["bandwidth"] = 1536  # kHz
                else:
                    tx_dict["bandwidth"] = float(row[indices[6]])

                tx_dict["pol"] = "UNDEFINED"
                if row[indices[7]] != "":
                    # tx_dict["pol"] =row[indices[7]]
                    if "H" in row[indices[7]]:
                        tx_dict["pol"] = "H"
                    else:
                        tx_dict["pol"] = "V"

                tx_dict["erp_h"] = "UNDEFINED"
                if indices[8] != -1:
                    if str(row[indices[8]]).strip() != "":
                        if erp_unit == "dBW":
                            tx_dict["erp_h"] = float(row[indices[8]])
                        else:
                            tx_dict["erp_h"] = 10 * math.log10(float(row[indices[8]]))

                tx_dict["erp_v"] = "UNDEFINED"
                if indices[9] != -1:
                    if str(row[indices[9]]).strip() != "":
                        if erp_unit == "dBW":
                            tx_dict["erp_v"] = float(row[indices[9]])
                        else:
                            tx_dict["erp_v"] = 10 * math.log10(float(row[indices[9]]))

                tx_dict["signal_type"] = signal_type

                tx_dict["type"] = ""
                tx_dict["horiz_diagr_att"] = "UNDEFINED"
                horiz_diag_pot = row[indices[10]]
                if horiz_diag_pot.find("OMNI", 0, 15) == 0:
                    tx_dict["type"] = "OMNI"
                    tx_dict["horiz_diagr_att"] = 0
                elif horiz_diag_pot.find("VECTOR", 0, 15) == 0:
                    horiz_diag_pot_str_list = horiz_diag_pot.split(" ")

                    del horiz_diag_pot_str_list[
                        0:2
                    ]  # delete VECTOR and 10 or 1 or whatever the angle step size is
                    tx_dict["horiz_diagr_att"] = [
                        round(float(x), 3) for x in horiz_diag_pot_str_list
                    ]
                    tx_dict["type"] = "directional"

                elif horiz_diag_pot.find("POINTS", 0, 15) == 0:
                    horiz_diag_pot_str_list = horiz_diag_pot.split(" ")
                    del horiz_diag_pot_str_list[0:1]  # delete POINTS
                    tx_dict["type"] = "interpol. directional"
                    tx_dict["horiz_diagr_att"] = []
                    prev_deg_added = (
                        -1
                    )  # Running index for writing in list: 360 values returned
                    prev_deg_in_list = 0
                    prev_value_in_list = round(float(horiz_diag_pot_str_list[1]), 3)

                    if horiz_diag_pot_str_list[0] != 0:
                        logging.getLogger("PCL").debug(
                            "Might have a problem while loading/interpolating horizontal attenuation diagram first entry is not at degree zero"
                        )

                    horiz_diag_pot_str_list.append(
                        360
                    )  # assuming first entry is zero. Appends last entry to be 360 deg in order to interpolate
                    horiz_diag_pot_str_list.append(horiz_diag_pot_str_list[1])
                    for i in range(len(horiz_diag_pot_str_list)):
                        if i % 2 == 0:
                            deg_in_list = int(horiz_diag_pot_str_list[i])
                            value_in_list = round(
                                float(horiz_diag_pot_str_list[i + 1]), 3
                            )
                            while prev_deg_added < deg_in_list:

                                prev_deg_added += 1

                                if deg_in_list - prev_deg_in_list == 0:
                                    slope = 0
                                else:
                                    slope = (value_in_list - prev_value_in_list) / (
                                        deg_in_list - prev_deg_in_list
                                    )
                                offset = value_in_list - slope * deg_in_list

                                tx_dict["horiz_diagr_att"].append(
                                    slope * prev_deg_added + offset
                                )
                            prev_deg_in_list = deg_in_list
                            prev_value_in_list = value_in_list

                    del tx_dict["horiz_diagr_att"][
                        -1
                    ]  # deleting very last entry (==360 deg, equals 0 degrees, which is first entry)

                elif horiz_diag_pot == "":
                    logging.getLogger("PCL").debug(
                        "empty horizontal diagramm found, assuming OMNI"
                    )
                    tx_dict["type"] = "OMNI"
                    tx_dict["horiz_diagr_att"] = 0
                else:
                    logging.getLogger("PCL").debug("invalid horizontal_diagramm input")

                tx_dict["vert_diagr_att"] = "UNDEFINED"
                if indices[11] != -1:
                    vert_diag_pot = row[indices[11]]
                    if vert_diag_pot.find("OMNI", 0, 15) == 0:
                        tx_dict["vert_diagr_att"] = 0
                    elif vert_diag_pot.find("VECTOR", 0, 15) == 0:
                        vert_diag_pot_str_list = vert_diag_pot.split(" ")
                        del vert_diag_pot_str_list[
                            0:2
                        ]  # delete VECTOR and 10 or 1 or whatever the angle step size is
                        tx_dict["vert_diagr_att"] = [
                            round(float(x), 3) for x in vert_diag_pot_str_list
                        ]

                    elif vert_diag_pot.find("POINTS", 0, 15) == 0:
                        logging.getLogger("PCL").debug(
                            "LOADING VERTICAL ATTENUATION DIAGRAM VIA POINTS IS NOT YET IMPLEMENTED!!"
                        )
                        
                    elif vert_diag_pot == "":
                        tx_dict["vert_diagr_att"] = "UNDEFINED"
                    else:
                        logging.getLogger("PCL").debug(
                            "invalid vertical diagram input, namely: %s", vert_diag_pot
                        )
                        # TODO: what if empty

                # convert dictionary to class
                tx = to_Tx(tx_dict)

                # make sure the callsign is unique and has max 8 characters 
                # (otherwise the txcallsigns of an rx with 1000 tx too long for DB triggers)
                if len(tx.callsign) > 8:
                    tx.callsign = tx.signal_type[:2] + str(
                        random.randint(0, 99999)
                    )  # Tx.callsign[:3].strip()

                all_tx.append(tx)

        # now sort the Txs with descending power
        all_tx_sorted = sorted(all_tx, key=lambda x: x.power, reverse=True)

        # and get the best maximum maxnumtx
        maxnoftx = 50  # 150
        all_tx_sorted_max150 = all_tx_sorted[:maxnoftx]

    # close websocket
    basefunctions.close_connection_to_dem_server(ws_dem_server)
    
    # return all_tx if you just want all the Tx inside the limit_distance
    # return all_tx_sorted_max150 for the strongest 150 tx inside the limit_distance
    return (
        rx,
        all_tx_sorted_max150,
        tx_callsign_mapper,
    )  
