"""
This Websocket server performs all PCL computations
"""

import os.path
import json
import logging
import tornado.websocket

from openburst.types.losmapper import TxToLocationLOSMapper
from openburst.types import requestwrapper
from openburst.types.requestwrapper import  to_request
from openburst.types.callsignmapper import CallsignMapper
from openburst.types.grid_params import to_grid_params
from openburst.pcl import loadtx
from openburst.types.rx import to_Rx
from openburst.types.tx import to_Tx, findTxByCallsign
from openburst.pcl import coverage
from openburst.functions import basefunctions
from openburst.functions import geofunctions
from openburst.constants import openburst_config
from openburst.functions import dbfunctions



class PclWebSocketHandler(tornado.websocket.WebSocketHandler):
    """Class for PCL Websocket Server"""
    def __init__(self, val1, val2):
        tornado.websocket.WebSocketHandler.__init__(self, val1, val2)

    def check_origin(self, origin):
        return True

    # the client connected
    def open(self):
        logging.getLogger("PCL").info("New PCL client connected; ")

    def on_close(self):
        logging.getLogger("PCL").info("PCL Client disconnected")

    # the client sent the message
    def on_message(self, message):

        line = message
        if line is None:
            logging.getLogger("PCL").debug("line is None")
            return

        if line == "server should answer":
            self.write_message("ok this is the answer of the server")
        elif line == "server should do nothing":
            pass

        else:
            logging.getLogger("PCL").debug("server is loading the request from json")

            request_received = json.loads(line, object_hook=to_request)
            logging.getLogger("PCL").info(
                "------received request to: %s",  request_received.request_type
            )

            if (
                request_received.request_type == "findTxForRx_all"
            ):  # return all LOS-Tx for all Receivers, while mapping the Rx to the Tx and vice-versa through LOSRxIDs tag

                tx_CallsignMapper = (
                    CallsignMapper()
                )  # this variable/class instance helps to keep track which Tx has already been loaded
                tx_all = []
                # this list contains all the loaded Tx

                Rx_all_json_in = request_received.args[
                    0
                ]  # this is a list containing all the receivers, each in json string format
                also_take_non_LOS_Tx_from_Rx = request_received.args[1]

                Rx_all_json_out = []
                #for rx_nbr in range(len(Rx_all_json_in)):
                for _, curr_rx in enumerate(Rx_all_json_in):

                    receiver = json.loads(
                        #Rx_all_json_in[rx_nbr], object_hook= to_Rx
                        curr_rx,  object_hook= to_Rx
                    )
                    
                    receiver, tx_all, tx_CallsignMapper = (
                        loadtx.get_los_tx(
                            receiver,
                            tx_all,
                            tx_CallsignMapper,
                            also_take_non_LOS_Tx_from_Rx,
                        )
                    )
                    Rx_all_json_out.append(json.dumps(receiver.__dict__))

                tx_all_json = []
                for i in range(len(tx_all)):
                    tx_all_json.append(json.dumps(tx_all[i].__dict__))

                response = requestwrapper.RequestWrapper(
                    request_received.request_type + "_response:Rx's and Tx's",
                    2,
                    [Rx_all_json_out, tx_all_json],
                )
                response_json = json.dumps(response.__dict__)

                logging.getLogger("PCL").debug("----------------sending response ")
                self.write_message(response_json)

            
            if request_received.request_type == "calcMinDetRCScoverage":
                logging.getLogger("PCL").info(
                    "----- pclServer received query: calcMinDetRCScoverage.---"
                )

                if (request_received.nbr_args != 8) or (
                    len(request_received.args) != 8
                ):
                    logging.getLogger("PCL").info(
                        "----- unvalid request, did not receive 8 arguments..."
                    )
                    return

                json_str_arr_rx = request_received.args[0]
                json_str_arr_tx = request_received.args[1]
                snr_thresh = json.loads(request_received.args[2])
                delay_thresh = json.loads(request_received.args[3])  # us
                t_max = json.loads(request_received.args[4])
                json_grid_params = request_received.args[5]

                radioprop_enabled = json.loads(request_received.args[6])
                radioprop_params = request_received.args[7]

                rcs_grid_params = json.loads(
                    json_grid_params, object_hook=to_grid_params
                )
                logging.getLogger("PCL").info(
                    "----- pclServer calling create_range_rcs_gridpoints"
                )
                points_x, points_y, points_z = geofunctions.create_range_rcs_gridpoints(
                    rcs_grid_params
                )  # returns lon, lat, z points

                combined_heatmaps_for_each_rx = (
                    []
                )  # will have as many entries as there are Rx: each of those entries contain a heatmap for all the Transmitters combined

                if len(json_str_arr_rx) == 0 or len(json_str_arr_tx) == 0:
                    logging.getLogger("PCL").error(
                        "--- Either no Receiver or Transmitter in request, aborting..."
                    )
                    return

                # This structure is needed as some Tx might be deactivated - this way it is easier to find correct one
                tx_all = []
                biggest_tx_id = -1
                #for tx_nbr in range(len(json_str_arr_tx)):
                for tx_nbr, curr_tx in enumerate(json_str_arr_tx):
                    tx_all.append(
                        #json.loads(json_str_arr_tx[tx_nbr], object_hook=to_Tx)
                        json.loads(curr_tx, object_hook=to_Tx)
                    )
                    if tx_all[tx_nbr].tx_id > biggest_tx_id:
                        biggest_tx_id = tx_all[tx_nbr].tx_id

                # find the largest TX ID (we asuume that Tx IDs start at 0 and go consecutively without "holes" to the largest)
                tx_to_loc_grid_mapper = TxToLocationLOSMapper(biggest_tx_id)

                #for rx_nbr in range(len(json_str_arr_rx)):
                for rx_nbr, curr_rx in enumerate(json_str_arr_rx):

                    #Rx = json.loads(json_str_arr_rx[rx_nbr], object_hook=to_Rx)
                    Rx = json.loads(curr_rx, object_hook=to_Rx)
                    logging.getLogger("PCL").info(
                        "----- pclServer calling calcCoverage.get_antenna_los_grid"
                    )
                    print(
                        "--------------------------------------------pclServer.py: calling calcCoverage.get_antenna_los_grid for RECEIVER-TGT GRID: =  ",
                        (rcs_grid_params.max_x - rcs_grid_params.min_x)
                        / rcs_grid_params.res_x,
                        (rcs_grid_params.max_y - rcs_grid_params.min_y)
                        / rcs_grid_params.res_y,
                    )

                    if radioprop_enabled == 0:
                        max_LOS_arr_Rx = coverage.get_antenna_los_grid(
                            Rx.lon,
                            Rx.lat,
                            Rx.masl + Rx.ahmagl,
                            rcs_grid_params.min_x,
                            rcs_grid_params.max_x,
                            rcs_grid_params.res_x,
                            rcs_grid_params.min_y,
                            rcs_grid_params.max_y,
                            rcs_grid_params.res_y,
                            rcs_grid_params.min_z,
                            rcs_grid_params.max_z,
                            rcs_grid_params.res_z,
                            Rx.name,
                            radioprop_enabled,
                            1,
                            Rx.get_rx_signal_type(),
                            rcs_grid_params.amt_pts_y,
                            rcs_grid_params.amt_pts_x,
                        )

                    combined_heatmap_for_one_Rx = []

                    # use tx callsigns instead of IDs
                    txcallsigns = Rx.txcallsigns.split(",")

                    #for tx_callsign_nbr in range(len(txcallsigns)):
                    for tx_nbr, curr_tx in enumerate(txcallsigns):
                
                        #Tx_callsign = txcallsigns[tx_callsign_nbr]
                        Tx_callsign = curr_tx

                        Tx, found = findTxByCallsign(tx_all, Tx_callsign)

                        if not found:
                            logging.getLogger("PCL").debug(
                                "---------- This LOS-transmitter has not been found (most probably deactivated) %s",
                                Tx_callsign,
                            )
                            continue

                        if radioprop_enabled == 0:
                            tx_to_loc_grid_mapper.calculate_los_grid_if_loc_not_done(
                                Tx,
                                rcs_grid_params.min_x,
                                rcs_grid_params.max_x,
                                rcs_grid_params.res_x,
                                rcs_grid_params.min_y,
                                rcs_grid_params.max_y,
                                rcs_grid_params.res_y,
                                rcs_grid_params.min_z,
                                rcs_grid_params.max_z,
                                rcs_grid_params.res_z,
                                radioprop_enabled,
                                0,
                                rcs_grid_params.amt_pts_y,
                                rcs_grid_params.amt_pts_x,
                            )
                            LOS_arr_Tx = tx_to_loc_grid_mapper.get_los_grid(Tx.tx_id)

                        logging.getLogger("PCL").info(
                            "----------pclServer calling calcCoverage.calculate_min_rcs_coverage %s, %s: ",
                            points_x.shape,
                            points_y.shape,
                        )
                        if radioprop_enabled == 0:
                            heat_map, _ = (
                                coverage.calculate_min_rcs_coverage(
                                    snr_thresh,
                                    Rx,
                                    Tx,
                                    t_max,
                                    max_LOS_arr_Rx,
                                    LOS_arr_Tx,
                                    points_x,
                                    points_y,
                                    points_z,
                                    delay_thresh,
                                    radioprop_enabled,
                                    radioprop_params,
                                )
                            )
                        else:
                            heat_map, _ = (
                                coverage.calculate_min_rcs_coverage_prop(
                                    snr_thresh,
                                    Rx,
                                    Tx,
                                    t_max,
                                    points_x,
                                    points_y,
                                    points_z,
                                    delay_thresh,
                                )
                            )

                        if tx_nbr == 0 or len(combined_heatmap_for_one_Rx) == 0:
                            combined_heatmap_for_one_Rx = heat_map

                        else:
                            for y in range(len(points_y)):
                                for x in range(len(points_x)):
                                    if len(points_z) == 1:
                                        heat_map_pos_valid = heat_map[y][x] != -1
                                        # true if there is LOS.
                                        if heat_map_pos_valid == (
                                            combined_heatmap_for_one_Rx[y][x] != -1
                                        ):  # if both invalid or both valid
                                            combined_heatmap_for_one_Rx[y][x] = min(
                                                heat_map[y][x],
                                                combined_heatmap_for_one_Rx[y][x],
                                            )
                                        elif (
                                            heat_map_pos_valid
                                        ):  # this position has LOS for new Tx , whereas it has not for the older Tx
                                            combined_heatmap_for_one_Rx[y][x] = (
                                                heat_map[y][x]
                                            )

                                    else:
                                        for z in range(len(points_z)):
                                            heat_map_pos_valid = heat_map[y][x][z] != -1
                                            # true if there is LOS.
                                            if heat_map_pos_valid == (
                                                combined_heatmap_for_one_Rx[y][x][z]
                                                != -1
                                            ):  # if both invalid or both valid
                                                combined_heatmap_for_one_Rx[y][x][z] = (
                                                    min(
                                                        heat_map[y][x][z],
                                                        combined_heatmap_for_one_Rx[y][
                                                            x
                                                        ][z],
                                                    )
                                                )
                                            elif (
                                                heat_map_pos_valid
                                            ):  # this position has LOS for new Tx , whereas it has not for the older Tx
                                                combined_heatmap_for_one_Rx[y][x][z] = (
                                                    heat_map[y][x][z]
                                                )

                    json_combined_heatmap = json.dumps(
                        combined_heatmap_for_one_Rx.tolist()
                    )
                    combined_heatmaps_for_each_rx.append(json_combined_heatmap)

                logging.getLogger("PCL").info("----- calculation finished")

                json_combined_heatmaps = json.dumps(combined_heatmaps_for_each_rx)
                logging.getLogger("PCL").info("----- all_heatmaps serialized")

                nbr_args = 1
                args = []

                args.append(json_combined_heatmaps)

                all_heatmaps_responses = requestwrapper.RequestWrapper(
                    request_received.request_type + "_response", nbr_args, args
                )

                response_json = json.dumps(all_heatmaps_responses.__dict__)

                logging.getLogger("PCL").info(
                    "----- sending PCL coverage response: to Client"
                )
                self.write_message(response_json)

        

