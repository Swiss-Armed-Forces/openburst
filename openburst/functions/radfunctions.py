"""
Active monostatic radar probability of detection (pd) computation from SNR.
Python implementation of the thesis Matlab code from: 
"A MATLAB Radar Range Equation and Probability of Detection Evaluation Tool"
Barry Scheiner
Army Research Laboratory
1999
https://apps.dtic.mil/sti/pdfs/ADA360040.pdf
"""

import math
from scipy import special
from scipy import integrate
import numpy as np
import scipy.constants as sc


alpha = None

def marcum_q_fn(v):
    """ integrand function to evaluate the Marcum Q
        function that provides the probability of detection for
        a single pulse out of a quadrature detector.
    """
    return v * math.exp(-(v * v + alpha * alpha) / 2) * special.iv(0, alpha * v)


def radar_eq_pd(
    trans_pwr,
    antenna_diam,
    frequency,
    pulse_width,
    cpi_pulses,
    bandwidth,
    pfa,
    rcs_sm,
    tgt_rad_dist,
    one_way_pure_prop_loss_db=0,
):
    """! returns pd given the radar parameters and the target rcs and the distance [m] between radar and target.
    if one_way_pure_prop_loss_db is given: we do not compute prop loss in both directions (Rad->Tgt and Tgt->Rad, instead we assume the prop loss is the same in both directions)
    
    """

    ####################### Radar and target values ##################

    c = sc.speed_of_light
    # speed of light
    rf_loss = 12
    # RF system hardware loss (not known for ASR, best guess from chapter 2.12, p.80 Skolnik "Introduction to radar systems")

    rcs_start = 10 * np.log10(rcs_sm)
    # rcs_start=13;                        # RCS in db
    noise_figure = 1.9
    # Receiver LNA noise figure in dB  (not known for specific radars, best guess)
    window = 0
    # rectangular for no window, or Hamming (=0)
    equiv_temp = 300
    # equivalent temperature [K] (not known for ASR, best guess) = Skolnik Ambient temperature  T_0 (usually 290K)

    ########################################################################################

    ############# ------------- analyze for upto 400 kms
    #start_range = 0
    # [m]
    # Attention!!!!!! if the snr is very high (that is for low ranges) the besseli function will overflow
    # throwing a segmentation fault (another way to avoid it is to return Pd=1 for snr > e.g. 30dB)
    # this can be avoided by setting the start_range to be a higher value
    #stop_range = 400000
    # [m]

    # -----------------------evaluate radar range equation -----------------------------------

    A = np.pi * antenna_diam * antenna_diam / 4
    wavelength = c / (frequency * 1.0e9)
    antenna_gain = 10 * np.log10(0.6 * 4 * np.pi * A / (wavelength * wavelength))

    four_pi = 10 * np.log10(pow((4 * np.pi), 3))
    pt = 10 * np.log10(trans_pwr)
    lambda_sq = 2 * 10 * np.log10(c / (frequency * 1.0e9))
    ktb = 10 * np.log10(1.38e-23 * equiv_temp * (bandwidth * 1e6))
    t_bw_gain = 10 * np.log10(pulse_width * bandwidth)
    dop_gain = 10 * np.log10(cpi_pulses)
    # rad_range = linspace(start_range, stop_range, 100);
    rad_range = tgt_rad_dist
    snr = (
        pt
        + lambda_sq
        + 2 * antenna_gain
        + t_bw_gain
        + dop_gain
        + rcs_start
        - four_pi
        - ktb
        - 40 * np.log10(rad_range)
        - noise_figure
        - rf_loss
        - 2 * one_way_pure_prop_loss_db
    )

    # ------------------------------evaluate  range resolution ---------------

    res = c / (2 * (bandwidth * 1e6))
    if window == 0:
        res = res * 1.44
        # -----------------------------evaluate Pd function -----------------------

        beta = math.sqrt(-2 * (np.log(pfa)))

        #### avoid segmentation fault in the besseli function for high snr values
        if snr > 30:
            pd = 1.0
        else:
            global alpha
            alpha = pow(10, ((snr + 3) / 20))
            pd = 1 - integrate.quad(marcum_q_fn, 0, beta)[0]
        return pd


