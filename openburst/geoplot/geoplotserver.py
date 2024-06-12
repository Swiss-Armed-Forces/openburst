"""
This Websocket server performs all KML drawing
"""

from __future__ import division

import pickle
import os
import os.path
import json
import logging
import multiprocessing as mp
import sys
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mc
import fiona
import numpy as np
import tornado.websocket
import simplekml

from openburst.functions import dbfunctions
from openburst.functions import basefunctions
from openburst.functions import geofunctions
from openburst.types.requestwrapper import to_request
from openburst.types import requestwrapper
from openburst.types.grid_params import to_grid_params
from openburst.types.scheduler import Scheduler
from openburst.constants import openburst_config


matplotlib.use("Agg")

# Enable fiona driver
fiona.drvsupport.supported_drivers["KML"] = (
    "rw"  # needed to write KML file from geopandas
)

if sys.version_info[0] >= 3:
    Unicode = str


def get_rad_coverage_kml(
    z_mat,
    queue,
    rad_id,
    flight_height,
    rcs,
    rad_lat,
    rad_lon,
    theta_res,
    dist_step,
    max_distance,
    request_type,
):
    """ 
    returns a heatmap kml file given all border points of an active coverage
    region when using propagation model
    """

    logger = logging.getLogger("GEO")
    logger.info("getting kml plot for active radar coverage")

    z_list = np.array(z_mat)
    logging.getLogger("GEO").info(
        "in get_rad_coverage_kml: z_list.shape: %s", z_list.shape
    )

    x = int(z_list.shape[0]) / 3  # z_list contains [lat,lon,los][lat,lon,los]...
    z_d = np.reshape(z_list, [int(x), 3])

    azimuths = np.arange(0, 360, theta_res)
    zeniths = np.arange(max_distance, 0 - dist_step, -1 * dist_step)

    len_az = azimuths.shape[0]
    len_zen = zeniths.shape[0]

    zz0 = z_d[:, 0]  # lats
    zz1 = z_d[:, 1]  # lons
    zz2 = z_d[:, 2]  # los [0/1]

    Y = np.reshape(zz0, (len_az, len_zen))
    X = np.reshape(zz1, (len_az, len_zen))
    Z = np.reshape(zz2, (len_az, len_zen))

    # plt.ion()
    figure = plt.figure()
    axs = figure.add_subplot(111, aspect=1)
    axs.clear()

    # levels = np.linspace(-1, 1, 40)
    levels = np.power(10, np.linspace(-1, 2, 3))
    norm = mc.BoundaryNorm(levels, 256)

    contour = axs.contourf(X, Y, Z, levels=levels, cmap=plt.jet(), norm=norm)
    #cbar = plt.colorbar(contour, ax=axs)

    # plt.show()
    # figure.canvas.draw()
    # plt.savefig('/tmp/burst.png')
    # os.system('eog /tmp/burst.png &')

    kml = simplekml.Kml(open=1)
    polyname = (
        "RAD_ID:"
        + str(rad_id)
        + "/masl/mAGL:"
        + str(flight_height)
        + "/RCS:"
        + str(rcs)
    )
    file_name = (
        "/tmp/" + str(rad_id) + "_" + str(flight_height) + "masl/mAGL_RCS1" + ".kml"
    )
    logger.debug("saving kml file as: %s", file_name)

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
                    pol = kml.newpolygon(name=polyname)
                else:
                    pol = kml.newpolygon(name="")
                # set the boundaries of the polygon
                pol.outerboundaryis = mytuple

                # set color of polygon border lines
                # print("polycolor = ", polycolor)
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

    snd_msg = json.dumps(kml.kml())
    nbr_args = 1
    args = [snd_msg]
    response = requestwrapper.RequestWrapper(request_type + "_response", nbr_args, args)
    response_json = json.dumps(response.__dict__)
    logger("GEO").info(
        "sending kml with request_type: %s", response.request_type
    )
    queue.put(response_json)


