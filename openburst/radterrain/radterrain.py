"""
This Websocket server performs all DEM related computations, 
including multiprocessed LoS and propagation loss computations intergating splat via Boost and MPI.
"""
import time
import pickle
from functools import reduce
import json
import random
import multiprocessing as mp
import math
import os.path
import sys
import logging 
import geopy
import tornado.websocket
import numpy as np
import scipy.constants as sc
from haversine import haversine  

from openburst.functions import dbfunctions
from openburst.functions import basefunctions
from openburst.functions import geofunctions
from openburst.constants import splatconstants
from openburst.constants import radarconstants
from openburst.functions import radfunctions
from openburst.types.scheduler import Scheduler
from openburst.constants import openburst_config

if sys.version_info[0] >= 3:
    Unicode = str

basefunctions.set_openburst_system_path()
basefunctions.set_openburst_linked_lib_path()
import libsplathd as splat


def get_radar_coverage_above_Sensor(
    rad_id,
    flight_height,
    radar_lat,
    radar_lon,
    power,
    antenna_diam,
    freq,
    pulse_width,
    cpi_pulses,
    bandwidth,
    pfa,
    rcs,
    min_elev_deg,
    max_elev_deg,
    queue,
    radioprop_enabled=0,
):
    """
    computes radar coverage for a given altitude above the sensor
    """
    radar_h = geofunctions.get_terrain_height(splat,radar_lat, radar_lon)

    
    logger = logging.getLogger("DEM")

    snd_msg = np.array([559765, rad_id, flight_height, rcs, radar_h + radarconstants.RADAR_Z_OFFSET])
    ## this will be overwritten later if radioprop_enabled == 1

    origin = geopy.Point(radar_lat, radar_lon)

    try:
        floats = radfunctions.radar_eq_max_dist(
            power, antenna_diam, freq, pulse_width, cpi_pulses, bandwidth, pfa, rcs
        )
    except ValueError:
        logger = logging.getLogger("DEM")
        logger.error(
            "could not connect to RAD server...check if RAD server running"
        )
        snd_msg = np.append(snd_msg, [])
        send_list = snd_msg.tolist()
        queue.put(json.dumps(send_list))
        return

    max_distance = floats
    origin = (radar_lat, radar_lon)

    flight_height_km = flight_height / 1000.0
    elev_dist = 0

    if flight_height > (radar_h + radarconstants.RADAR_Z_OFFSET):
        elev_dist = math.fabs(flight_height_km / math.tan(math.radians(max_elev_deg)))
    else:
        elev_dist = math.fabs(flight_height_km / math.tan(math.radians(min_elev_deg)))

    if elev_dist > max_distance:
        logger = logging.getLogger("DEM")
        logger.debug("flight above the radar antenna diagramm..returning")
        snd_msg = np.append(snd_msg, [])
        send_list = snd_msg.tolist()
        queue.put(json.dumps(send_list))
        return

    # resolution for range and azimuth
    dist_step = radarconstants.RAD_COVERAGE_DISTANCE_STEP  # kms
    theta_res = radarconstants.RAD_COVERAGE_THETA_STEP  # degrees
    asl = 1 # we use asl (and not agl)

    justlos = 1
    if radioprop_enabled == 1:
        justlos = 0
        snd_msg = np.array(
            [
                919765,
                rad_id,
                flight_height,
                rcs,
                radar_h + radarconstants.RADAR_Z_OFFSET,
                radar_lat,
                radar_lon,
                theta_res,
                dist_step,
                max_distance,
            ]
        )

    nofprocs = int(mp.cpu_count() / 2)  # gets the number of cpus using multiprocessing
    stop_at_first_los = 1  # set 1 for above radar coverage and 0 for below radar coverage

    max_north = geofunctions.burstvincentydistance(origin, max_distance, 0)
    max_east = geofunctions.burstvincentydistance(origin, max_distance, 90)
    max_south = geofunctions.burstvincentydistance(origin, max_distance, 180)
    max_west = geofunctions.burstvincentydistance(origin, max_distance, 270)

    mpi_max_lat = math.ceil(max_north.latitude)
    mpi_min_lat = math.floor(max_south.latitude)
    mpi_min_lon = math.floor(360.0 - max_east.longitude)
    mpi_max_lon = math.ceil(360.0 - max_west.longitude)

    print("rad loc ::::::::::::: ", origin)
    print("max_distance ======== ", max_distance)
    print(
        "min max for MPI ======= ", mpi_min_lat, mpi_max_lat, mpi_min_lon, mpi_max_lon
    )
    print("radar height[m] = ", (radar_h + radarconstants.RADAR_Z_OFFSET))
    print("flight height[m] = ", flight_height)

    dest_lat_arr = np.array([])
    dest_lon_arr = np.array([])
    theta_arr = np.array([])

    print("radterrain.py: creating dest_lat_ar, dest_lon_arr and theta_arr...")

    start = time.time()
    theta_arr = np.arange(0, 360, theta_res)
    dist_arr = np.arange(max_distance, 0 - dist_step, -1 * dist_step)
    x = geofunctions.tabulate(origin, theta_arr, dist_arr, geofunctions.get_dest_loc_from_dist_and_angle)
    y = x[0].ravel()
    dest_lat_arr = np.vectorize(lambda x: x.latitude)(y)
    dest_lon_arr = np.vectorize(lambda x: 360.0 - x.longitude)(y)
    theta_arr = x[1].ravel()
    nof_points_per_arr = dist_arr.shape[0]
    end = time.time()

    if justlos == 0:  # PROP computation seems to need a bit more of DEM
        mpi_min_lat = mpi_min_lat - 0.1
        mpi_max_lat = mpi_max_lat + 0.1
        mpi_min_lon = mpi_min_lon - 0.1
        mpi_max_lon = mpi_max_lon + 0.1
        stop_at_first_los = 0  # for prop computation we need to compute loss at each point

    print(
        "thetas and points computed in time[s] = ", end - start, "...starting splat..."
    )
    p_site = splat.prop_site()
    p_site.setLatLonBoundaries(mpi_min_lat, mpi_max_lat, mpi_min_lon, mpi_max_lon)

    ####################### compute LoS and Dist with MPI ################
    start = time.time()

    ret = p_site.getLosAndLossRadial(
        radar_lat,
        360.0 - radar_lon,
        (radar_h + radarconstants.RADAR_Z_OFFSET) / sc.foot,
        dest_lat_arr.tolist(),
        dest_lon_arr.tolist(),
        flight_height / sc.foot,
        freq,
        asl,
        nofprocs,
        justlos,
        nof_points_per_arr,
        stop_at_first_los,
    )
    end = time.time()

    print(
        "########### elapsed time [s] ",
        end - start,
        ", for ",
        (max_distance / dist_step) * (360.0 / theta_res),
        " splat calls with ",
        nofprocs,
        " parallel processes",
    )

    ####### and now get the matrices required
    mpi_los_arr = np.array(ret.readLosMatrix())
    mpi_dist_arr = np.array(ret.readDistMatrix())  # [m]

    if radioprop_enabled == 1:
        mpi_prop_loss_arr = np.array(ret.readLossMatrix())  # prop loss in dB
        mpi_free_loss_arr = np.array(ret.readFreeLossMatrix())  # free space loss in dB

        mpi_dist_arr = np.array(ret.readDistMatrix())  # distance in km from rad
        snd_msg = radfunctions.get_detection_latlon_matrix(
            power,
            antenna_diam,
            freq,
            pulse_width,
            cpi_pulses,
            bandwidth,
            pfa,
            rcs,
            mpi_los_arr,
            mpi_prop_loss_arr,
            mpi_free_loss_arr,
            mpi_dist_arr,
            dest_lat_arr,
            dest_lon_arr,
            max_distance,
            queue,
            rad_id,
            radar_lat,
            radar_lon,
            theta_res,
            dist_step,
            snd_msg,
            flight_height,
            radar_h,
            radarconstants.RADAR_Z_OFFSET,
            origin,
            max_elev_deg,
            theta_arr,
        )

    else:  # i.e. if propagation model not used
        # now loop through the los and prepare snd message
        delta_h_km = (
            flight_height - (radar_h + radarconstants.RADAR_Z_OFFSET)
        ) / 1000.0  # assuming flight is above radar
        min_xydist_m = math.fabs(
            (flight_height - (radar_h + radarconstants.RADAR_Z_OFFSET))
            / math.tan(math.radians(max_elev_deg))
        )
        max_xydist_m = 1000.0 * math.sqrt(
            max_distance * max_distance - delta_h_km * delta_h_km
        )

        ind = mpi_los_arr.shape[0] - 1
        runner = 0
        while ind > -1:
            clos = mpi_los_arr[ind]
            cdist = mpi_dist_arr[ind]  # [m]
            clat = dest_lat_arr[ind]
            clon = 360.0 - dest_lon_arr[ind]
            ctheta = theta_arr[ind]
            min_dest = geofunctions.burstvincentydistance(origin, min_xydist_m / 1000.0, ctheta)
            max_dest = geofunctions.burstvincentydistance(origin, max_xydist_m / 1000.0, ctheta)

            if (
                (clos == 1)
                and (cdist <= max_xydist_m)
                and (cdist >= min_xydist_m)
                and (cdist >= 0.0)
            ):
                snd_msg = np.append(snd_msg, [clat, clon, 1.0])
                snd_msg = np.append(
                    snd_msg, [min_dest.latitude, min_dest.longitude, 0.0]
                )
                ind = ind - (nof_points_per_arr - runner)  # jump to the next ray
                runner = 0

            elif (
                (clos == 1)
                and (cdist > max_xydist_m)
                and (cdist >= min_xydist_m)
                and (cdist >= 0.0)
            ):
                snd_msg = np.append(
                    snd_msg, [max_dest.latitude, max_dest.longitude, 1.0]
                )
                snd_msg = np.append(
                    snd_msg, [min_dest.latitude, min_dest.longitude, 0.0]
                )
                ind = ind - (nof_points_per_arr - runner)  # jump to the next ray
                runner = 0

            elif (cdist < min_xydist_m) and (
                cdist >= 0.0
            ):  # cdist < 0 would mean it is under ground level
                snd_msg = np.append(
                    snd_msg, [min_dest.latitude, min_dest.longitude, 1.0]
                )
                snd_msg = np.append(
                    snd_msg, [min_dest.latitude, min_dest.longitude, 0.0]
                )
                ind = ind - (nof_points_per_arr - runner)  # jump to the next ray
                runner = 0
            elif runner == nof_points_per_arr:
                snd_msg = np.append(
                    snd_msg, [min_dest.latitude, min_dest.longitude, 1.0]
                )
                snd_msg = np.append(
                    snd_msg, [min_dest.latitude, min_dest.longitude, 0.0]
                )
                runner = 0
                ind = ind - 1
            else:
                ind = ind - 1
                runner = runner + 1

    send_list = snd_msg.tolist()
    queue.put(json.dumps(send_list))