class Application(tornado.web.Application):
    """Torando websocket application class"""
    def __init__(self):
        base_dir = os.path.dirname(__file__)
        settings = {
            "template_path": os.path.join(base_dir, "../templates"),
            "static_path": os.path.join(base_dir, "../static"),
        }

        tornado.web.Application.__init__(
            self,
            [
                (r"/pcl", PclWebSocketHandler),
            ],
            **settings
        )


def main():
    "main function"
    
    logger_dir = basefunctions.get_openburst_logging_dir()
    logger_file = logger_dir + "burst_pcl_logging.json"
    logger = basefunctions.setup_logging(logger_file, "PCL")

    logger.info(
        "----------------------------------------------------------------------------------------"
    )
    logger.info(
        "-------------------------------------PCL Server newly started---------------------------"
    )
    logger.info(
        "----------------------------------------------------------------------------------------"
    )

    try:
        myip = basefunctions.get_myip()
        port = openburst_config.PCL_SERVER_PORT
        dbfunctions.write_server_start_to_db("pcl", myip, port)
        tornado.options.parse_command_line()
        Application().listen(port)
        main_loop = tornado.ioloop.IOLoop.instance()
        main_loop.start()

    except ValueError:
        logging.getLogger("PCL").error(
            "PCL initialization error! check 1) ip or port setting in servers.py, 2) check if DB-server running 3) and if DB schema and tables initiated correctly"
        )


if __name__ == "__main__":

    main()