def get_rad_coverage_kml_below_rad(Z_list, queue, rad_id, flight_height, rcs,  rad_lat, rad_lon, theta_res, dist_step, max_distance, request_type, start_theta=0, end_theta=360):
    """
    returns a rad acoverage kml for coverage below sensor
    """

    x = int(Z_list.shape[0])/3 # Z_list contains [lat,lon,los][lat,lon,los]...
    Z_d = np.reshape(Z_list, [int(x),3])
    azimuths = np.arange(start_theta, end_theta+theta_res, theta_res) # these are in degrees, they are used here only to get the SHAPES (we are using normal contourf and not a polar contourf)
    zeniths = np.arange(0, max_distance+dist_step, dist_step)

    if (start_theta == -1): # this means dat afor 4 quadrants are delivered (also end_theta will be here -1)
        azimuths = np.arange(0, 360 + theta_res, theta_res)


    len_az = azimuths.shape[0]
    len_zen = zeniths.shape[0]

    Zz0 = Z_d[:,0] # lats
    Zz1 = Z_d[:,1] # lons
    Zz2 = Z_d[:,2] # los [0/1]
    
    len_az = int(np.shape(Zz2)[0] / len_zen) # to avoid matrix size errors

    Y = np.reshape(Zz0, (len_az, len_zen))
    X = np.reshape(Zz1, (len_az, len_zen))
    Z = np.reshape(Zz2, (len_az, len_zen))

    #plt.ion()
    figure = plt.figure()
    axs  = figure.add_subplot(111, aspect = 1)    
    axs.clear()

    #levels = np.linspace(-1, 1, 40)
    levels = np.power(10, np.linspace(-1,2,3))
    norm = mc.BoundaryNorm(levels, 256)

    contour = axs.contourf(X, Y, Z, levels=levels, cmap=plt.jet(), norm=norm)
    #cbar = plt.colorbar(contour, ax=axs)

    kml = simplekml.Kml(open=1)
    polyname= 'RAD_ID:' + str(rad_id) + '/mASL:' + str(flight_height) + '/RCS:' + str(rcs)
    file_name = "/tmp/" + str(rad_id) + "_" + str(flight_height) + "mASL_RCS1"  + ".kml"
    logging.getLogger("GEO").debug("saving kml file as: %s", file_name)

    # now get all the polygons in the contourf plot and make a kml file from them
    nofpolys = 0
    for collection in contour.collections:
        for path in collection.get_paths():
            path.should_simplify = False
            for polygon in path.to_polygons(): 
                nofpolys = nofpolys + 1
                #print polygon.__class__
                polycolor = collection.get_facecolor().tolist()[0]
                mytuple = basefunctions.totuple(polygon)
                if (nofpolys == 1):                
                    pol = kml.newpolygon(name=polyname)
                else:
                    pol = kml.newpolygon(name="")
                # set the boundaries of the polygon
                pol.outerboundaryis = mytuple
                                
                # set color of polygon border lines
                pol.style.linestyle.color = simplekml.Color.rgb(int(polycolor[0]*255.0), int(polycolor[1]*255.0), int(polycolor[2]*255.0), 255)
                pol.style.linestyle.width = 1
                pol.style.polystyle.fill = 1
                pol.style.polystyle.outline = 1
                # fill polygon with transparent color (color same as the line color)
                pol.style.polystyle.color = simplekml.Color.rgb(int(polycolor[0]*255.0), int(polycolor[1]*255.0), int(polycolor[2]*255.0), 255) #r,g,b,transparency
           

    kml.save(file_name)
    snd_msg = json.dumps(kml.kml())
    nbr_args = 1
    args=[snd_msg];                               
    response = requestwrapper.RequestWrapper(request_type+"_response", nbr_args, args)                
    response_json = json.dumps(response.__dict__)
    logging.getLogger("GEO").debug("sending kml with request_type: %s", response.request_type)
    queue.put(response_json)


