"""
Function definitions for operations on the WGS84 projection and 
transformations to other projections.
"""

import math
from numpy import linspace
from numpy import meshgrid
import numpy as np
import geopy.distance
import scipy.constants as sc
from haversine import haversine  # for computing distance between two (lat, lon) points
from geographiclib.geodesic import Geodesic
from pyproj import Proj, transform # needed for transforming from Lat/Long to CH Lv93 coordinates
from openburst.functions import basefunctions

def get_azimuth_between_locs(lat1, lon1, lat2, lon2):

    """

    returns azimuth (clockwise from north between point1 and point2 given in lat lon) in radians
    The shortest path between two points on the ellipsoid at (lat1, lon1) and (lat2, lon2) is called the geodesic. 
    Its length is s12 and the geodesic from point 1 to point 2 has azimuths azi1 and azi2 at the two end points. 
    (The azimuth is the heading measured clockwise from north. azi2 is the "forward" azimuth, i.e., 
    the heading that takes you beyond point 2 not back to point 1.)

    Parameters
    ----------
    lat1, lon1 : source position
    lat2, lon2 : destination position

    Returns
    -------
    : tmp : azimuth in degrees

    References
    ----------
    https://geographiclib.sourceforge.io/2009-03/geodesic.html

    """


    tmp = Geodesic.WGS84.Inverse(lat1, lon1, lat2, lon2)
    return math.radians(tmp["azi1"])


def get_elev_angle(tgt_z, antenna_z, dist_tgt_antenna):

    """
    
    calculates the elevation angle given a target height, antenna height and distance from target to antenna

    Parameters
    ----------
    tgt_z : z position of target
    antenna_z: z position of antenna
    dist_tgt_antenna: distance between target and antenna on XY plane

    Returns
    -------
    : elev_angle
        returned in radians

    """

    try:
        elev_angle = math.asin((tgt_z - antenna_z) / dist_tgt_antenna)
        return elev_angle
    except ValueError as e:
        print("functions.py get_elev_angle Exception: ", e)
        return None


def get_2d_distance_between_locs(lat1, lon1, lat2, lon2):
    """
    
    calculates the 2D distance between two lat/lon values

    Parameters
    ----------
    lat1, lon1 : position 1
    lat2, lon2: position 2

    Returns
    -------
    : haversine between to points

    """

    p1 = (lat1, lon1)
    p2 = (lat2, lon2)
    return haversine(p1, p2)

def get_deg_from_ch(y, x): 
    """ returns lon, lat from Swissgrid coordinates """
    p_world = Proj(init="epsg:4326")
    p_ch = Proj(init="epsg:21781")
    lv = transform(p_ch, p_world, y, x, 0)
    return lv

def get_chf_from_deg(lat, lon):
    """! reads in lat/lon and returns CH1903 coordinates in y,x """
    p_world = Proj(init="epsg:4326")
    p_ch = Proj(init="epsg:21781")
    lv = transform(p_world,p_ch, lon, lat, 0)
    return lv 

def get_bistatic_range(tx_latlonalt, rx_latlonalt, tgt_latlonalt):
    """ returns bistatic range [km],  tgt_rx_range [km], tgt_tx_range [km], baseline_range [km])
        for given Tx, Rx and Target
        input Tx: lat, lon, alt[masl] + antenna height [magl]
        input Rx: lat, lon, alt[masl] + antenna height [magl]
        input tgt: lat, lon, alt[masl]
        definition bistatic range [km]  = distance(Tx -> Tgt -> Rx ) - distance(Rx->Tx) 
    """
    tx_tgt_range = get_2d_distance_between_locs_heights(tx_latlonalt[0], tx_latlonalt[1], tx_latlonalt[2], tgt_latlonalt[0], tgt_latlonalt[1], tgt_latlonalt[2])
    tgt_rx_range = get_2d_distance_between_locs_heights(rx_latlonalt[0], rx_latlonalt[1], rx_latlonalt[2], tgt_latlonalt[0], tgt_latlonalt[1], tgt_latlonalt[2])
    tx_rx_range = get_2d_distance_between_locs_heights(tx_latlonalt[0], tx_latlonalt[1], tx_latlonalt[2], rx_latlonalt[0], rx_latlonalt[1], rx_latlonalt[2])
    return (tx_tgt_range + tgt_rx_range  - tx_rx_range, tgt_rx_range, tx_tgt_range, tx_rx_range)