def get_rad_pd(
    power,
    antenna_diam,
    freq,
    pulse_width,
    cpi_pulses,
    bandwidth,
    pfa,
    rcs,
    dist,
    max_distance,
    rad_lat,
    rad_lon,
    rad_height,
    tgt_lat,
    tgt_lon,
    tgt_height,
    splat_obj,
):
    """computes pd from given radar parameters"""
    rad_boundaries_ok = splat_obj.testBoundaries(rad_lat, rad_lon)
    tgt_boundaries_ok = splat_obj.testBoundaries(tgt_lat, tgt_lon)

    if (rad_boundaries_ok == 0) or (tgt_boundaries_ok == 0):
        return 0.0

    ret = splat_obj.getRawLosAndLoss(
        rad_lat, rad_lon, rad_height, tgt_lat, tgt_lon, tgt_height, freq, 1, 0, 0
    )  # last three params: int asl, int justlos, int reverseDirection=0

    # LOS, PROP_LOSS, FREE_SPACE_LOSS,  dist[m], source_elev[masl], dest_elev[masl], p_to_pdist[m], first_fresnel_zone_free
    los_ok = ret[0]
    prop_loss = ret[1]
    free_space_loss = ret[2]
    fresnel_free = ret[7]
    got_pd = radar_detection_given_with_splat(
        0,
        power,
        antenna_diam,
        freq,
        pulse_width,
        cpi_pulses,
        bandwidth,
        pfa,
        rcs,
        dist,
        max_distance,
        los_ok,
        prop_loss,
        free_space_loss,
        fresnel_free,
    )

    return got_pd



def radar_detection_given_with_splat(
    justlos,
    trans_pwr,
    antenna_diam,
    frequency,
    pulse_width,
    cpi_pulses,
    bandwidth,
    pfa,
    rcs_sm,
    tgt_rad_dist,
    max_distance,
    los_ok,
    prop_loss,
    free_space_loss,
    fresnel_free,
):
    """
    returns pd given the radar parameters and the target rcs and the distance [m] between radar and target.
    if one_way_pure_prop_loss_db is given: we do not compute prop loss in both directions 
    (Rad->Tgt and Tgt->Rad, instead we assume the prop loss is the same in both directions)

    This uses the results from splat computation to determine the radar detection: 
    used for LIVE detection and by coverage computation with prop model.
    justlos should be always 0, then we always want to consider splat! for propagation losses

    """

    ####################### Radar and target values (working) ##################
    c = sc.speed_of_light
    # speed of light
    rcs_start = 10 * np.log10(rcs_sm)
    # rcs_start=13;                        # RCS in db
    window = 0
    # rectangular for no window, or Hamming (=0)

    rf_loss = 12
    # RF system hardware loss (not known for ASR, best guess from chapter 2.12, p.80 Skolnik "Introduction to radar systems")

    noise_figure = 1.9
    # Receiver LNA noise figure in dB  (not known for specific radars, best guess)
    window = 0
    # rectangular for no window, or Hamming (=0)
    equiv_temp = 300

    four_pi = 10 * np.log10(pow((4 * np.pi), 3))
    pt = 10 * np.log10(trans_pwr)
    lambda_sq = 2 * 10 * np.log10(c / (frequency * 1.0e9))
    ktb = 10 * np.log10(1.38e-23 * equiv_temp * (bandwidth * 1e6))

    ########################################################################################

    ############# ------------- analyze for upto 400 kms
    #start_range = 0
    # [m]
    # Attention!!!!!! if the snr is very high (that is for low ranges) the besseli function will overflow
    # throwing a segmentation fault (another way to avoid it is to return Pd=1 for snr > e.g. 30dB)
    # this can be avoided by setting the start_range to be a higher value
    #stop_range = 400000
    # [m]

    # -----------------------evaluate radar range equation -----------------------------------

    A = np.pi * antenna_diam * antenna_diam / 4
    wavelength = c / (frequency * 1.0e9)
    antenna_gain = 10 * np.log10(0.6 * 4 * np.pi * A / (wavelength * wavelength))

    pt = 10 * np.log10(trans_pwr)
    lambda_sq = 2 * 10 * np.log10(c / (frequency * 1.0e9))

    t_bw_gain = 10 * np.log10(pulse_width * bandwidth)
    dop_gain = 10 * np.log10(cpi_pulses)
    rng = tgt_rad_dist

    # in radterrain module for computation of max_dist the SNR is computed as following 
    # (i.e. without prop losses)
    # curr_snr = pt + lambda_sq + 2*antenna_gain + t_bw_gain + dop_gain + rcs_start - four_pi - ktb - 40 * np.log10(rng) - noise_figure - rf_loss;
    # we will here use the same formula but without the terms for free space loss
    if math.isnan(prop_loss):
        if (los_ok == 1) and (
            fresnel_free == 1
        ):  # here we use the free space model as always
            snr = (
                pt
                + lambda_sq
                + 2 * antenna_gain
                + t_bw_gain
                + dop_gain
                + rcs_start
                - four_pi
                - ktb
                - 40 * np.log10(rng)
                - noise_figure
                - rf_loss
            )
        else:
            return 0.0
    else:
        snr_old = (
            pt
            + lambda_sq
            + 2 * antenna_gain
            + t_bw_gain
            + dop_gain
            + rcs_start
            - four_pi
            - ktb
            - 40 * np.log10(rng)
            - noise_figure
            - rf_loss
        )
        snr = snr_old - 2 * (
            prop_loss - free_space_loss
        )  # we simply remove the extra loss found by the propagation mode

    # ------------------------------evaluate  range resolution ---------------

    res = c / (2 * (bandwidth * 1e6))
    if window == 0:
        res = res * 1.44
        # -----------------------------evaluate Pd function -----------------------

        beta = math.sqrt(-2 * (np.log(pfa)))

        # avoid segmentation fault in the besseli function for high snr values
        if snr > 30:
            pd = 1.0
        else:
            global alpha
            alpha = pow(10, ((snr + 3) / 20))
            # this is declared global above
            pd = 1 - integrate.quad(marcum_q_fn, 0, beta)[0]
        return pd