def get_rad_coverage_kml_above_rad(Z, queue, rad_id, flight_height, rcs, request_type):
    """
    returns a kml file for rad coverage above sensor
    """

    kml = simplekml.Kml()
    polyname= 'RAD_ID:' + str(rad_id) + '/mASL:' + str(flight_height) + '/RCS:' + str(rcs)
    ZZ = np.array(Z)
    ZZ[:,0] = Z[:,1]
    ZZ[:,1] = Z[:,0]
    ZZ_out = ZZ[np.where(ZZ[:,2] == 1.0)]
    ZZ_in = ZZ[np.where(ZZ[:,2] == 0.0)]
    mytuple_out = tuple(ZZ_out[:,0:2])
    mytuple_in = tuple(ZZ_in[:,0:2])

    inner_bounds = []
    for i in range(0,ZZ_in.shape[0]):
        inner_bounds.append((ZZ_in[i,0], ZZ_in[i,1], flight_height))
    pol = kml.newpolygon(name=polyname, outerboundaryis=mytuple_out, innerboundaryis=inner_bounds)

    file_name = "/tmp/" + str(rad_id) + "_" + str(flight_height) + "mASL_RCS1"  + ".kml"
    logging.getLogger("GEO").debug("saving kml file as: %s", file_name)
    kml.save(file_name) # just for debugging
    snd_msg = json.dumps(kml.kml())
    nbr_args = 1
    args=[snd_msg]                              
    response = requestwrapper.RequestWrapper(request_type+"_response", nbr_args, args)                
    response_json = json.dumps(response.__dict__)
    logging.getLogger("GEO").debug("sending kml with request_type: %s", response.request_type)
    queue.put(response_json)


def get_kml_object_simple(gridparams, Z, flight_height):
    """
    returns a kml file using matplotlib and simplekml
    """
    kml = simplekml.Kml(name="contour_polygons")
    Z = np.asarray(Z)
    Z = Z.astype(float)
    Z[Z == -1] = np.nan
    # avoid values above 100 (NaN)
    Z[Z > 100] = np.nan
    # values below 0.1 (and not -1): set to 0.1
    Z[Z < 0.1] = 0.1

    lons, lats, _ = geofunctions.create_range_rcs_gridpoints(gridparams)
    X = lons
    Y = lats

    # Create a contour plot plot from grid (lat, lon) data
    figure = plt.figure()
    ax = figure.add_subplot(111)
    levels = np.power(10, np.linspace(-1, 2, 50))
    norm = mc.BoundaryNorm(levels, 256)
    contour = ax.contourf(X, Y, Z, levels=levels, cmap=plt.jet(), norm=norm)
    #cbar = plt.colorbar(contour, ax=ax)

    # plt.show()
    plt.savefig("/tmp/contour_pcl.png")

    levels = contour.levels
    kml_name = "PCL@" + "masl:" + str(flight_height)
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
                pol = kml.newpolygon(name=kml_name)
                kml_name = ""
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

    kml.save("/tmp/simple_pr_contours.kml")
    return kml.kml()


