"""
This Websocket server performs all PET computations
"""

from __future__ import division
import math
import json
import logging
import os
import multiprocessing as mp
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mc
import numpy as np
import tornado.websocket
import simplekml
from haversine import haversine

from openburst.functions import dbfunctions, basefunctions
from openburst.types import requestwrapper
from openburst.types.requestwrapper import to_request
from openburst.types.petsensor import to_pet
from openburst.types.scheduler import Scheduler
from openburst.constants import openburst_config
from openburst.functions import radfunctions

matplotlib.use("Agg")


def update_pet_data(
    sensor,
    flight_height,
    erp,
    lat_min,
    lat_max,
    lon_min,
    lon_max,
    X,
    Y,
    Z,
    dem_ws_client,
):
    """Updates PET data"""
    z_mat = Z
    pet = json.loads(sensor, object_hook=to_pet)
    irange = z_mat.shape[0] - 1
    jrange = z_mat.shape[1] - 1

    for i in range(0, irange):
        for j in range(0, jrange):
            curr_lat = X[i, j]
            curr_lon = Y[i, j]
            # get distance from (pet.lat, pet.lon, pet.height) to (curr_lat, curr_lon, flight_height)
            try:
                num = (
                    str(89133)
                    + ","
                    + str(pet.lat)
                    + ","
                    + str(pet.lon)
                    + ","
                    + str(pet.height)
                    + ","
                    + str(curr_lat)
                    + ","
                    + str(curr_lon)
                    + ","
                    + str(flight_height)
                    + "&"
                )
                num_list = num  # json.dumps(num)
                dem_ws_client.send(num_list)
                rec_data_float = dem_ws_client.recv()

                got_arr = rec_data_float.replace("[", "")
                got_arr = got_arr.replace("]", "")
                arr = np.fromstring(got_arr, sep=",")
                los = arr[0]
                if los == 1:
                    dist = arr[1]
                    frequency = 9 * (10**9)
                    speed_of_light = 3 * (10**8)
                    power_density_at_range = radfunctions.dbm2si(erp) / (4 * 3.14 * dist * dist)
                    signal_strength_at_range = (
                        power_density_at_range
                        * ((speed_of_light / frequency) ** 2)
                        / (4 * math.pi)
                    )
                    threshold_si = radfunctions.dbm2si(pet.threshold)

                    if signal_strength_at_range > threshold_si:
                        z_mat[i, j] = z_mat[i, j] + 1.0

            except: # pylint: disable=bare-except
                logging.getLogger("PET").debug(
                    "sending/reception error with DEM server"
                )
                return z_mat

    return z_mat


def get_pet_coverage_splat(args, queue, request_type):
    """
    gets the PET coeverage using Splat! propagation loss computation
    """
    try:
        dem_ws_client = basefunctions.open_connection_to_dem_server()
    except: # pylint: disable=bare-except
        logging.getLogger("PET").error(
            "oops..could not connect to DEM server...check if DEM server running"
        )
        return

    rad_id = int(json.loads(args[0]))
    rad_lat = float(json.loads(args[1]))
    rad_lon = float(json.loads(args[2]))
    flight_height = float(json.loads(args[3]))
    erp_dbm = float(json.loads(args[4]))
    threshold_dbm = float(json.loads(args[5]))
    freq = float(json.loads(args[6]))
    radioprop_enabled = int(json.loads(args[7]))
    lat_min = float(json.loads(args[8]))
    lat_max = float(json.loads(args[9]))
    lon_min = float(json.loads(args[10]))
    lon_max = float(json.loads(args[11]))  #

    use_antenna_diag = int(json.loads(args[12]))
    main_beam_azimuth = int(json.loads(args[13]))
    main_beam_elevation = int(json.loads(args[14]))
    magl_enabled = int(json.loads(args[15]))

    logging.getLogger("PET").info(
        "received for PET coverage SPLAT: %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s",
        rad_id,
        rad_lat,
        rad_lon,
        flight_height,
        erp_dbm,
        threshold_dbm,
        freq,
        radioprop_enabled,
        lat_min,
        lat_max,
        lon_min,
        lon_max,
        use_antenna_diag,
        main_beam_azimuth,
        main_beam_elevation,
    )

    num = (
        str(559999)
        + ","
        + str(rad_id)
        + ","
        + str(rad_lat)
        + ","
        + str(rad_lon)
        + ","
        + str(flight_height)
        + ","
        + str(erp_dbm)
        + ","
        + str(threshold_dbm)
        + ","
        + str(freq)
        + ","
        + str(radioprop_enabled)
        + ","
        + str(use_antenna_diag)
        + ","
        + str(main_beam_azimuth)
        + ","
        + str(main_beam_elevation)
        + ","
        + str(magl_enabled)
        + "&"
    )
    num_list = num
    dem_ws_client.send(num_list)
    rec_data_float = dem_ws_client.recv()

    logging.getLogger("PET").info("received...%s \n", rec_data_float)
    if "-9999" in str(
        rec_data_float
    ):  # this means files have to be read that were written
        logging.getLogger("PET").info("received....-9999")
        basefunctions.send_all_pet_lists(queue)
    else:
        queue.put(rec_data_float)

    dem_ws_client.close()


