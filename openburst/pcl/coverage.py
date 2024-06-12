""" 
Module for PCL coverage calculation
"""

import json
import logging
import math

from openburst.functions import basefunctions
from openburst.functions import geofunctions
from openburst.pcl import minrcs
from openburst.types import splatmanager

def get_antenna_los_grid(
    radar_x,
    radar_y,
    radar_z,
    x_start,
    x_stop,
    x_step,
    y_start,
    y_stop,
    y_step,
    z_start,
    z_stop,
    z_step,
    name,
    propagation,
    reverse_direction,
    signal_type,
    nof_lats,
    nof_lons,
):
    
    """computes the Line-of-Sight grid for an antenna location"""
    ws = basefunctions.open_connection_to_dem_server()
    # Send the request to calculate LOS via websocket
    query = (
        str(6193758)
        + ","
        + str(radar_x)
        + ","
        + str(radar_y)
        + ","
        + str(radar_z)
        + ","
        + str(x_start)
        + ","
        + str(x_stop)
        + ","
        + str(x_step)
        + ","
        + str(y_start)
        + ","
        + str(y_stop)
        + ","
        + str(y_step)
        + ","
        + str(z_start)
        + ","
        + str(z_stop)
        + ","
        + str(z_step)
        + ","
        + name
        + ","
        + str(propagation)
        + ","
        + str(reverse_direction)
        + ","
        + signal_type
        + ","
        + str(nof_lats)
        + ","
        + str(nof_lons)
        + "&"
    )

    ws.send(query)

    result = json.loads(
        ws.recv()
    )  # ws.recv() is string, result is an array. if no LOS, it will be 0.

    if result[0] != 6193758:
        logging.getLogger("PCL").debug(
            "-- on pass LOS grid request: wrong response ID from DEM Server"
        )

    # close websocket
    ws.close()

    return result[1]
   


def calculate_min_rcs_coverage_prop(
    snr_thresh, rx, tx, t_max, points_x, points_y, points_z, delay_thresh
):
    """ for min RCS computatation considering propagation losses tx-Tgt and Tgt-rx; 
    i.e. without using loss grids 
    """

    ############################################
    Rx_lat_lon = (rx.lat, rx.lon)
    max_north = geofunctions.burstvincentydistance(Rx_lat_lon, 150, 0) # we set 150 km max distance for PCL
    max_east = geofunctions.burstvincentydistance(Rx_lat_lon, 150, 90)
    max_south = geofunctions.burstvincentydistance(Rx_lat_lon, 150, 180)
    max_west = geofunctions.burstvincentydistance(Rx_lat_lon, 150, 270)

    max_lat = math.ceil(max_north.latitude)
    min_lat = math.floor(max_south.latitude)
    min_lon = math.floor(360.0 - max_east.longitude)
    max_lon = math.ceil(360.0 - max_west.longitude)

    print("calculate_min_rcs_coverage_prop: lat/lon bounds = ", min_lat, max_lat, min_lon, max_lon)
    
    ## for SPLAT
    manager = splatmanager.StateManager()#classes.StateManager()
    # start manager
    manager.start()
    #splat_obj = manager.SharedSPLAT(min_lat, max_lat, min_lon, max_lon)
    splat_obj = manager.pclcoveragesplat(min_lat, max_lat, min_lon, max_lon)#splatmanager.SharedSPLAT(min_lat, max_lat, min_lon, max_lon)

    logging.getLogger("PCL").info("----------  calling python function to calculate coverage with Propagation losses (minimal RCS without LOS restrictions)")
    time_start=basefunctions.get_time()
    
    #RCS_heatmap, SNR_heatmap = findMinRCSwithLOS.calcMinRCSWithLOS( SNR_thresh,1 , points_x, points_y, points_z, t_max, None, None, Rx, Tx, delay_thresh, 0, 1, None, 0, splat_obj)
    RCS_heatmap, SNR_heatmap = minrcs.calculate_min_rcs_with_los( snr_thresh,1 , points_x, points_y, points_z, t_max, None, None, rx, tx, delay_thresh, 0, 1, None, 0, splat_obj)

    time_stop=basefunctions.get_time()
    logging.getLogger("PCL").info("----------  python script finished within %f seconds", (time_stop-time_start))
    manager.shutdown() # this release the memory for the loaded DEM files for this coverage (we prefer memory than CPU)
    return RCS_heatmap, SNR_heatmap


    ##########################################3
"""
    rx_lat_lon = (rx.lat, rx.lon)
    max_north = geofunctions.burstvincentydistance(rx_lat_lon, 150, 0)
    # we set 150 km max distance for PCL
    max_east = geofunctions.burstvincentydistance(rx_lat_lon, 150, 90)
    max_south = geofunctions.burstvincentydistance(rx_lat_lon, 150, 180)
    max_west = geofunctions.burstvincentydistance(rx_lat_lon, 150, 270)

    max_lat = math.ceil(max_north.latitude)
    min_lat = math.floor(max_south.latitude)
    min_lon = math.floor(360.0 - max_east.longitude)
    max_lon = math.ceil(360.0 - max_west.longitude)

    print("calculate_min_rcs_coverage_prop: lat/lon bounds = ", min_lat, max_lat, min_lon, max_lon)

    ## for SPLAT
    manager = splatmanager.StateManager()
    # start manager
    manager.start()
    splat_obj = splatmanager.SharedSPLAT(min_lat, max_lat, min_lon, max_lon)

    logging.getLogger("PCL").info(
        "----------  calculate coverage with Propagation losses (minimal RCS without LOS restrictions)"
    )
    time_start = basefunctions.get_time()

    rcs_heatmap, snr_heatmap = minrcs.calculate_min_rcs_with_los(
        snr_thresh,
        1,
        points_x,
        points_y,
        points_z,
        t_max,
        None,
        None,
        rx,
        tx,
        delay_thresh,
        0,
        1,
        None,
        0,
        splat_obj,
    )

    time_stop = basefunctions.get_time()
    logging.getLogger("PCL").info(
        "----------  python script finished within %f seconds", (time_stop - time_start)
    )
    return rcs_heatmap, snr_heatmap

"""


def calculate_min_rcs_coverage(
    snr_thresh,
    rx,
    tx,
    t_max,
    max_los_arr_rx,
    max_los_arr_tx,
    points_x,
    points_y,
    points_z,
    delay_thresh,
    radioprop_enabled,
    radioprop_params,
):
    """ min RCS computation without propagation losses; 
    i.e. using the LOS Grids tx-Tgt and Tgt-rx"""
    static_rcs = 0  # m^2 (we do not use static RCS)
    use_grid = 1

    logging.getLogger("PCL").info(
        "----------  calling python function to calculate coverage (minimal RCS with LOS and Delay)"
    )
    time_start = basefunctions.get_time()
    rcs_heatmap, snr_heatmap = minrcs.calculate_min_rcs_with_los(
        snr_thresh,
        use_grid,
        points_x,
        points_y,
        points_z,
        t_max,
        max_los_arr_rx,
        max_los_arr_tx,
        rx,
        tx,
        delay_thresh,
        static_rcs,
        radioprop_enabled,
        radioprop_params,
    )

    time_stop = basefunctions.get_time()
    logging.getLogger("PCL").info(
        "----------  python script finished within %f seconds", (time_stop - time_start)
    )

    return rcs_heatmap, snr_heatmap