class GeoplotWebSocketHandler(tornado.websocket.WebSocketHandler):
    """
    Geoplot Tornado websocket server
    """
    def __init__(self, val1, val2):
        tornado.websocket.WebSocketHandler.__init__(self, val1, val2)
        self.scheduler = None

    def check_origin(self, origin):
        return True

    # the client connected
    def open(self):
        logging.getLogger("GEO").info("New Geoplot client connected; ")


    def on_close(self):
        if self.scheduler != None:
            self.scheduler.wait_time_secs = -1

    # the client sent the message
    def on_message(self, message):
        line = message
        logging.getLogger("GEO").info(
            " received message of size = %s ", sys.getsizeof(line)
        )
        if line is None:
            logging.getLogger("GEO").info("line is None...returning")
            return
        if isinstance(line, Unicode):
            self.scheduler = Scheduler(self, 1)
            self.scheduler.schedule_func()
            # print("-----------------------------geoplot received query: ", line)
            request_received = json.loads(line, object_hook=to_request)
            logging.getLogger("GEO").info(
                "------received request to: %s", request_received.request_type
            )

            ### ------------------------------------CALCULATE PR COVERAGE1 ---------------------------------------------------------
            if request_received.request_type == "createKMLforRCSgrid":
                logging.getLogger("GEO").info("computing PR coverage 1...")

                rcs_grid_params = json.loads(
                    request_received.args[0], object_hook=to_grid_params
                )
                rcs_heatmap_one_height = json.loads(request_received.args[1])
                flight_height = json.loads(request_received.args[2])
                kml_object = get_kml_object_simple(
                    rcs_grid_params, rcs_heatmap_one_height, flight_height
                )

                if kml_object != "":
                    logging.getLogger("GEO").info(
                        "sending back PR coverage 1 kml file..."
                    )
                    snd_msg = json.dumps(kml_object)

                    nbr_args = 1
                    args = [snd_msg]
                    response = requestwrapper.RequestWrapper(
                        request_received.request_type + "_response", nbr_args, args
                    )
                    response_json = json.dumps(response.__dict__)
                    logging.getLogger("GEO").debug(
                        "sending kml with request_type: %s", response.request_type
                    )
                    self.write_message(response_json)
                 

                ### --------------------------------------KML FILES----------------------------------
            elif request_received.request_type == "getKMLFileList":
                logging.getLogger("GEO").info("get kml file names query received..")
                kml_files = []
                
                kml_files = next(os.walk(openburst_config.KML_FILE_PATH))[2]
                nbr_args = 1
                args = [json.dumps(kml_files)]
                kml_files_response = requestwrapper.RequestWrapper(
                    request_received.request_type + "_response", nbr_args, args
                )
                response_json = json.dumps(kml_files_response.__dict__)
                logging.getLogger("GEO").info(
                    "going to send to client kml file name list.."
                )
                self.write_message(response_json)

            elif request_received.request_type == "getKMLFile":
                file_name = json.loads(request_received.args[0])
                filename = openburst_config.KML_FILE_PATH + file_name
                logging.getLogger("GEO").info(
                    "get kml file query received with filename: %s", filename
                )
                doc = open(filename, "r", encoding="utf-8").read()

                if doc != "":
                    logging.getLogger("GEO").info("sending back one kml file...")
                    nbr_args = 1
                    args = [json.dumps(doc)]
                    kml_files_response = requestwrapper.RequestWrapper(
                        request_received.request_type + "_response", nbr_args, args
                    )
                    response_json = json.dumps(kml_files_response.__dict__)
                    logging.getLogger("GEO").info("sending to client...")
                    self.write_message(response_json)

            elif request_received.request_type == "activeCoveragePoints":
                logging.getLogger("GEO").info("active coverage points request")
                # format: np.array([559765, rad_id, flight_height, rcs, rad_height, lat,lon,1, lat, lon,1,...]); see demServer.py routine: getRadarCoverageNewProcess
                coverage_points = json.loads(request_received.args[0])
                cov_pos = np.array(json.loads(coverage_points))
                cov_pos2 = cov_pos.astype(float)

                cov_pos3 = np.array(cov_pos2[5:])

                rad_id = int(cov_pos2[1])
                flight_height = int(cov_pos2[2])
                rcs = int(cov_pos2[3])
                rad_height = int(cov_pos2[4])

                if (flight_height > rad_height) and (
                    rcs > 0
                ):  # the demServer returns one kind of output if target above radar height
                    # with PET sensor coverage, rcs is set to -1, and we always want to plot below radar like for PET coverage
                    logging.getLogger("GEO").info("active coverage above radar....")
                    x = int(int(cov_pos3.shape[0]) / 3)

                    cov_pos4 = np.reshape(cov_pos3, [x, 3])
                    logging.getLogger("GEO").info(
                        "shape of cov_pos4 = %s ", cov_pos4.shape
                    )
                    process = mp.Process(
                        target=get_rad_coverage_kml_above_rad,
                        args=(
                            cov_pos4,
                            self.scheduler.queue,
                            rad_id,
                            flight_height,
                            rcs,
                            request_received.request_type,
                        ),
                    )
                    process.start()
                else:  # the demServer returns another kind of output if target below radar height
                    logging.getLogger("GEO").info(
                        "active coverage below radar or PET coverage...."
                    )

                    rad_lat = float(cov_pos2[5])
                    rad_lon = float(cov_pos2[6])
                    theta_res = float(cov_pos2[7])
                    dist_step = float(cov_pos2[8])
                    max_distance = float(cov_pos2[9])
                    start_theta = float(cov_pos2[10])
                    end_theta = float(cov_pos2[11])
                    
                    # 559999, rad_id, flight_height, -1, radar_z + radar_z_offset, radar_lat, radar_lon, theta_res, dist_step, max_distance
                    cov_pos4 = np.array(cov_pos2[12:])

                    if cov_pos4.shape[0] == 1:
                        filename = "/tmp/" + str(int(cov_pos4[0])) + ".burst"
                        with open(filename, "rb") as filehandle:
                            cov_pos4 = np.array(pickle.load(filehandle))
                            cov_pos4 = cov_pos4.ravel()

                        logging.getLogger("GEO").info("cov_pos4 loaded from disk")

                    logging.getLogger("GEO").info(
                        "shape of cov_pos4 = %s ", cov_pos4.shape
                    )

                    process = mp.Process(
                        target=get_rad_coverage_kml_below_rad,
                        args=(
                            cov_pos4,
                            self.scheduler.queue,
                            rad_id,
                            flight_height,
                            rcs,
                            rad_lat,
                            rad_lon,
                            theta_res,
                            dist_step,
                            max_distance,
                            request_received.request_type,
                            start_theta,
                            end_theta,
                        ),
                    )
                    process.start()
            elif request_received.request_type == "activeCoveragePointsPropagation":
                logging.getLogger("GEO").info(
                    "active coverage points request with Propagation model"
                )
                # format: np.array([919765, rad_id, flight_height, rcs, radar_z + radar_z_offset, radar_lat, radar_lon, theta_res, dist_step, max_distance]); see demserver.py get_radar_coverage_above_Sensor
                coverage_points = json.loads(request_received.args[0])
                cov_pos = np.array(json.loads(coverage_points))
                cov_pos2 = cov_pos.astype(float)
                cov_pos3 = np.array(cov_pos2[5:])
                rad_id = int(cov_pos2[1])
                flight_height = int(cov_pos2[2])
                rcs = int(cov_pos2[3])
                rad_height = int(cov_pos2[4])

                rad_lat = float(cov_pos2[5])
                rad_lon = float(cov_pos2[6])
                theta_res = float(cov_pos2[7])
                dist_step = float(cov_pos2[8])
                max_distance = float(cov_pos2[9])

                cov_pos4 = np.array(cov_pos2[10:])

                process = mp.Process(
                    target=get_rad_coverage_kml,
                    args=(
                        cov_pos4,
                        self.scheduler.queue,
                        rad_id,
                        flight_height,
                        rcs,
                        rad_lat,
                        rad_lon,
                        theta_res,
                        dist_step,
                        max_distance,
                        request_received.request_type,
                    ),
                )
                process.start()