def get_radar_coverage_below_sensor(
    rad_id,
    flight_height,
    radar_lat,
    radar_lon,
    power,
    antenna_diam,
    freq,
    pulse_width,
    cpi_pulses,
    bandwidth,
    pfa,
    rcs,
    min_elev,
    max_elev,
    queue,
    radioprop_enabled=0,
    magl_enabled=0,
):
    """
    computes radar coverage for a given altitude below the sensor
    """
    radar_h = geofunctions.get_terrain_height(splat,radar_lat, radar_lon)
    logger = logging.getLogger("DEM")
    logger.info("computing rad coverage below sensor")

    origin = geopy.Point(radar_lat, radar_lon)

    # now get the max detection distance of the radar
    snd_msg = np.array([])
    try:
        floats = radfunctions.radar_eq_max_dist(
            power, antenna_diam, freq, pulse_width, cpi_pulses, bandwidth, pfa, rcs
        )
    except ValueError:
        logger = logging.getLogger("DEM")
        logger.error("could not get RAD max range")
        snd_msg = np.append(snd_msg, [])
        send_list = snd_msg.tolist()
        queue.put(json.dumps(send_list))
        return

    max_distance = floats
    origin = (radar_lat, radar_lon)
    lat_min = geofunctions.burstvincentydistance(origin, max_distance, 180).latitude
    lat_max = geofunctions.burstvincentydistance(origin, max_distance, 0).latitude
    lon_min = geofunctions.burstvincentydistance(origin, max_distance, 270).longitude
    lon_max = geofunctions.burstvincentydistance(origin, max_distance, 90).longitude
    logging.getLogger("DEM").info(
        "=======> max_distance = %s, lat_min = %s, lat_max = %s, lon_min = %s, lon_max = %s ",
        max_distance,
        lat_min,
        lat_max,
        lon_min,
        lon_max,
    )

    flight_height_km = flight_height / 1000.0
    elev_dist = math.fabs(flight_height_km / math.tan(math.radians(min_elev)))

    if elev_dist > max_distance:
        logger = logging.getLogger("DEM")
        logger.debug("flight below the radar antenna diagramm..returning")
        snd_msg = np.append(snd_msg, [])
        send_list = snd_msg.tolist()
        queue.put(json.dumps(send_list))
        return

    ####### crucial resolution parameters
    ##  no differnce visually seen when using 0.5 dist_step and 0.5 theta_res (running time 3 hrs Monterosa) and dist_step:1 and theta_res:1 (running time 40min Monterosa)
    dist_step = radarconstants.RAD_COVERAGE_DISTANCE_STEP
    theta_res = radarconstants.RAD_COVERAGE_THETA_STEP
    asl = 1

    justlos = 1
    if radioprop_enabled == 1:
        justlos = 0
    nofprocs = int(mp.cpu_count() / 2)  # gets the number of cpus using multiprocessing
    stop_at_first_los = 0  # set 1 for above radar coverage and 0 for below radar coverage

    snd_msg = np.array(
        [
            559765,
            rad_id,
            flight_height,
            rcs,
            radar_h + radarconstants.RADAR_Z_OFFSET,
            radar_lat,
            radar_lon,
            theta_res,
            dist_step,
            max_distance,
            0,
            360,
        ]
    )
    snd_msg_empty = snd_msg

    max_north = geofunctions.burstvincentydistance(origin, max_distance, 0)
    max_east = geofunctions.burstvincentydistance(origin, max_distance, 90)
    max_south = geofunctions.burstvincentydistance(origin, max_distance, 180)
    max_west = geofunctions.burstvincentydistance(origin, max_distance, 270)

    mpi_max_lat = math.ceil(max_north.latitude)
    mpi_min_lat = math.floor(max_south.latitude)
    mpi_min_lon = math.floor(360.0 - max_east.longitude)
    mpi_max_lon = math.ceil(360.0 - max_west.longitude)

    logger.info("rad loc ::::::::::::: %s", origin)
    logger.info("max_distance ======== %s", max_distance)
    logger.info("radar height[m] = %s", (radar_h + radarconstants.RADAR_Z_OFFSET))
    logger.info("flight height[m] = %s", flight_height)

    dest_lat_arr = np.array([])
    dest_lon_arr = np.array([])
    theta_arr = np.array([])

    logger.info("creating dest_lat_ar, dest_lon_arr and theta_arr...")

    start = time.time()
    theta_arr = np.arange(0, 360 + theta_res, theta_res)
    dist_arr = np.arange(0, max_distance + dist_step, dist_step)
    x = geofunctions.tabulate(origin, theta_arr, dist_arr, geofunctions.get_dest_loc_from_dist_and_angle)
    y = x[0].ravel()
    dest_lat_arr = np.vectorize(lambda x: x.latitude)(y)
    dest_lon_arr = np.vectorize(lambda x: 360.0 - x.longitude)(y)
    theta_arr = x[1].ravel()
    nof_points_per_arr = dist_arr.shape[0]
    end = time.time()
    print("array shapes = ", dest_lat_arr.shape, dest_lon_arr.shape, theta_arr.shape, dist_arr.shape)

    if justlos == 0:  # PROP computation seems to need a bit more of DEM
        mpi_min_lat = mpi_min_lat - 0.1
        mpi_max_lat = mpi_max_lat + 0.1
        mpi_min_lon = mpi_min_lon - 0.1
        mpi_max_lon = mpi_max_lon + 0.1

    print(
        "thetas and points computed in time[s] = ", end - start, "...starting splat..."
    )
    p_site = splat.prop_site()
    p_site.setLatLonBoundaries(mpi_min_lat, mpi_max_lat, mpi_min_lon, mpi_max_lon)

    # compute LoS and Dist with MPI ################
    start = basefunctions.get_time()
    if magl_enabled == 1:
        asl = 0
        radar_h = 0

    ret = p_site.getLosAndLossRadial(
        radar_lat,
        360.0 - radar_lon,
        (radar_h + radarconstants.RADAR_Z_OFFSET) / sc.foot,
        dest_lat_arr.tolist(),
        dest_lon_arr.tolist(),
        flight_height / sc.foot,
        freq,
        asl,
        nofprocs,
        justlos,
        nof_points_per_arr,
        stop_at_first_los,
    )

    end = basefunctions.get_time()

    print(
        "########### elapsed time [s] ",
        end - start,
        ", for ",
        (max_distance / dist_step) * (360.0 / theta_res),
        " splat calls with ",
        nofprocs,
        " parallel processes",
    )

    # and now get the matrices required
    mpi_los_arr = np.array(ret.readLosMatrix())
    mpi_dist_arr = np.array(ret.readDistMatrix())  # [m]

    # now loop through the los and prepare snd message
    delta_h_km = (
        (radar_h + radarconstants.RADAR_Z_OFFSET) - flight_height
    ) / 1000.0  # assuming flight is below radar
    min_xydist_m = math.fabs(
        ((radar_h + radarconstants.RADAR_Z_OFFSET) - flight_height) / math.tan(math.radians(min_elev))
    )
    max_xydist_m = 1000.0 * math.sqrt(
        max_distance * max_distance - delta_h_km * delta_h_km
    )

    cov_list = []
    logger.info("..........writing LOS LAT LON LIST")
    start = time.time()
    tmparr = np.array(
        [mpi_los_arr, mpi_dist_arr, dest_lat_arr, 360.0 - dest_lon_arr, theta_arr]
    )

    los_cols = np.where((tmparr[0, :]) == 1)
    cdist_maxok_cols = np.where((tmparr[1, :]) <= max_xydist_m)
    cdist_minok_cols = np.where((tmparr[1, :]) >= min_xydist_m)
    cdist_pos_cols = np.where((tmparr[1, :]) >= 0.0)


    good_indices = reduce(
        np.intersect1d, (los_cols, cdist_maxok_cols, cdist_minok_cols, cdist_pos_cols)
    )

    index_arr = np.where(mpi_los_arr != None) # do not set this to "is not None"
    bad_indices = np.setdiff1d(index_arr, good_indices)


    cov_list1 = np.column_stack(
        (
            np.ravel(np.array([good_indices])),
            dest_lat_arr[good_indices],
            360.0 - dest_lon_arr[good_indices],
            np.ones(np.array(good_indices).shape[0]),
        )
    )
    cov_list0 = np.column_stack(
        (
            np.ravel(np.array([bad_indices])),
            dest_lat_arr[bad_indices],
            360.0 - dest_lon_arr[bad_indices],
            np.zeros(np.array(bad_indices).shape[0]),
        )
    )

    cov_list = np.row_stack((cov_list1, cov_list0))
    cov_list = cov_list[cov_list[:, 0].argsort()]
    cov_list = np.array(cov_list[:, 1:])
    cov_list = cov_list.flatten()
    end = basefunctions.get_time()
    logger.info("........finished writing LOS LAT LON LIST in %s [s]", end - start)
    

    snd_msg = np.append(snd_msg, cov_list)
    send_list = snd_msg.tolist()
    if sys.getsizeof(send_list) < 500000:
        queue.put(json.dumps(send_list))
    else:
        rnd_nr = random.randint(10, 100000)
        rnd_filename = "/tmp/" + str(rnd_nr) + ".burst"
        snd_msg_new = np.append(snd_msg_empty, [rnd_nr])
        # write send_list to file
        logger.info(
            "radar coverage below radar send_list too big..wrote to file: %s", rnd_filename
        )
        # now write the coverage to the disk
        with open(rnd_filename, "wb") as filehandle:
            # store the data as binary data stream
            pickle.dump(cov_list, filehandle)

        time.sleep(5)
        send_list_new = snd_msg_new.tolist()
        queue.put(json.dumps(send_list_new))