def getPetCoverage(args, queue, request_type):

    try:
        dem_ws_client = basefunctions.open_connection_to_dem_server()
    except: # pylint: disable=bare-except
        logging.getLogger("PET").error(
            "oops..could not connect to DEM server...check if DEM server running"
        )
        return

    flight_height = float(json.loads(args[0]))
    erp = float(json.loads(args[1]))
    tmp_arr = json.loads(args[2])
    lat_min = float(json.loads(tmp_arr[0]))
    lat_max = float(json.loads(tmp_arr[1]))
    lon_min = float(json.loads(tmp_arr[2]))
    lon_max = float(json.loads(tmp_arr[3]))

    name = json.loads(args[3])

    Z = []
    lat_res = 0.1
    lon_res = 0.1
    noflats = int(math.ceil((lat_max - lat_min) / lat_res))
    noflons = int(math.ceil((lon_max - lon_min) / lon_res))

    x = np.linspace(lat_min, lat_max, noflats)
    y = np.linspace(lon_min, lon_max, noflons)

    X, Y = np.meshgrid(x, y)
    Z = np.zeros((noflons, noflats))
    nofpets = 0
    for i in range(4, len(args)):
        nofpets = nofpets + 1
        Z = update_pet_data(
            args[i],
            flight_height,
            erp,
            lat_min,
            lat_max,
            lon_min,
            lon_max,
            X,
            Y,
            Z,
            dem_ws_client,
        )

    figure = plt.figure()
    axs = figure.add_subplot(111, aspect=1)
    axs.clear()
    levels = np.linspace(0, nofpets, nofpets + 2)
    #norm = mc.BoundaryNorm(levels, 256)

    contour = axs.contourf(Y, X, Z, levels=levels, cmap=plt.jet())
    #cbar = plt.colorbar(contour, ax=axs)
    plt.savefig("/tmp/burst.png")
    os.system("eog /tmp/burst.png &")
    kml = simplekml.Kml(open=1)

    # now get all the polygons in the contourf plot and make a kml file from them
    nofpolys = 0
    for collection in contour.collections:
        for path in collection.get_paths():
            path.should_simplify = False
            for polygon in path.to_polygons():
                nofpolys = nofpolys + 1
                # print polygon.__class__
                polycolor = collection.get_facecolor().tolist()[0]
                mytuple = basefunctions.totuple(polygon)
                if nofpolys == 1:
                    pol = kml.newpolygon(name=name)
                else:
                    pol = kml.newpolygon(name="")
                # set the boundaries of the polygon
                pol.outerboundaryis = mytuple

                # set color of polygon border lines
                pol.style.linestyle.color = simplekml.Color.rgb(
                    int(polycolor[0] * 255.0),
                    int(polycolor[1] * 255.0),
                    int(polycolor[2] * 255.0),
                    255,
                )
                pol.style.linestyle.width = 1
                pol.style.polystyle.fill = 1
                pol.style.polystyle.outline = 1
                # fill polygon with transparent color (color same as the line color)
                pol.style.polystyle.color = simplekml.Color.rgb(
                    int(polycolor[0] * 255.0),
                    int(polycolor[1] * 255.0),
                    int(polycolor[2] * 255.0),
                    255,
                )  # r,g,b,transparency

    file_name = "/tmp/pet_contours_" + str(name) + ".kml"
    logging.getLogger("PET").info("debug: saving kml file as: %s", file_name)
    kml.save(file_name)

    snd_msg = json.dumps(kml.kml())
    nbr_args = 1
    args = [snd_msg]
    response = requestwrapper.RequestWrapper(request_type + "_response", nbr_args, args)
    response_json = json.dumps(response.__dict__)
    logging.getLogger("PET").debug(
        "sending kml with request_type: %s", response.request_type
    )
    queue.put(response_json)
    dem_ws_client.close()