class Application(tornado.web.Application):
    """
    Tornado Application class for geoplot server module
    """
    def __init__(self):
        base_dir = os.path.dirname(__file__)
        settings = {
            "template_path": os.path.join(base_dir, "../templates"),
            "static_path": os.path.join(base_dir, "../static"),
        }

        tornado.web.Application.__init__(
            self,
            [
                (r"/geoplot", GeoplotWebSocketHandler),
            ],
            **settings
        )


def main():
    """
    Main routine
    """
    logger_dir = basefunctions.get_openburst_logging_dir()
    logger_file = logger_dir + "burst_geo_logging.json"
    logger = basefunctions.setup_logging(logger_file, "GEO")

    logger.info(
        "----------------------------------------------------------------------------------------"
    )
    logger.info(
        "-------------------------------------GEOPLOT Server newly started---------------------------"
    )
    logger.info(
        "----------------------------------------------------------------------------------------"
    )

    myip = basefunctions.get_myip()
    port = openburst_config.GEOPLOT_SERVER_PORT
    dbfunctions.write_server_start_to_db(
        "geoplot", myip, port
    )  # write to db that server started (this name should be the same as the opened port ending "/geoplot" !!)

    try:
        tornado.options.parse_command_line()
        Application().listen(port)
        main_loop = tornado.ioloop.IOLoop.instance()
        logging.getLogger("GEO").info(
            "-----------------GEO PLOT SERVER UP AND RUNNING..."
        )
        main_loop.start()
    except: # pylint: disable=bare-except
        logging.getLogger("GEO").error(
            "GEOPLOT Server initialization error! check 1) ip or port setting in servers.py, 2) check if DB-server running 3) and if DB schema and tables initiated correctly"
        )


if __name__ == "__main__":

    main()