def get_pet_coverage_for_quadrant(queue, radar_h, theta_res, dist_step, rad_id, flight_height, radar_lat, radar_lon, erp_dbm, threshold_dbm, freq, quadrant, radioprop_enabled=0, use_antenna_diag = 0, h_antenna_diagramm =None, v_antenna_diagramm = None, main_beam_azimuth=0, main_beam_elevation=0, magl_enabled=0):
    """"
    returns pet coverage for a given quadrant
    """
    logger = logging.getLogger("DEM")
    logger.info("demServer: get_pet_coverage_for_quadrant %s; ", quadrant)
    origin = geopy.Point(radar_lat, radar_lon)
    snd_msg = np.array([])
    try:
        floats = radfunctions.pet_eq_max_dist(erp_dbm, threshold_dbm, freq)  
    except ValueError:
        logger.error("..could not connect to RAD server...check if RAD server running")
        snd_msg = np.append(snd_msg, [])
        send_list = snd_msg.tolist()
        queue.put(json.dumps(send_list))
        return


    max_distance = floats

    if (max_distance > 900):
        logger.error("! PET MAX DISTANCE EXCEEDING SPLAT MAXPAGES LIMITS..setting max distance to 900km")
        max_distance = 900

    origin = (radar_lat, radar_lon)
    lat_min, lat_max, lon_min, lon_max = geofunctions.get_latlon_box_for_midpoint(origin, max_distance, quadrant)

    logger.info("=======> max_distance = %s, lat_min = %s, lat_max = %s, lon_min = %s, lon_max = %s ",
                                  max_distance, lat_min, lat_max, lon_min, lon_max)

    # asl is default to 1, if agl is used we will change it later
    asl = 1

    justlos = 1
    if (radioprop_enabled == 1):
        justlos = 0
    nofprocs = int(mp.cpu_count() / 2)   # gets the number of cpus using multiprocessing
    stopatfirstlos = 0  


    # to compute RAD AGL coverage at mAGL=x meters: 
    if (magl_enabled == 1):
        asl = 0
        radar_h = 0 # we want to send the AGL value to SPLAT!
        logging.getLogger("DEM").info("------------------------------------> MAGL ENABLED")

    mpi_max_lat = math.ceil(lat_max)  
    mpi_min_lat = math.floor(lat_min)  
    mpi_max_lon = math.ceil(360.0 - lon_min)  
    mpi_min_lon = math.floor(360.0 - lon_max)  
    

    dest_lat_arr = np.array([])
    dest_lon_arr = np.array([])
    theta_arr = np.array([])

    logger.info("creating dest_lat_ar, dest_lon_arr and theta_arr...")

    start = time.time()

    if (quadrant == 1):
        theta_arr = np.arange(0, 90+theta_res, theta_res)
    if (quadrant == 2):
        theta_arr = np.arange(90, 180+theta_res, theta_res)
    if (quadrant == 3):
        theta_arr = np.arange(180, 270+theta_res, theta_res)
    if (quadrant == 4):
        theta_arr = np.arange(270, 360+theta_res, theta_res)

    #theta_arr = np.arange(0, 360 + theta_res, theta_res)
    dist_arr = np.arange(0, max_distance + dist_step, dist_step)
    x = geofunctions.tabulate(origin, theta_arr, dist_arr, geofunctions.get_dest_loc_from_dist_and_angle)
    y = x[0].ravel()
    dest_lat_arr = np.vectorize(lambda x: x.latitude)(y)
    dest_lon_arr = np.vectorize(lambda x: 360.0 - x.longitude)(y)
    theta_arr = x[1].ravel()
    nof_points_per_arr = dist_arr.shape[0]
    end = basefunctions.get_time()

    if (justlos == 0):  # PROP computation seems to need a bit more of DEM
        mpi_min_lat = mpi_min_lat - 0.1
        mpi_max_lat = mpi_max_lat + 0.1
        mpi_min_lon = mpi_min_lon - 0.1
        mpi_max_lon = mpi_max_lon + 0.1

    logger.info("thetas and points computed in time[s] = %s, starting splat!", end - start)
    p_site = splat.prop_site()
    p_site.setLatLonBoundaries(mpi_min_lat, mpi_max_lat, mpi_min_lon, mpi_max_lon)

    # compute LoS and Dist with MPI 
    start = basefunctions.get_time()


    ret = p_site.getLosAndLossRadial(radar_lat, 360.0 - radar_lon, (radar_h + radarconstants.RADAR_Z_OFFSET) / sc.foot,
                                     dest_lat_arr.tolist(), dest_lon_arr.tolist(), flight_height / sc.foot, freq, asl,
                                     nofprocs, justlos, nof_points_per_arr, stopatfirstlos)

    end = basefunctions.get_time()

    print("########### elapsed time [s] ", end - start, ", for ", (max_distance / dist_step) * (360.0 / theta_res),
          " splat calls with ", nofprocs, " parallel processes")

    # and now get the matrices required
    mpi_los_arr = np.array(ret.readLosMatrix())
    mpi_dist_arr = np.array(ret.readDistMatrix())  # [m]

    # now loop through the los and prepare snd message
    delta_h_km = ((radar_h + radarconstants.RADAR_Z_OFFSET) - flight_height) / 1000.0  # assuming flight is below radar
    min_xydist_m = 0.1 

    max_xydist_m = 1000.0 * math.sqrt(max_distance * max_distance - delta_h_km * delta_h_km)

    if (use_antenna_diag == 1): # here antenna diagramm will be used to compute max_xydist_m again for each lat,lon
        max_xydist_m = []
        for ind in range(len(dest_lat_arr.tolist())):
            clat = dest_lat_arr[ind]
            clon = 360.0 - dest_lon_arr[ind]
            xydist = geofunctions.get_2d_distance_between_locs(origin[0], origin[1], clat, clon) * 1000.0
            deltaheight = flight_height - (radar_h + radarconstants.RADAR_Z_OFFSET)
            alpha = math.atan2(deltaheight,  xydist)  # angle on vertical plane towards target
            alpha = math.degrees(alpha)
            if (alpha < 0.0):
                alpha = 360 + alpha
            
            ctheta = theta_arr[ind] # azimuth in degrees
            curr_max_xydist_m = radfunctions.pet_get_max_dist_with_ant_diag(alpha, ctheta, erp_dbm, threshold_dbm, freq, h_antenna_diagramm, v_antenna_diagramm, main_beam_azimuth, main_beam_elevation)
            max_xydist_m = np.append(max_xydist_m, curr_max_xydist_m)
            
    ind = mpi_los_arr.shape[0] - 1
    logger.info("..........writing LOS LAT LON LIST")
    start = time.time()
    tmparr = np.array([mpi_los_arr, mpi_dist_arr, dest_lat_arr, 360.0 - dest_lon_arr, theta_arr])

    los_cols = np.where((tmparr[0, :]) == 1)
    if (use_antenna_diag == 1):
        cdist_maxok_cols = np.where((tmparr[1, :]) <= max_xydist_m[:])
    else:
        cdist_maxok_cols = np.where((tmparr[1, :]) <= max_xydist_m)

    cdist_minok_cols = np.where((tmparr[1, :]) >= min_xydist_m)
    cdist_pos_cols = np.where((tmparr[1, :]) >= 0.0)

    good_indices = reduce(np.intersect1d, (los_cols, cdist_maxok_cols, cdist_minok_cols, cdist_pos_cols))

    index_arr = np.where(mpi_los_arr != None) # do not set this to is not None
    bad_indices = np.setdiff1d(index_arr, good_indices)

    cov_list1 = np.column_stack((np.ravel(np.array([good_indices])), dest_lat_arr[good_indices],
                                 360.0 - dest_lon_arr[good_indices], np.ones(np.array(good_indices).shape[0])))
    cov_list0 = np.column_stack((np.ravel(np.array([bad_indices])), dest_lat_arr[bad_indices],
                                 360.0 - dest_lon_arr[bad_indices], np.zeros(np.array(bad_indices).shape[0])))

    end = time.time()
    logger.info(".......finished writing LOS LAT LON LIST in %s [s]", end - start)


    return max_distance, cov_list1, cov_list0