def dbm2si(dbm_val):
    """returns si from dBm"""
    return 10 ** ((dbm_val - 30.0) / 10.0)


def pet_eq_max_dist(erp_dbm, threshold_dbm, freq):
    """ returns max distance in kms for detection using a pet sensor with sensitivity: 
        threshold_dbm for a given emitter at freq (MHz) with erp in erp_dbm. 
        see pet detection formula on picture on the PET folder
    """
    # Radar and target values 
    freq = freq * 1e9  # assuming: freq is given in GHz
    threshold_w = dbm2si(threshold_dbm)
    erp_w = dbm2si(erp_dbm)
    dist_meters = np.sqrt(erp_w / threshold_w) * (
        sc.speed_of_light / (freq * 4 * np.pi)
    )
    return dist_meters / 1000.0


def pet_get_max_dist_with_ant_diag(
    v_alpha,
    h_alpha,
    erp_dbm,
    threshold_dbm,
    freq,
    h_antenna_diagramm,
    v_antenna_diagramm,
    main_beam_azimuth,
    main_beam_elevation,
):
    """!  returns max distance in kms for detection using a pet sensor with sensitivity: 
    threshold_dbm for a given emitter at freq with erp in erp_dbm
    but also using the sensor_pos, h and v angles in direction of target_pos and antenna diagramms.
    antenna diagramms should be given for each angle (0 to 360 for H and V) 
    in units of dBi as antenna gains.
    for H 0 means north looking and then clockwise
    for V 0 means horizontal looking and then clockwise towards the sky 
    (i.e. 90 means looking straight up, 270 straight down ).
    erp_dbm is the max erp in the main beam.
    v_alpha and h_alpha: are vertical and horizontal degrees
    
    """

    # rotate the antenna diagramms with the given values for main_beam_azimuth, main_beam_elevation
    h_antenna_diagramm = np.roll(h_antenna_diagramm, main_beam_azimuth)
    v_antenna_diagramm = np.roll(v_antenna_diagramm, main_beam_elevation)

    # --------- H ---------------------------------
    # get the closest integer to h_alpha between 0..360
    h_alpha_ind = max(0, h_alpha)
    h_alpha_ind = min(359, h_alpha)
    h_alpha_ind = int(h_alpha_ind)
    power_h = (erp_dbm - 30.0) / np.max(
        h_antenna_diagramm
    )  # this is the power in main beam [Watt], which is the max power. we assume that the gain is max at angle=0 deg
    erp_curr_h_db = (
        power_h * h_antenna_diagramm[h_alpha_ind]
    )  # this is the ERP in dBW for the given H angle
    erp_curr_h_dbm = erp_curr_h_db + 30.0

    # --------- V ---------------------------------
    v_alpha_ind = max(0, v_alpha)
    v_alpha_ind = min(359, v_alpha)
    v_alpha_ind = int(v_alpha_ind)
    power_v = (erp_dbm - 30.0) / np.max(
        v_antenna_diagramm
    )  # this is the power in main beam [Watt], we assume that the gain is max at angle=0 deg
    erp_curr_v_db = (
        power_v * v_antenna_diagramm[v_alpha_ind]
    )  # this is the ERP in dBW for the given Verp_curr_v_dbm angle
    erp_curr_v_dbm = erp_curr_v_db + 30.0

    # we take the lower of the both
    erp_curr_dbm = min(erp_curr_h_dbm, erp_curr_v_dbm)

    return pet_eq_max_dist(erp_curr_dbm, threshold_dbm, freq) * 1000.0