def calculate_bistatic_doppler(rx, tgt, tx):
    """ calculates bistatic Doppler in Hz
        for given Tx, Rx and Target
        input Tx: lat, lon, alt[masl], antenna height [magl]
        input Rx: lat, lon, alt[masl], antenna height [magl]
        input tgt: lat, lon, alt[masl]
        returns Doppler shift in [Hz]  

        The bistatic Doppler shift is computed from the rate of change (R_t + R_r) 
        divided by the wavelength of tx signal

        The returned bistatic Doppler [Hz] value can be negative, depending on the 
        velocity vector of the target 
    """
    rr1 = (
        get_2d_distance_between_locs_heights(
            tgt.lat, tgt.lon, tgt.height, rx.lat, rx.lon, rx.masl+rx.ahmagl
        )
        * 1000.0
    )
    rt1 = (
        get_2d_distance_between_locs_heights(
            tx.lat, tx.lon, tx.masl+tx.ahmagl, tgt.lat, tgt.lon, tgt.height
        )
        * 1000.0
    )
    
    # asuuming that the target will travel with the current velocity vector for the below time window
    time_diff = 0.0001 # [s]

    # tgt.vx is the vel [m/s] along lon axis
    # tgt.vy is the vel [m/s] along lat axis
    # tgt.vz is vel [m/a] along z axis
    # see also methods: create_target_replay_track and update_target_track in sensorController module
    
    tgt_total_vel = tgt.velocity * 1000/3600 # [m/s]
    tgt_xy_vel = math.sqrt(tgt_total_vel*tgt_total_vel - tgt.vz*tgt.vz) # [m/s]
    alpha = math.degrees(math.atan2(tgt.vx, tgt.vy))
    if alpha < 0:
        alpha = 360 + alpha # now alpha is on degrees from north

    # move the target along the bearing given by the vel vectors with the fiven velocity to find change in target pos
    new_lat_lon = burstvincentydistance((tgt.lat, tgt.lon), (tgt_xy_vel*time_diff)/1000, alpha)
    new_lat = new_lat_lon.latitude # this is the predicted target_position lat with the given vel
    new_lon = new_lat_lon.longitude # this is the predicted target_position lon with the given vel
    new_z = tgt.height + time_diff * tgt.vz
    
    # now compute bistatic range components R_T and R_R for the new target position
    rr2 = (
        get_2d_distance_between_locs_heights(
            new_lat, new_lon, new_z, rx.lat, rx.lon, rx.masl+rx.ahmagl
        )
        * 1000.0
    )
    rt2 = (
        get_2d_distance_between_locs_heights(
            tx.lat, tx.lon, tx.masl+tx.ahmagl, new_lat, new_lon, new_z
        )
        * 1000.0
    )
    # compute the rate of change for R_T (tx to target range) and R_R (tgt to rx range)
    
    rt_rate_of_change = (rt2-rt1)/time_diff
    rr_rate_of_change = (rr2-rr1)/time_diff

    wavelength = sc.speed_of_light / (tx.freq * 1000000 ) # FM: 2.78 to 3.41 meters
    doppler_shift = (rt_rate_of_change + rr_rate_of_change) / wavelength  # [Hz]


    #print("rt2-rt1 : ", rt2 - rt1, ", rr2 - rr1: ", rr2-rr1, ", doppler = ", doppler_shift)
    return doppler_shift


def monostatic_doppler(
    freq, rad_lat, rad_lon, rad_alt, tgt_lat, tgt_lon, tgt_alt, tgt_vx, tgt_vy, tgt_vz
):
    """computes Doppler shift in Hz from target motion as seen at ground stationary radar
    freq given in MHz, alts given in masl.
    returns None if tgt V == 0. tgt_V is given as m/s along the lon/lat/z axis
    see Class Target definition
    """

    if (tgt_vx == 0) and (tgt_vy == 0) and (tgt_vz == 0):
        return None

    az = get_azimuth_between_locs(rad_lat, rad_lon, tgt_lat, tgt_lon)  # radians
    xy_dist = (
        get_2d_distance_between_locs(rad_lat, rad_lon, tgt_lat, tgt_lon) * 1000.0
    )  # [m]
    # (gx,gy,gz) will be the vector looking at the target from the radar
    gx = xy_dist * math.cos(az)  # [m]
    gy = xy_dist * math.sin(az)  # [m]
    gz = tgt_alt - rad_alt  # [m]

    # now find the aspect angle (ie angle between (tgt_vx, tgt_vy, tgt_vz) and (gx,gy,gz))
    g = np.array([gx, gy, gz])  # [m]
    tgt_v = np.array([tgt_vx, tgt_vy, tgt_vz])  # [m/s]

    # project tgt_v on g
    proj_tgt_v = basefunctions.project_vector_u_on_v(tgt_v, g)

    # calculate aspect angle
    asp_angle = basefunctions.calc_angle_from_vecs(g, tgt_v)

    # get wavelength from freq where freq is given in GHz
    wv = sc.c / (freq * 1000000000)  # [m]

    # now compute Doppler shift
    dopp_shift = 2.0 * np.linalg.norm(proj_tgt_v) * math.cos(asp_angle) / wv
    return dopp_shift