def get_pcl_max_los_grid_splat(
    radar_lon,
    radar_lat,
    radar_h,
    lon_start,
    lon_stop,
    lon_step,
    lat_start,
    lat_stop,
    lat_step,
    z_start,
    z_stop,
    z_step,
    loc_name,
    propagation,
    reverse_direction,
    sig_type,
    wished_nof_lats,
    wished_nof_lons,
):
    """
    Returns an array containing the minimum height in masl required at each grid point 
    to have LoS. If no LoS even at terrain height then -999 will be the value.
    It also computes propagation losses and save to disk for a given query.
    
    """


    logger = logging.getLogger("DEM")

    # make sure that we will have exactly the number of lats and lons 
    # and Z on the grid as requested by the query

    stepped_nof_lons = math.floor((lon_stop - lon_start) / lon_step)
    stepped_nof_lats = math.floor((lat_stop - lat_start) / lat_step)
    #nof_z = math.floor((z_stop - z_start) / z_step)

    if wished_nof_lats > stepped_nof_lats:
        lat_stop = lat_stop + lat_step / 2.0
    if wished_nof_lats < stepped_nof_lats:
        lat_stop = lat_stop - lat_step / 2.0
    if wished_nof_lons > stepped_nof_lons:
        lon_stop = lon_stop + lon_step / 2.0
    if wished_nof_lons < stepped_nof_lons:
        lon_stop = lon_stop - lon_step / 2.0

    logger.info(
        "demServer.get_pcl_max_los_grid_splat: wished_nof_lon  %s, wished_nof_lats = %s",
        wished_nof_lons,
        wished_nof_lats,
    )

    lon_arr = 360.0 - np.linspace(
        lon_start, lon_stop, num=wished_nof_lons
    )  # will create exactly num number of floats
    lat_arr = np.linspace(
        lat_start, lat_stop, num=wished_nof_lats
    )  # will create exactly num number of floats

    start = time.time()
    if propagation == 0:
        justlos = 1  # not computing propagation losses
    else:
        justlos = 0  # compute propagation losses
    asl = 1
    nofprocs = 8  # number of processes for MPI (ideally equal to number of cores)
    
    # for computign propagation losses we assume a certain frequency per signal type
    if sig_type == "FM":
        freq = 90.0  # MHZ
    if sig_type == "DAB":
        freq = 200.0  # MHZ
    if sig_type == "DVB":
        freq = 600.0  # MHZ

    p_site = splat.prop_site()
    p_site.setLatLonBoundaries(
        lat_start - 1.0, lat_stop + 1.0, 360 - lon_stop - 1.0, 360 - lon_start + 1.0
    )
    #compute LoS, prop_loss and free_space loss or just Los (set justlos= 1).
    # we compute just for one Z (=z_start)
    ret = p_site.getLosAndLossMatrix(
        radar_lat,
        360.0 - radar_lon,
        radar_h / sc.foot,
        lat_arr.tolist(),
        lon_arr.tolist(),
        z_start / sc.foot,
        freq,
        asl,
        nofprocs,
        justlos,
        reverse_direction,
    )  # to check if reversedirection correct
    end = time.time()
    logger.info(
        "########### elapsed time [s] %s, with %s parallel processes",
        end - start,
        nofprocs,
    )

    los_arr = np.array(ret.readLosMatrix())

    sav_arr2 = np.where(los_arr == 1, z_start, -999)

    sav_arr3 = sav_arr2.reshape(lat_arr.shape[0], lon_arr.shape[0])

    return sav_arr3.tolist()