def radar_eq_max_dist(
    trans_pwr, antenna_diam, frequency, pulse_width, cpi_pulses, bandwidth, pfa, rcsSM
):
    """! returns maximal distance given the radar parameters and the target rcs. 
    MAX RANGE IS SET TO 400kms, due to the HARD LIMIT in SPLAT! (see MAXPAFES in splatBurst.h)
    """

    ####################### Radar and target values (working) ##################

    c = sc.speed_of_light
    # speed of light
    rf_loss = 12
    # RF system hardware loss (not known for ASR, best guess from chapter 2.12, p.80 Skolnik)
    rcs_start = 10 * np.log10(rcsSM)
    # rcs_start=13;                        # RCS in db
    noise_figure = 1.9
    # Receiver LNA noise figure in dB  (not known for TA, best guess)
    window = 0
    # rectangular for no window, or Hamming (=0)
    equiv_temp = 300
    # equivalent temperature [K] (not known for ASR, best guess)

    ########################################################################################

    ############# ------------- analyze for upto 400 kms
    start_range = 0.001
    # [m] starting at 0 will cause a division by 0 error further down
    # Attention!!!!!! if the snr is very high (that is for low ranges) the besseli function will overflow
    # throwing a segmentation fault (another way to avoid it is to return Pd=1 for snr > e.g. 30dB)
    # this can be avoided by setting the start_range to be a higher value
    stop_range = 400000
    # [m]

    # ------------------------------evaluate  range resolution ---------------

    res = c / (2 * (bandwidth * 1e6))
    if window == 0:
        res = res * 1.44

    # we set resolution manually
    res = 1000 # [m]

    # -----------------------evaluate radar range equation -----------------------------------

    A = np.pi * antenna_diam * antenna_diam / 4
    wavelength = c / (frequency * 1e9)
    antenna_gain = 10 * np.log10(0.6 * 4 * np.pi * A / (wavelength * wavelength))

    four_pi = 10 * np.log10(pow((4 * np.pi), 3))
    pt = 10 * np.log10(trans_pwr)
    lambda_sq = 2 * 10 * np.log10(c / (frequency * 1e9))
    ktb = 10 * np.log10(1.38e-23 * equiv_temp * (bandwidth * 1e6))
    t_bw_gain = 10 * np.log10(pulse_width * bandwidth)
    dop_gain = 10 * np.log10(cpi_pulses)

    ranges = np.arange(start_range, stop_range + 1, res)
    snr = []
    for rng in ranges:
        curr_snr = (
            pt
            + lambda_sq
            + 2 * antenna_gain
            + t_bw_gain
            + dop_gain
            + rcs_start
            - four_pi
            - ktb
            - 40 * np.log10(rng)
            - noise_figure
            - rf_loss
        )
        snr = np.concatenate([snr, [curr_snr]])

    # -----------------------------evaluate Pd function -----------------------

    beta = math.sqrt(-2 * (np.log(pfa)))

    rangel = np.arange(start_range, stop_range + 1, res)

    #lrl = rangel.shape[0]

    jj = 0
    pd = []

    for rng in rangel:       
        # avoid segmentation fault in the besseli function for high snr values
        if snr[jj] > 30:
            pd = np.concatenate([pd, [1.0]])
        else:
            global alpha  # make alpha global to pass it to marcum_r_fn
            alpha = pow(10, (snr[jj] + 3) / 20)
            # this is declared global above
            curr_pd = 1 - integrate.quad(marcum_q_fn, 0, beta)[0]
            pd = np.concatenate([pd, [curr_pd]])

        jj = jj + 1

    # compute and return max range (attention: all max ranges above this will not be noted by the user)
    retval = 400000

    ii = 0
    for _ in pd:
        if pd[ii] <= 0.8:
            retval = (rangel[ii] + rangel[ii - 1]) / 2
            break
        ii = ii + 1

    # change from m to km
    retval = retval / 1000.0
    return retval