def get_clear_sky_attenuation(transmitter_freq):
    """
    returns the clear sky atmospheric one-way attenuation in dB/km for Radar Windows,
    given the transmitter_freq in MHz

    Clear Sky weather values from Barton book: 'Modern Radar System Analysis'
    """

    freq_mhz = [200, 500, 1000, 10000]
    atten = [0.00075, 0.003, 0.0055, 0.012]
    # one-way attenuation: dB/km therefore division by 2
    atten_db = max(np.interp(transmitter_freq, freq_mhz, atten), 0)

    return atten_db

def get_2d_distance_between_locs_heights(lat1, lon1, h1, lat2, lon2, h2):
    """
    returns distance in kilometers between two lat lons and heights.
    geopy.distance does NOT consider altitude!! the solution below with haversine formula compared to geopy.distance without height are at 220km are identical upto a difference below 50m
    the solution here is not exactly correct, but good enough for our purposes
    for large geodesic distances (ie large distance on the ellipsoid surface) the difference is less than a few hundred meters
    assuming Earth's mean radius 6,371 km, adding 10 km to that adds about 0.16% to the geometric distance at 10 km altitude, ie about 300m
    see e.g. http://cosinekitty.com/compass.html
    h1, h2: meters
    """

    p1 = (lat1, lon1)
    p2 = (lat2, lon2)
    hav = haversine(p1, p2)
    xy_dist = hav * 1000.0  # [m]
    z_dist = abs(h2 - h1)
    total_dist = math.sqrt(xy_dist * xy_dist + z_dist * z_dist)
    return total_dist / 1000.0

# variable used by the "get_dest_loc_from_dist_and_angle" called from "tabulate" using np.vectorize
origin_for_tabulate = None

def tabulate(orig, x, y, f):
    """! Return a table of f(x, y)."""
    global origin_for_tabulate
    origin_for_tabulate = orig
    return np.vectorize(f)(*np.meshgrid(x, y, indexing="ij", sparse=False))

def get_dest_loc_from_dist_and_angle(theta, dist):
    """
    returns destination location (lat/lon) from distance and angle from global origin
    """
    dest = burstvincentydistance(origin_for_tabulate, dist, theta)
    return dest, theta


def burstvincentydistance(pnt, dist_km, brng):
    """! returns the destination [lat/lon] point at distance dist_km[km] and at bearing brng[deg] from point pnt[lat/lon]"""
    d = geopy.distance.distance(kilometers=dist_km)
    dest = d.destination(point=pnt, bearing=brng)
    return dest