class RadTerrainWebSocketHandler(tornado.websocket.WebSocketHandler):
    """
    Tornado Websocket handler
    """    

    def __init__(self, val1, val2):
        tornado.websocket.WebSocketHandler.__init__(self, val1, val2)
        self.scheduler = Scheduler(self, 2.0)
        self.scheduler.schedule_func()
        self.logger = None

    def check_origin(self, origin):
        return True

    # the client connected
    def open(self):
        self.logger = logging.getLogger("DEM")
        self.logger.info("New DEM client connected; ")

    def on_close(self):
        self.scheduler.wait_time_secs = -1
        self.logger.info("DEM Client disconnected")

    # the client sent the message
    def on_message(self, message):
        
        line = message

        if line is None:
            self.logger.info("DEM Client: line is none")
            return
        if isinstance(line, Unicode):
            self.logger.info("-------------received query: %s", line)
            # first split line t get the data for all queries
            alldata = line.split("&")
            headerdata = alldata[0]

            # now get the individual data in the main data
            maindata = headerdata.split(",")

            #maindata2 = headerdata.split(";")

            try:
                tmp_d = int(maindata[0])
                if (
                    tmp_d == 6200901
                ):  # this is request for terrain height at a lat lon

                    c_lat = float(maindata[1])
                    c_lon = float(maindata[2])
                    poi_lat = float(maindata[3])
                    poi_lon = float(maindata[4])
                    heigh = geofunctions.get_terrain_height(splat,c_lat, c_lon)
                    p1 = (c_lat, c_lon)
                    p2 = (poi_lat, poi_lon)
                    dist = haversine(p1, p2)
                    tmp_msg = [int(6200901), int(heigh), float(dist)]
                    snd_msg = json.dumps(tmp_msg)
                    self.write_message(snd_msg)

                elif (
                    tmp_d == 6200902
                ):  # this is request for terrain height at a lat lon

                    c_lat = float(maindata[1])
                    c_lon = float(maindata[2])
                    poi_lat = float(maindata[3])
                    poi_lon = float(maindata[4])
                    heigh = geofunctions.get_terrain_height(splat,c_lat, c_lon)
                    dist = 0
                    tmp_msg = [int(6200902), int(heigh), float(dist)]
                    snd_msg = json.dumps(tmp_msg)
                    self.write_message(snd_msg)
                elif (
                    tmp_d == 6200903
                ):  # this is request for terrain height at a lat lon for PCL

                    c_lat = float(maindata[1])
                    c_lon = float(maindata[2])
                    poi_lat = float(maindata[3])
                    poi_lon = float(maindata[4])

                    heigh = geofunctions.get_terrain_height(splat,c_lat, c_lon)
                    dist = 0
                    tmp_msg = [int(6200903), int(heigh), float(dist)]
                    snd_msg = json.dumps(tmp_msg)
                    self.write_message(snd_msg)

                elif tmp_d == 559765:  # this is radar coverage computation request
                    logger = logging.getLogger("DEM")
                    logger.info(
                        "=============================in radar coverage computation request"
                    )
                    radar_id = int(maindata[1])
                    radar_lat = float(maindata[2])
                    radar_lon = float(maindata[3])
                    flight_height = float(maindata[4])
                    power = int(maindata[5])
                    antenna_diam = float(maindata[6])
                    freq = float(maindata[7])
                    pulse_width = float(maindata[8])
                    cpi_pulses = int(maindata[9])
                    bandwidth = int(maindata[10])
                    pfa = float(maindata[11])
                    rcs = float(maindata[12])
                    min_elev = float(maindata[13])
                    max_elev = float(maindata[14])
                    radioprop_enabled = int(maindata[15])
                    magl_enabled = int(maindata[16])

                    radar_h = geofunctions.get_terrain_height(splat,radar_lat, radar_lon)

                    
                    if (flight_height >= (radar_h + radarconstants.RADAR_Z_OFFSET)) and (
                        magl_enabled == 0
                    ):  # if target above radar height
                        logger = logging.getLogger("DEM")
                        logger.info("computing coverage for target ABOVE radar...")
                        process = mp.Process(
                            target=get_radar_coverage_above_Sensor,
                            args=(
                                radar_id,
                                flight_height,
                                radar_lat,
                                radar_lon,
                                power,
                                antenna_diam,
                                freq,
                                pulse_width,
                                cpi_pulses,
                                bandwidth,
                                pfa,
                                rcs,
                                min_elev,
                                max_elev,
                                self.scheduler.queue,
                                radioprop_enabled,
                            ),
                        )
                        process.start()
                    else:  # if target under radar height or magl computation
                        process = mp.Process(
                            target=get_radar_coverage_below_sensor,
                            args=(
                                radar_id,
                                flight_height,
                                radar_lat,
                                radar_lon,
                                power,
                                antenna_diam,
                                freq,
                                pulse_width,
                                cpi_pulses,
                                bandwidth,
                                pfa,
                                rcs,
                                min_elev,
                                max_elev,
                                self.scheduler.queue,
                                radioprop_enabled,
                                magl_enabled,
                            ),
                        )
                        
                        self.logger.info("computing coverage for target below radar...")
                        process.start()

                elif tmp_d == 559999:  # this is PET coverage computation request

                    self.logger.info(
                        "=============================in PET coverage computation request"
                    )
                    radar_id = int(maindata[1])
                    radar_lat = float(maindata[2])
                    radar_lon = float(maindata[3])
                    flight_height = float(maindata[4])
                    erp_dbm = float(maindata[5])
                    threshold_dbm = float(maindata[6])
                    freq = float(maindata[7])
                    radioprop_enabled = int(maindata[8])
                    use_antenna_diag = int(maindata[9])
                    main_beam_azimuth = int(maindata[10])
                    main_beam_elevation = int(maindata[11])
                    magl_enabled = int(maindata[12])

                    # now read the antennad diagramms from file in PET directory
                    h_filename = "../PET/sample_h_gains_copolar.txt"
                    v_filename = "../PET/sample_v_gains_copolar.txt"
                    (h_antenna_diagramm, v_antenna_diagramm) = geofunctions.read_pet_antenna_diags(
                        radar_id, h_filename, v_filename
                    )

                    radar_h = geofunctions.get_terrain_height(splat,radar_lat, radar_lon)

                    self.logger.info("computing coverage for PET...")
                    ####### crucial resolution parameters
                    ##  for ASL: 0.5 dist_Step is more than enough, 1.0 dist_step is quite good also, theta_res = 0.9
                    # for AGL (eg 100mAGL) the resolution is very important. set dist_step <= 1.0 and theta_res = 0.9
                    dist_step = 5.0
                    theta_res = 0.1

                    max_distance, covlist1_q1, covlist0_q1 = get_pet_coverage_for_quadrant(
                        self.scheduler.queue,
                        radar_h,
                        theta_res,
                        dist_step,
                        radar_id,
                        flight_height,
                        radar_lat,
                        radar_lon,
                        erp_dbm,
                        threshold_dbm,
                        freq,
                        1,
                        radioprop_enabled,
                        use_antenna_diag,
                        h_antenna_diagramm,
                        v_antenna_diagramm,
                        main_beam_azimuth,
                        main_beam_elevation,
                        magl_enabled
                    )
                    index = 0
                    cov_list_q1 = np.row_stack((covlist1_q1, covlist0_q1))
                    cov_list_q1 = cov_list_q1[cov_list_q1[:, 0].argsort()]
                    cov_list_q1 = np.array(cov_list_q1[:, 1:])
                    index = index + cov_list_q1.shape[0]

                    max_distance, covlist1_q2, covlist0_q2 = get_pet_coverage_for_quadrant(
                        self.scheduler.queue,
                        radar_h,
                        theta_res,
                        dist_step,
                        radar_id,
                        flight_height,
                        radar_lat,
                        radar_lon,
                        erp_dbm,
                        threshold_dbm,
                        freq,
                        2,
                        radioprop_enabled,
                        use_antenna_diag,
                        h_antenna_diagramm,
                        v_antenna_diagramm,
                        main_beam_azimuth,
                        main_beam_elevation,
                        magl_enabled,
                    )
                    cov_list_q2 = np.row_stack((covlist1_q2, covlist0_q2))
                    cov_list_q2 = cov_list_q2[cov_list_q2[:, 0].argsort()]
                    cov_list_q2 = np.array(cov_list_q2[:, 1:])

                    covlist1_q2[:, 0] += index
                    covlist0_q2[:, 0] += index
                    index = index + cov_list_q2.shape[0]

                    max_distance, covlist1_q3, covlist0_q3 = get_pet_coverage_for_quadrant(
                        self.scheduler.queue,
                        radar_h,
                        theta_res,
                        dist_step,
                        radar_id,
                        flight_height,
                        radar_lat,
                        radar_lon,
                        erp_dbm,
                        threshold_dbm,
                        freq,
                        3,
                        radioprop_enabled,
                        use_antenna_diag,
                        h_antenna_diagramm,
                        v_antenna_diagramm,
                        main_beam_azimuth,
                        main_beam_elevation,
                        magl_enabled,
                    )

                    cov_list_q3 = np.row_stack((covlist1_q3, covlist0_q3))
                    cov_list_q3 = cov_list_q3[cov_list_q3[:, 0].argsort()]
                    cov_list_q3 = np.array(cov_list_q3[:, 1:])

                    covlist1_q3[:, 0] += index
                    covlist0_q3[:, 0] += index
                    index = index + cov_list_q3.shape[0]

                    max_distance, covlist1_q4, covlist0_q4 = get_pet_coverage_for_quadrant(
                        self.scheduler.queue,
                        radar_h,
                        theta_res,
                        dist_step,
                        radar_id,
                        flight_height,
                        radar_lat,
                        radar_lon,
                        erp_dbm,
                        threshold_dbm,
                        freq,
                        4,
                        radioprop_enabled,
                        use_antenna_diag,
                        h_antenna_diagramm,
                        v_antenna_diagramm,
                        main_beam_azimuth,
                        main_beam_elevation,
                        magl_enabled,
                    )

                    cov_list_q4 = np.row_stack((covlist1_q4, covlist0_q4))
                    cov_list_q4 = cov_list_q4[cov_list_q4[:, 0].argsort()]
                    cov_list_q4 = np.array(cov_list_q4[:, 1:])

                    covlist1_q4[:, 0] += index
                    covlist0_q4[:, 0] += index
                    index = index + cov_list_q4.shape[0]

                    # now append all the results and send it through the queue
                    cov_list = np.row_stack(
                        (
                            covlist1_q1,
                            covlist1_q2,
                            covlist1_q3,
                            covlist1_q4,
                            covlist0_q1,
                            covlist0_q2,
                            covlist0_q3,
                            covlist0_q4,
                        )
                    )
                    cov_list = cov_list[cov_list[:, 0].argsort()]
                    cov_list = np.array(cov_list[:, 1:])

                    cov_list = cov_list.flatten()
                    snd_msg = np.array(
                        [
                            559999,
                            radar_id,
                            flight_height,
                            -1,
                            radar_h + radarconstants.PET_Z_OFFSET,
                            radar_lat,
                            radar_lon,
                            theta_res,
                            dist_step,
                            max_distance,
                            -1,
                            -1,
                        ]
                    )

                    snd_msg_empty = snd_msg
                    snd_msg = np.append(snd_msg, cov_list)

                    send_list = snd_msg.tolist()
                    if sys.getsizeof(send_list) < 500000:
                        self.scheduler.queue.put(json.dumps(send_list))
                    else:
                        rnd_nr = random.randint(10, 100000)
                        rnd_filename = "/tmp/" + str(rnd_nr) + ".burst"
                        snd_msg_new = np.append(snd_msg_empty, [rnd_nr])
                        # write send_list to file
                        logging.getLogger("DEM").info(
                            "PET send_list too big..wrote to file"
                        )
                        # now write the coverage to the disk
                        with open(rnd_filename, "wb") as filehandle:
                            # store the data as binary data stream
                            pickle.dump(cov_list, filehandle)

                        time.sleep(5)
                        send_list_new = snd_msg_new.tolist()
                        self.scheduler.queue.put(json.dumps(send_list_new))


                elif (
                    tmp_d == 6193758
                ):  # this is passive radar max LOS grid computation request
                    logger = logging.getLogger("DEM")
                    logger.info(
                        "=============================in passive radar max LOS grid computation request"
                    )
                    radar_lon = float(maindata[1])
                    # x - lon
                    radar_lat = float(maindata[2])
                    # y - lat
                    radar_h = float(maindata[3])
                    # masl
                    lon_start = float(maindata[4])
                    # lon
                    lon_stop = float(maindata[5])
                    # lon
                    lon_step = float(maindata[6])
                    #
                    lat_start = float(maindata[7])
                    # lat
                    lat_stop = float(maindata[8])
                    # lat
                    lat_step = float(maindata[9])
                    #
                    z_start = float(maindata[10])
                    # masl
                    z_stop = float(maindata[11])
                    # masl
                    z_step = float(maindata[12])
                    # meter
                    loc_name = maindata[13]  # Name/Callsign of Rx or Tx as String
                    propagation = int(
                        maindata[14]
                    )  # set to 1 to compute propagation losses
                    reverse_direction = int(
                        maindata[15]
                    )  # reverse direction of propagation computation
                    sig_type = maindata[16]  # signal type FM/DAB/DVB/GRAVES
                    nof_lats = int(maindata[17])  # nof y_axis points
                    nof_lons = int(maindata[18])  # nof x_axis points

                
                    LOS_grid_arr = get_pcl_max_los_grid_splat(
                        radar_lon,
                        radar_lat,
                        radar_h,
                        lon_start,
                        lon_stop,
                        lon_step,
                        lat_start,
                        lat_stop,
                        lat_step,
                        z_start,
                        z_stop,
                        z_step,
                        loc_name,
                        propagation,
                        reverse_direction,
                        sig_type,
                        nof_lats,
                        nof_lons,
                    )
                    tmp_msg = [6193758, LOS_grid_arr]
                    snd_msg = json.dumps(tmp_msg)
                    logger = logging.getLogger("DEM")
                    logger.debug("sending: Response for max LOS grid computation")
                    self.write_message(snd_msg)


                elif tmp_d == 29824733:  # this detailed prop loss computation request
                    print("demServer got prop computation req: ", maindata)
                    tx_lat = round(
                        float(maindata[1]), 4
                    )  # without rounding splat-hd seems to hang
                    tx_lon = round(float(maindata[2]), 4)
                    tx_antenna_height = round(float(maindata[3]), 4)
                    rx_lat = round(float(maindata[4]), 4)
                    rx_lon = round(float(maindata[5]), 4)
                    rx_antenna_height = round(float(maindata[6]), 4)
                    diel_const = float(maindata[7])
                    earth_cond = float(maindata[8])
                    at_bend = float(maindata[9])
                    freq = float(maindata[10])
                    radio_climate = float(maindata[11])
                    pol = float(maindata[12])
                    #ground_clutter = float(maindata[13])
                    #oitm = float(maindata[14])
                    #detailed_analysis = float(maindata[15])
                    #erp = float(maindata[16])

                    tx_path = "./SPLAT_RADIOPROP/tx.qth"
                    tx_file = open(tx_path, "w")
                    tx_file.write("TX \n" + str(tx_lat) + "\n")
                    tx_file.write(str(360.0 + tx_lon) + "\n")
                    tx_file.write(str(tx_antenna_height) + "\n")
                    tx_file.close()

                    rx_path = "./SPLAT_RADIOPROP/rx.qth"
                    rx_file = open(rx_path, "w")
                    rx_file.write("RX \n" + str(rx_lat) + "\n")
                    rx_file.write(str(360.0 + rx_lon) + "\n")
                    rx_file.write(str(rx_antenna_height) + "\n")
                    rx_file.close()

                    lrp_path = "./SPLAT_RADIOPROP/tx.lrp"
                    lrp_file = open(lrp_path, "w")
                    lrp_file.write(str(diel_const) + "\n")
                    lrp_file.write(str(earth_cond) + "\n")
                    lrp_file.write(str(at_bend) + "\n")
                    lrp_file.write(str(freq) + "\n")
                    lrp_file.write(str(radio_climate) + "\n")
                    lrp_file.write(str(pol) + "\n")
                    lrp_file.write(str(0.5) + "\n")
                    lrp_file.write(str(0.9) + "\n")
                    lrp_file.close()

                    runstr = (
                        " cd SPLAT_RADIOPROP && ./splat-hd -t tx.qth -r rx.qth -metric -olditm -d "
                        + splatconstants.DEM_FILES_PATH
                        + " -m 1.333 -H height_profile.png "
                    )
                    os.system(
                        runstr
                    )  # ./splat-hd -t tx.qth -r rx.qth -metric -olditm -d /home/red3/Downloads/SRTM3_Eurasia_Data/SDF_Files -m 1.333 -H height_profile.png
                    os.system(
                        " cd SPLAT_RADIOPROP && python3 generate_json_from_png_and_txt.py"
                    )

                    with open("./SPLAT_RADIOPROP/tmp.json") as json_file:
                        data = json.load(json_file)
                        tmp_msg = [29824733, data]
                        snd_msg = json.dumps(tmp_msg)
                        logger = logging.getLogger("DEM")
                        logger.info(
                            "sending: Response for point to point PROPAGATION computation"
                        )
                        self.write_message(snd_msg)

                elif tmp_d == 3456178:  # this is request for elevation matrix
                    
                    tx_lat = round(
                        float(maindata[1]), 4
                    )  # without rounding splat-hd seems to hang
                    tx_lon = round(
                        float(maindata[2]), 4
                    )  # without rounding splat-hd seems to hang
                    max_distance = float(maindata[3])  # km
                    origin = (tx_lat, tx_lon)

                    lat_res = 0.001
                    lon_res = 0.001

                    max_north = geofunctions.burstvincentydistance(origin, max_distance, 0)
                    max_east = geofunctions.burstvincentydistance(origin, max_distance, 90)
                    max_south = geofunctions.burstvincentydistance(origin, max_distance, 180)
                    max_west = geofunctions.burstvincentydistance(origin, max_distance, 270)

                    mpi_max_lat = math.ceil(max_north.latitude)
                    mpi_min_lat = math.floor(max_south.latitude)
                    mpi_min_lon = math.floor(360.0 - max_east.longitude)
                    mpi_max_lon = math.ceil(360.0 - max_west.longitude)

                    # we need to get 30m resolution for lat and lon to make use of the max DEM resolution
                    # compute lat-lon dist between points
                    #loc1 = (max_south.latitude, max_west.longitude)
                    #loc2 = (max_north.latitude, max_west.longitude)

                    dist_ns = (
                        geofunctions.get_2d_distance_between_locs(
                            max_south.latitude,
                            max_west.longitude,
                            max_north.latitude,
                            max_west.longitude,
                        )
                        * 1000.0
                    )

                    #loc3 = (max_south.latitude, max_west.longitude)
                    #loc4 = (max_south.latitude, max_east.longitude)

                    dist_ew = geofunctions.get_2d_distance_between_locs(
                        max_south.latitude,
                        max_west.longitude,
                        max_south.latitude,
                        max_east.longitude,
                    )

                    nof_lats = dist_ns / 30.0
                    lat_res = (
                        math.fabs(max_north.latitude - max_south.latitude) / nof_lats
                    )
                    nof_lons = dist_ew / 30.0
                    lon_res = (
                        math.fabs(max_west.longitude - max_east.longitude) / nof_lats
                    )

                    dest_lat_arr = np.arange(
                        max_south.latitude, max_north.latitude, lat_res
                    )
                    dest_lon_arr = np.arange(
                        max_west.longitude, max_east.longitude, lon_res
                    )

                    xv, yv = np.meshgrid(dest_lat_arr, dest_lon_arr)
                    dest_lat_arr_new = xv.ravel()
                    dest_lon_arr_new = 360.0 - yv.ravel()

                    p_site = splat.prop_site()
                    p_site.initialize_heavy(
                        mpi_min_lat,
                        mpi_max_lat,
                        mpi_min_lon,
                        mpi_max_lon,
                        splatconstants.DIEL_CONST,
                        splatconstants.EARTH_COND,
                        splatconstants.AT_BEND,
                        splatconstants.RADIO_CLIMATE,
                        splatconstants.POL,
                        splatconstants.FRAC_OF_SITU,
                        splatconstants.FRAC_OF_TIME,
                        splatconstants.GROUND_CLUTTER,
                    )

                    elev_arr = []
                    elev_arr = np.array(
                        p_site.getElevationsMatrix(
                            dest_lat_arr_new.tolist(), dest_lon_arr_new.tolist()
                        )
                    )
                    elev_arr_grid = np.reshape(
                        elev_arr, (dest_lon_arr.shape[0], dest_lat_arr.shape[0])
                    )

                    #tmp_arr1 = np.linspace(
                    #    -1.0 * (dist_ns / 2.0), dist_ns / 2.0, num=dest_lat_arr.shape[0]
                    #)

                    tmp_arr2 = np.linspace(
                        -1.0 * (dist_ew / 2.0),
                        dist_ew / 2.0,
                        num=elev_arr_grid.shape[0],
                    )
                    tmp_arr2 = np.reshape(tmp_arr2, (elev_arr_grid.shape[0], 1))

                    x_data = np.linspace(
                        -1 * max_distance * 1000.0,
                        max_distance * 1000,
                        num=elev_arr_grid.shape[0],
                    )
                    y_data = np.linspace(
                        -1 * max_distance * 1000.0,
                        max_distance * 1000,
                        num=elev_arr_grid.shape[1],
                    )

                    tmp_msg = [
                        3456178,
                        np.transpose(elev_arr_grid).tolist(),
                        dist_ns,
                        dist_ew,
                        x_data.tolist(),
                        y_data.tolist(),
                    ]
                    snd_msg = json.dumps(tmp_msg)
                    logger = logging.getLogger("DEM")
                    logger.debug("sending: Response for elev matrix computation")
                    self.write_message(snd_msg)

                else: 
                    return

            except ValueError:
                logger = logging.getLogger("DEM")
                logger.error("error in received data: %s", alldata)
                snd_msg = "query error! expected format: query_id,data,&"
                logger.error("sending answer to los query: %s", snd_msg)
                self.write_message(snd_msg)


class Application(tornado.web.Application):
    """
    Tornado Application class
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
                (r"/dem", RadTerrainWebSocketHandler),
            ],
            **settings
        )


def main():
    """
    main function
    """

    logger_dir = basefunctions.get_openburst_logging_dir()
    logger_file = logger_dir + "burst_dem_logging.json"
    logger = basefunctions.setup_logging(logger_file, "DEM")

    [ip, port] = dbfunctions.read_server_ip_port_from_db("rad")
    global ws_str
    ws_str = "ws://" + ip + ":" + str(port) + "/" + "rad"

    # if logger.isEnabledFor(logging.DEBUG):
    logger.info("matlab ws_str = %s", ws_str)

    logger.info(
        "----------------------------------------------------------------------------------------"
    )
    logger.debug(
        "-------------------------------------DEM Server newly started---------------------------"
    )
    logger.info(
        "----------------------------------------------------------------------------------------"
    )

    myip = basefunctions.get_myip()
    port = openburst_config.DEM_SERVER_PORT
    dbfunctions.write_server_start_to_db("dem", myip, port)
    tornado.options.parse_command_line()
    Application().listen(port)
    main_loop = tornado.ioloop.IOLoop.instance()
    main_loop.start()

if __name__ == "__main__":

    main()