def radar_detection_given(
    power,
    antenna_diam,
    freq,
    pulse_width,
    cpi_pulses,
    bandwidth,
    pfa,
    rcs,
    one_way_pure_prop_loss,
    dist,
    max_distance,
):
    """!  this function will return True if detection is given for the given values else False"""
    return radar_eq_pd(
        power,
        antenna_diam,
        freq,
        pulse_width,
        cpi_pulses,
        bandwidth,
        pfa,
        rcs,
        dist * 1000,
        one_way_pure_prop_loss,
    )


def get_detection_latlon_matrix(
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
    radar_z,
    radar_z_offset,
    origin,
    max_elev_deg,
    theta_arr,
):
    """ 
    returns detection lat/lon when propagtion is enabled 
    should append to send message 0.0 or 1.0 at lat,lon: 
    snd_msg = np.append(snd_msg, [lat, lon, 0.0]) depending on coverage given or not
    """
    delta_h_km = (
        flight_height - (radar_z + radar_z_offset)
    ) / 1000.0  # assuming flight is above radar
    min_xydist_m = math.fabs(
        (flight_height - (radar_z + radar_z_offset))
        / math.tan(math.radians(max_elev_deg))
    )
    max_xydist_m = 1000.0 * math.sqrt(
        max_distance * max_distance - delta_h_km * delta_h_km
    )

    ind = mpi_los_arr.shape[0] - 1
    while ind > -1:
        clos = mpi_los_arr[ind]  # this will be zero if no LoS

        cdist = mpi_dist_arr[ind]  # [m]
        clat = dest_lat_arr[ind]
        clon = 360.0 - dest_lon_arr[ind]
        #ctheta = theta_arr[ind]

        if clos < 0.0:  # something is under ground
            ind = ind - 1
            snd_msg = np.append(snd_msg, [clat, clon, 0.0])
            continue

        if cdist > (delta_h_km * 1000.0):
            curr_xy_dist_km = math.sqrt(
                (cdist / 1000.0) * (cdist / 1000.0) - (delta_h_km * delta_h_km)
            )
        else:
            curr_xy_dist_km = 0.0

        if mpi_prop_loss_arr[ind] > mpi_free_loss_arr[ind]:
            one_way_pure_prop_loss = mpi_prop_loss_arr[ind] - mpi_free_loss_arr[ind]
        else:
            one_way_pure_prop_loss = 0  # prop loss is automatically greater than free space los if fresnel zone is not clear

        if one_way_pure_prop_loss < 0.0:
            one_way_pure_prop_loss = 0.0
        if (cdist >= 0.0) and (curr_xy_dist_km >= (min_xydist_m / 1000.0)):

            pd = radar_detection_given_with_splat(
                0,
                power,
                antenna_diam,
                freq,
                pulse_width,
                cpi_pulses,
                bandwidth,
                pfa,
                rcs,
                cdist,
                max_distance * 1000,
                clos,
                mpi_prop_loss_arr[ind],
                mpi_free_loss_arr[ind],
                1,
            )  # fresnel free not available here

            if pd >= 0.8:
                snd_msg = np.append(snd_msg, [clat, clon, 1.0])

            else:
                snd_msg = np.append(snd_msg, [clat, clon, 0.0])

        else:
            snd_msg = np.append(snd_msg, [clat, clon, 0.0])

        ind = ind - 1

    return snd_msg