def calculate_initial_compass_bearing(pointA, pointB):
    """! calculates bearing between two points: https://gist.github.com/jeromer/2005586"""
    if ((not isinstance(pointA, tuple)) or (not isinstance(pointB, tuple))):
        raise TypeError("Only tuples are supported as arguments")

    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])

    difflong = math.radians(pointB[1] - pointA[1])

    x = math.sin(difflong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (
        math.sin(lat1) * math.cos(lat2) * math.cos(difflong)
    )

    initial_bearing = math.atan2(x, y)

    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing


def read_pet_antenna_diags(_, h_filename, v_filename):
    """! will read antenna diagramms for H and V for PET or Richtstrahl from files and return them
    h_filename and v_filename are full filenames for the h and v gain files
    antenna diags are given for angles 0 to 360 for V and H in separate files in dB, assumed is max ERP at 0 degrees
    assumption: the file are given in angels -180 to 180, we need to convert it to 0..360 degrees
    """

    tmp_h = np.loadtxt(h_filename)
    tmp_h_first_half = tmp_h[180:-1]  # 0 to 180 degrees
    tmp_h_second_half = tmp_h[0:181]  # -180 to 0 degrees degrees
    h_antenna_diagramm = np.concatenate((tmp_h_first_half, tmp_h_second_half))

    tmp_v = np.loadtxt(v_filename)
    tmp_v_first_half = tmp_v[180:-1]  # 0 to 180 degrees
    tmp_v_second_half = tmp_v[0:181]  # -180 to 0 degrees degrees
    v_antenna_diagramm = np.concatenate((tmp_v_first_half, tmp_v_second_half))

    return (h_antenna_diagramm, v_antenna_diagramm)



def get_ch_from_deg(lat, lon):
    """! reads in lat/lon and returns CH1903 coordinates   in y,x"""
    pWorld = Proj(init="epsg:4326")
    pCH = Proj(init="epsg:21781")
    lv = transform(pWorld, pCH, lon, lat, 0)
    return lv


def compute_freespace_loss(freq, dist_meters):
    """! returns free space loss in dB given frequency and distance in meters (same computation as SPLAT)"""
    return 36.6 + (20.0 * math.log10(freq)) + (20.0 * math.log10(dist_meters / sc.mile))


def create_range_by_res(min_pt, max_pt, res):
    """creates a range of points, such that res is the resolution/spacing between the points. 
    min_pt and max_pt are definitively included in the result,  
    however if (max_pt-min_pt)%res != 0, the first entry of the result will be lower than min_pt, 
    as the last entry will be larger than max_pt.
    Thus max_x and min_y need updating hereafter"""

    mod_is_not_zero = (
        (max_pt - min_pt) % res
    ) != 0  # is false only when (max_pt-min_pt) is a multiple of res
    middle_pt = (max_pt + min_pt) / 2.0
    amt_pts = max(
        2, (max_pt - min_pt) // res + mod_is_not_zero + 1
    )  
    return np.arange(
        middle_pt - (amt_pts / 2.0 - 0.5) * res,
        middle_pt + ((amt_pts / 2.0 - 0.5) * res) + 0.000001,
        res,
    )  # starting and stop pts from middle/avg between the two points


def create_range_by_res_height(min_z, max_z, res_z):
    """creates a range of points by height resolution """
    if (res_z == 0) or (
        max_z - min_z < res_z
    ):  # Catch division by zero and empty array
        points_z = np.asarray([min_z])
    else:
        points_z = np.arange(min_z, max_z + 0.00001, res_z)
    return points_z
    # amt_pts and min, max might be wrong after this call


def create_range_by_nbr_points(min_pt, max_pt, nbr_pts):
    """creates a range of points by given number of points"""
    return np.linspace(min_pt, max_pt, nbr_pts)
    # Resoultion might be wrong after this call


def create_range_by_nbr_points_latlon(
    min_lat, max_lat, amt_pts_y, min_lon, max_lon, amt_pts_x
):
    """creates a range of points by lat/lon resolution """
    x = linspace(min_lon, max_lon, amt_pts_x)
    y = linspace(min_lat, max_lat, amt_pts_y)

    # make a meshgrid in global coordinates
    xx, yy = meshgrid(x, y)

    x_points = np.array(xx)
    y_points = np.array(yy)

    return x_points, y_points


def create_range_rcs_gridpoints(rcs_gridparams):
    """creates a grid given the parameters"""
    points_x, points_y = create_range_by_nbr_points_latlon(
        rcs_gridparams.lat_start,
        rcs_gridparams.lat_stop,
        rcs_gridparams.amt_pts_y,
        rcs_gridparams.lon_start,
        rcs_gridparams.lon_stop,
        rcs_gridparams.amt_pts_x,
    )  # assures there are amt_pts_x in range.
    points_z = create_range_by_res_height(
        rcs_gridparams.min_z, rcs_gridparams.max_z, rcs_gridparams.res_z
    )

    return points_x, points_y, points_z


def get_terrain_height(splat, p_lat, p_lon): 
    """ returns terrain height in [masl] for a given lat lon """ 
    loc = splat.prop_site()
    elev = loc.getElevationAtLoc(p_lat, 360.0 - p_lon)
    return elev


def get_latlon_box_for_midpoint(origin, max_distance, quadrant):
    """
    returns a lat/lon box end points given an origin and maximum distance
    """
    if quadrant == 1:
        lat_min = origin[0]
        lat_max = burstvincentydistance(origin, max_distance, 0).latitude
        lon_min = origin[1]
        lon_max = burstvincentydistance(origin, max_distance, 90).longitude

    if quadrant == 2:
        lat_min = burstvincentydistance(origin, max_distance, 180).latitude
        lat_max = origin[0]
        lon_min = origin[1]
        lon_max = burstvincentydistance(origin, max_distance, 90).longitude

    if quadrant == 3:
        lat_min = burstvincentydistance(origin, max_distance, 180).latitude
        lat_max = origin[0]
        lon_min = burstvincentydistance(origin, max_distance, 270).longitude
        lon_max = origin[1]
    if quadrant == 4:
        lat_min = origin[0]
        lat_max = burstvincentydistance(origin, max_distance, 0).latitude
        lon_min = burstvincentydistance(origin, max_distance, 270).longitude
        lon_max = origin[1]

    return (lat_min, lat_max, lon_min, lon_max)