class PetWebSocketHandler(tornado.websocket.WebSocketHandler):
    """
    Tornado Websocket Class for PET Server
    """
    def __init__(self, val1, val2):
        tornado.websocket.WebSocketHandler.__init__(self, val1, val2)
        self.scheduler = Scheduler(self, 1)  # 1s wait time
        self.scheduler.schedule_func()

    def check_origin(self, origin):
        return True

    # the client connected
    def open(self):
        logging.getLogger("PET").info("New PET client connected; ")

    # the client sent the message
    def on_message(self, message):
        line = message
        # print line
        logging.getLogger("PET").info("received client query")
        if line is None:
            logging.getLogger("PET").info("line is None...returning")
            return
        if isinstance(line, basefunctions.Unicode):
            request_received = json.loads(line, object_hook=to_request)
            logging.getLogger("PET").info(
                "------received request to: %s", request_received.request_type
            )

            if request_received.request_type == "addPETSensor":
                logging.getLogger("PET").info("PET add sensor...")

            elif request_received.request_type == "computeCoverage":
                logging.getLogger("PET").info(
                    "PET coverage points request..nof args: %s",
                    len(request_received.args),
                )
                nofargs = len(request_received.args)
                process = mp.Process(
                    target=get_pet_coverage_splat,
                    args=(
                        request_received.args,
                        self.scheduler.queue,
                        request_received.request_type,
                    ),
                )
                process.start()


class Application(tornado.web.Application):
    """Tornado websocket application class"""
    def __init__(self):
        base_dir = os.path.dirname(__file__)
        settings = {
            "template_path": os.path.join(base_dir, "../templates"),
            "static_path": os.path.join(base_dir, "../static"),
        }

        tornado.web.Application.__init__(
            self,
            [
                (r"/pet", PetWebSocketHandler),
            ],
            **settings
        )


def main():
    """main function"""
    logger_dir = basefunctions.get_openburst_logging_dir()
    logger_file = logger_dir + "burst_pet_logging.json"
    logger = basefunctions.setup_logging(logger_file, "PET")
    
    logger.info(
        "----------------------------------------------------------------------------------------"
    )
    logger.info(
        "-------------------------------------PET Server newly started---------------------------"
    )
    logger.info(
        "----------------------------------------------------------------------------------------"
    )

    myip = basefunctions.get_myip()
    port = openburst_config.PET_SERVER_PORT
    dbfunctions.write_server_start_to_db(
        "pet", myip, port
    )  # write to db that server started (this name should be the same as the opened port ending "/geoplot" !!)

    try:

        tornado.options.parse_command_line()
        Application().listen(port)
        main_loop = tornado.ioloop.IOLoop.instance()
        logging.getLogger("PET").info("----------------- PET SERVER UP AND RUNNING...")
        main_loop.start()

    except: # pylint: disable=bare-except
        logging.getLogger("PET").error(
            "PET Server initialization error! check 1) ip or port setting in servers.py, 2) check if DB-server running 3) and if DB schema and tables initiated correctly"
        )


if __name__ == "__main__":
    main()
