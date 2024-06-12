"""
Module to compute PCL minimum detectable rcs for a given bistatic pair (rx,tx) and target positions. 
"""

import math
import logging
import numpy as np

from openburst.functions import geofunctions

TAKE_EASIER_VERT_INTERPOL_ATTEN = True

def query_bistatic_pairwise_los(tgt_z, los_height_tx, los_height_rx, Rx, Tx, tgt_x, tgt_y):
    """
    returns true/false for tg-tgt and rx-tgt LoS 
    
    != -999 needed to check if target Route - only array with '1' or '-1' as LOS

    """ 
    return (
        (tgt_z >= los_height_tx)
        and (tgt_z >= los_height_rx)
        and (los_height_rx != -999)
        and (los_height_tx != -999)
    )


def calculate_min_rcs_with_los(
    snr_thresh,
    use_grid,
    points_x,
    points_y,
    points_z,
    t_max,
    los_height_rx_grid,
    los_height_tx_grid,
    rx_in,
    tx_in,
    delay_thresh,
    static_rcs,
    radioprop_enabled,
    radioprop_params,
    input_splat_loss=0,
    splat_obj=None,
):

    """ 
    function calculates the minimal rcs detectable given the target position 
    if there is LOS between Tx-tgt and Rx-tgt and
    if the delay of the echo of the target is above the threshold
    and some other criteria.

    """

    Rx = rx_in  
    Tx = tx_in

    Tx = Tx.updatePolToHighest()
    # Converts the transmitter polarization 'M' (mixed) to 'V' or 'H', depending on which ERP is highest
    erp = Tx.returnERP()

    interpol_atten_in_advance = 1
    # defines whether attenuation values should be interpolated in advance or not
    nbr_interpol_angles_atten = 2 * 360
    # defines how many angles should be taken if attenuation values are to be interpolated in advance
    # # # # # nbr_interpol_angles_LOS=2*360; # defines how many angles should be taken for the max_LOS distance # Interpolation not done here anymore

    ## Setting & Calculating of some constants which are independent of target position
    atten_db_km = geofunctions.get_clear_sky_attenuation(Tx.freq)
    k = 1.38064852 * 1e-23 # Boltzmann constant in m^2 kg s^-2 K^-1
    g_proc = 10 * math.log10(t_max * Tx.bandwidth * 1000) # processing gain [dB] where BW in [kHz]
    c = 299792458.0 # speed of light

    # for the computation of snr_const: see the snr formula in P. Mousel master thesis ETH ZH, equations 2.15 to 2.17 on p.17
    # + 2.15 [dB] = 1.64 scalar from converting erp to EIRP.
    snr_const = (
        erp
        + 2.15
        + g_proc
        + Rx.gain
        - abs(Rx.losses)
        + 10
        * math.log10(
            (c / (Tx.freq * 1e6)) ** 2
            / ((4.0 * math.pi) ** 3 * k * Rx.temp_sys * Rx.bandwidth * 1000)
        )
    )
    # for usage with splat! propagation losses, we remove all the factors of free space loss for this snr_const
    snr_const_splat = (
        erp
        + 2.15
        + g_proc
        + Rx.gain
        - abs(Rx.losses)
        - 10 * math.log10(k * Rx.temp_sys * Rx.bandwidth * 1000)
    )

    if interpol_atten_in_advance == 1:
        new_interpol_angles = np.linspace(0, 2 * math.pi, nbr_interpol_angles_atten + 1)
        new_interpol_angles = np.delete(new_interpol_angles, -1)
        rx_horiz_diagr_att_interp, Rx.hor_att_angle_step = interpolate_attenuation(
            Rx.horiz_diagr_att, new_interpol_angles
        )
        tx_horiz_diagr_att_interp, Tx.hor_att_angle_step = interpolate_attenuation(
            Tx.horiz_diagr_att, new_interpol_angles
        )
    else:
        rx_horiz_diagr_att_interp = Rx.horiz_diagr_att
        tx_horiz_diagr_att_interp = Tx.horiz_diagr_att
        Rx.hor_att_angle_step = 1000
        Tx.hor_att_angle_step = 1000

    Tx = setup_vertical_attenuation(Tx, "Tx", tx_horiz_diagr_att_interp)

    Rx = setup_vertical_attenuation(Rx, "Rx", rx_horiz_diagr_att_interp)

    L = (
        geofunctions.get_2d_distance_between_locs_heights(
            Tx.lat, Tx.lon, Tx.masl + Tx.ahmagl, Rx.lat, Rx.lon, Rx.masl + Rx.ahmagl
        )
        * 1000
    )

    dist_delay_limit = delay_thresh * c / 1e6 + L # dist_delay_limit [m], delay_thresh [us], L in [m]

    ## Now loop over target positions
    # points_x and points_y have the same shape 
    # (both 2D array, points_x containing lon values, points_y containing lat values)
    try:
        len_x = points_x.shape[0]
        len_y = points_x.shape[1]
        len_z = len(points_z)
    except LookupError:
        pass

    if (
        use_grid == 1
    ):  # defines the points_x and points_y to be grid points: will thus loop over all points_y for each of the points_x

        rcs_heatmap = -1 * np.ones((len_y, len_x, len_z))
        snr_heatmap = np.zeros((len_y, len_x, len_z))

        for loop_ind_x in range(len_x):

            for loop_ind_y in range(len_y):
                tgt_x = points_x[loop_ind_x, loop_ind_y]
                # lon
                tgt_y = points_y[loop_ind_x, loop_ind_y]
                # lat

                for loop_ind_z in range(len_z):
                    tgt_z = points_z[loop_ind_z]

                    try:
                        tx_height = Tx.masl + Tx.ahmagl
                        rx_height = Rx.masl + Rx.ahmagl

                        nothing_underground = 1  # this will be set to zero if terrain at Tx or Rx od Tgt is under ground
                        if radioprop_enabled == 1:

                            if not np.isscalar(tgt_z):
                                tgt_z = tgt_z[0]
                            tx_tgt_loss_ret = splat_obj.getRawLosAndLoss(
                                Tx.lat,
                                Tx.lon,
                                tx_height,
                                tgt_y,
                                tgt_x,
                                tgt_z,
                                Tx.freq,
                                1,
                                0,
                                0,
                            )
                            tgt_rx_loss_ret = splat_obj.getRawLosAndLoss(
                                tgt_y,
                                tgt_x,
                                tgt_z,
                                Rx.lat,
                                Rx.lon,
                                rx_height,
                                Tx.freq,
                                1,
                                0,
                                0,
                            )

                            tx_tgt_prop_loss = tx_tgt_loss_ret[1]
                            tgt_rx_prop_loss = tgt_rx_loss_ret[1]
                            #tx_tgt_free_loss = tx_tgt_loss_ret[2]
                            #tgt_rx_free_loss = tgt_rx_loss_ret[2]
                            tx_tgt_los_ok = tx_tgt_loss_ret[0]
                            tx_tgt_fresnel_free = tx_tgt_loss_ret[7]
                            tgt_rx_los_ok = tgt_rx_loss_ret[0]
                            tgt_rx_fresnel_free = tgt_rx_loss_ret[7]

                            tx_tgt_loss = 0  # this will be set below
                            tgt_rx_loss = 0  # this will be set below

                            if math.isnan(tx_tgt_prop_loss):
                                if (tx_tgt_los_ok == 1) and (tx_tgt_fresnel_free == 1):
                                    tx_tgt_loss = tx_tgt_loss_ret[2]  # free space loss
                                else:
                                    tx_tgt_loss = (
                                        100000  # we set a very high loss value
                                    )
                            else:
                                tx_tgt_loss = tx_tgt_loss_ret[1]  # prop loss

                            if math.isnan(tgt_rx_prop_loss):
                                if (tgt_rx_los_ok == 1) and (tgt_rx_fresnel_free == 1):
                                    tgt_rx_loss = tgt_rx_loss_ret[2]  # free space loss
                                else:
                                    tgt_rx_loss = (
                                        100000  # we set a very high loss value
                                    )
                            else:
                                tgt_rx_loss = tgt_rx_loss_ret[1]  # prop loss

                            total_splat_loss = tx_tgt_loss + tgt_rx_loss

                            nothing_underground = 1

                        else:
                            total_splat_loss = 0

                        if nothing_underground == 1:
                            if radioprop_enabled == 0:
                                rcs, snr = calculate_min_rcs_los_single_pos(
                                    tgt_x,
                                    tgt_y,
                                    tgt_z,
                                    los_height_rx_grid[loop_ind_x][loop_ind_y],
                                    los_height_tx_grid[loop_ind_x][loop_ind_y],
                                    Rx,
                                    Tx,
                                    tx_horiz_diagr_att_interp,
                                    rx_horiz_diagr_att_interp,
                                    interpol_atten_in_advance,
                                    snr_const,
                                    snr_thresh,
                                    atten_db_km,
                                    dist_delay_limit,
                                    static_rcs,
                                    radioprop_enabled,
                                    total_splat_loss,
                                )
                            else:
                                rcs, snr = calculate_min_rcs_without_los_single_pos(
                                    tgt_x,
                                    tgt_y,
                                    tgt_z,
                                    Rx,
                                    Tx,
                                    tx_horiz_diagr_att_interp,
                                    rx_horiz_diagr_att_interp,
                                    interpol_atten_in_advance,
                                    snr_const_splat,
                                    snr_thresh,
                                    atten_db_km,
                                    dist_delay_limit,
                                    static_rcs,
                                    total_splat_loss,
                                )
                        else:
                            rcs = -1
                            snr = -1

                        rcs_heatmap[loop_ind_x][loop_ind_y][loop_ind_z] = rcs
                        snr_heatmap[loop_ind_x][loop_ind_y][loop_ind_z] = snr

                    except LookupError as exc:
                        
                        logging.getLogger("PCL").error(
                            "index error, loop_ind_x = %d, loop_ind_y =  %d, len1 = %d, len2 = %d",
                            loop_ind_x,
                            loop_ind_y,
                            len(los_height_rx_grid),
                            len(los_height_rx_grid[0]),
                        )
                        logging.getLogger("PCL").error(exc)

    else:

        rcs_heatmap = -1 * np.ones((len_y, len_x, len_z))
        snr_heatmap = np.zeros(len_x)
        for loop_ind in range(len_x):
            tgt_x = points_x[loop_ind]
            tgt_y = points_y[loop_ind]
            tgt_z = points_z[loop_ind]

            rcs, snr = calculate_min_rcs_los_single_pos(
                tgt_x,
                tgt_y,
                tgt_z,
                los_height_rx_grid[loop_ind],
                los_height_tx_grid[loop_ind],
                Rx,
                Tx,
                tx_horiz_diagr_att_interp,
                rx_horiz_diagr_att_interp,
                interpol_atten_in_advance,
                snr_const,
                snr_thresh,
                atten_db_km,
                dist_delay_limit,
                static_rcs,
                0,
                0
            )
            rcs_heatmap[loop_ind] = rcs
            snr_heatmap[loop_ind] = snr

    return rcs_heatmap, snr_heatmap


def calculate_min_rcs_los_single_pos(
    tgt_x,
    tgt_y,
    tgt_z,
    los_height_rx,
    los_height_tx,
    Rx,
    Tx,
    tx_horiz_diagr_att_interp,
    rx_horiz_diagr_att_interp,
    interpol_atten_in_advance,
    snr_const,
    snr_thresh,
    atten_db_km,
    dist_delay_limit,
    static_rcs,
    radioprop_enabled,
    total_splat_loss,
):
    """ 
    Calculates rcs for one single target position, is called by calculate_min_rcs_with_los
    """
    r_r = (
        geofunctions.get_2d_distance_between_locs_heights(
            Rx.lat, Rx.lon, Rx.masl + Rx.ahmagl, tgt_y, tgt_x, tgt_z
        )
        * 1000.0
    )  # distance in meters

    theta_r_bearing = geofunctions.get_azimuth_between_locs(Rx.lat, Rx.lon, tgt_y, tgt_x)
    theta_r_vert = geofunctions.get_elev_angle(tgt_z, Rx.masl + Rx.ahmagl, r_r)

    r_t = (
        geofunctions.get_2d_distance_between_locs_heights(
            Tx.lat, Tx.lon, Tx.masl + Tx.ahmagl, tgt_y, tgt_x, tgt_z
        )
        * 1000.0
    )  # distance in meters

    theta_t_bearing = geofunctions.get_azimuth_between_locs(Tx.lat, Tx.lon, tgt_y, tgt_x)
    theta_t_vert = geofunctions.get_elev_angle(tgt_z, Tx.masl + Tx.ahmagl, r_t)

    if r_r + r_t < dist_delay_limit:  # checks if delay threshold is valid
        rcs = -1
        snr = -1
    else:
        tx_horiz_att = find_attenuation_for_angle(
            theta_t_bearing,
            tx_horiz_diagr_att_interp,
            Tx.hor_att_angle_step,
            interpol_atten_in_advance + 1,
        )

        rx_horiz_att = find_attenuation_for_angle(
            theta_r_bearing,
            rx_horiz_diagr_att_interp,
            Rx.hor_att_angle_step,
            interpol_atten_in_advance + 1,
        )

        if TAKE_EASIER_VERT_INTERPOL_ATTEN:
            tx_vert_att = get_vertical_attenuation_easy_interpol(
                theta_t_vert, Tx.has_vert_diagr_att, Tx.vert_diagr_att, Tx.vert_angles
            )
            rx_vert_att = get_vertical_attenuation_easy_interpol(
                theta_r_vert, Rx.has_vert_diagr_att, Rx.vert_diagr_att, Rx.vert_angles
            )
        else:  # more complex interpolation method, where the orientation of the main beam in horizontal plane is checked, in order to calc. vertical attenuation

            rx_vert_att = get_vertical_attenuation(
                theta_r_bearing,
                theta_r_vert,
                Rx.has_vert_diagr_att,
                Rx.phi_h_max_bear,
                Rx.phi_v_max,
                Rx.vert_diagr_att,
                Rx.vert_angles,
            )

            tx_vert_att = get_vertical_attenuation(
                theta_t_bearing,
                theta_t_vert,
                Tx.has_vert_diagr_att,
                Tx.phi_h_max_bear,
                Tx.phi_v_max,
                Tx.vert_diagr_att,
                Tx.vert_angles,
            )

        # calculating the amount of snr which is above the threshold
        # the calculation of the snr is split into several parts to save computational time
        snr_extra = 0

        # we only consider (slightly) frequency dependent atmospheric attennuation 
        # (see computation of atten_db_km), the antenna diagramms and a freq independent free space loss
        # free space loss: 20*log10( r_t*r_r ): this was not included in snr_const
        # atmospheric attenuation (Barton approximation, see computation of atten_db_km): atten_db_km*( (r_t + r_r)/1000.0 )
        snr_extra = (
            snr_const
            - snr_thresh
            - atten_db_km * ((r_t + r_r) / 1000.0)
            - 1 * rx_horiz_att
            - 1 * tx_horiz_att
            - 1 * tx_vert_att
            - 1 * rx_vert_att
            - 20 * math.log10(r_t * r_r)
        )  # "20 * log10( r_t*r_r ) " is the same as "10 * log10(r_t*r_t * r_r*r_r)

        rcs = 10.0 ** (-snr_extra / 10.0)
        # see equation 2.20 in P. Mousel master thesis ETH 2017 p.18
        if rcs == 0.0:  # avoid rcs being 0 and math domain error in log further down
            rcs = 0.000001

        if static_rcs > 0.0:
            snr = snr_thresh + 10 * math.log10(static_rcs) - 10 * math.log10(rcs)
            # static_rcs is used just for snr computation with a static minimal rcs. we set static_rcs to 0 not to use this
        else:
            snr = snr_thresh - 10 * math.log10(rcs)
            # this is used usually with static_rcs set to 0

        if rcs > 150:  # we set the max to 150m2
            rcs = 150
    #print("snr = ", snr)
    return rcs, snr


def calculate_min_rcs_without_los_single_pos(
    tgt_x,
    tgt_y,
    tgt_z,
    Rx,
    Tx,
    tx_horiz_diagr_att_interp,
    rx_horiz_diagr_att_interp,
    interpol_atten_in_advance,
    snr_const_splat,
    snr_thresh,
    atten_db_km,
    dist_delay_limit,
    static_rcs,
    total_splat_loss,
):
    """ 
    Calculates min_rcs and snr for one single target position,
    """ 
    r_r = (
        geofunctions.get_2d_distance_between_locs_heights(
            Rx.lat, Rx.lon, Rx.masl + Rx.ahmagl, tgt_y, tgt_x, tgt_z
        )
        * 1000.0
    )  # distance in meters

    theta_r_bearing = geofunctions.get_azimuth_between_locs(Rx.lat, Rx.lon, tgt_y, tgt_x)
    theta_r_vert = geofunctions.get_elev_angle(tgt_z, Rx.masl + Rx.ahmagl, r_r)

    r_t = (
        geofunctions.get_2d_distance_between_locs_heights(
            Tx.lat, Tx.lon, Tx.masl + Tx.ahmagl, tgt_y, tgt_x, tgt_z
        )
        * 1000.0
    )  # distance in meters

    theta_t_bearing = geofunctions.get_azimuth_between_locs(Tx.lat, Tx.lon, tgt_y, tgt_x)
    theta_t_vert = geofunctions.get_elev_angle(tgt_z, Tx.masl + Tx.ahmagl, r_t)

    if r_r + r_t < dist_delay_limit:  # checks if delay threshold is valid
        rcs = -1
        snr = -1
    else:

        tx_horiz_att = find_attenuation_for_angle(
            theta_t_bearing,
            tx_horiz_diagr_att_interp,
            Tx.hor_att_angle_step,
            interpol_atten_in_advance + 1,
        )

        rx_horiz_att = find_attenuation_for_angle(
            theta_r_bearing,
            rx_horiz_diagr_att_interp,
            Rx.hor_att_angle_step,
            interpol_atten_in_advance + 1,
        )

        if TAKE_EASIER_VERT_INTERPOL_ATTEN:
            tx_vert_att = get_vertical_attenuation_easy_interpol(
                theta_t_vert, Tx.has_vert_diagr_att, Tx.vert_diagr_att, Tx.vert_angles
            )
            rx_vert_att = get_vertical_attenuation_easy_interpol(
                theta_r_vert, Rx.has_vert_diagr_att, Rx.vert_diagr_att, Rx.vert_angles
            )
        else:  # More complex interpolation method, where the orientation of the main beam in horizontal plane is checked, in order to calc. vertical attenuation

            rx_vert_att = get_vertical_attenuation(
                theta_r_bearing,
                theta_r_vert,
                Rx.has_vert_diagr_att,
                Rx.phi_h_max_bear,
                Rx.phi_v_max,
                Rx.vert_diagr_att,
                Rx.vert_angles,
            )

            tx_vert_att = get_vertical_attenuation(
                theta_t_bearing,
                theta_t_vert,
                Tx.has_vert_diagr_att,
                Tx.phi_h_max_bear,
                Tx.phi_v_max,
                Tx.vert_diagr_att,
                Tx.vert_angles,
            )

        # calculating the amount of snr which is above the threshold
        # the calculation of the snr is split into several parts to save computational time

        # propagation loss (includes besides propagation loss over terrain also freq dependent atmospheric attenutation) and a freq dependent free space loss computation by SPLAT are considered
        snr_extra = (
            snr_const_splat
            - snr_thresh
            - 1 * rx_horiz_att
            - 1 * tx_horiz_att
            - 1 * tx_vert_att
            - 1 * rx_vert_att
            - total_splat_loss
        )

        #print("#################")
        #print("snr_extra = ", snr_extra, ", + : ", snr_const_splat, ", - :" , snr_thresh, rx_horiz_att, tx_horiz_att, tx_vert_att, rx_vert_att, total_splat_loss)

        rcs = 10.0 ** (-snr_extra / 10.0)
        # see equation 2.20 in P. Mousel master thesis p.18
        if rcs == 0.0:  # avoid rcs being 0 and math domain error in log further down
            rcs = 0.000001
        #print("snr_extra, rcs: ", snr_extra, rcs)    

        if static_rcs > 0.0:
            snr = snr_thresh + 10 * math.log10(static_rcs) - 10 * math.log10(rcs)
            # static_rcs is used just for snr computation with a static minimal rcs. we set static_rcs to 0 not to use this
        else:
            snr = snr_thresh - 10 * math.log10(rcs)

        if rcs > 150:  # we set the max to 150m2
            rcs = 150
    
    return rcs, snr





def vertic_att_half_wave_dipole(theta):
    """
    This function calculates the vertical attenuation of a half-wave dipole antenna
    theta being elevation angle in rad (0rad == horizontal plane)
    """

    if abs(abs(theta) - math.pi / 2) < 1e-5:
        #    rad_power_factor = 0;
        attenuation_factor_db = 100
    else:
        rad_power_factor = (
            abs(math.cos(math.pi / 2 * math.cos(math.pi / 2 + theta)) / math.sin(math.pi / 2 + theta)) ** 2
        )
        attenuation_factor_db = -10.0 * math.log10(rad_power_factor)

    return attenuation_factor_db


def get_vertical_attenuation(
    theta_bearing,
    theta_vert,
    has_vert_diagr_att,
    phi_h_max_bear,
    phi_v_max,
    vert_diagr_att,
    vert_angles,
):
    """ 
    Computes vertical attenuation as minimal depending on direction of main lobe.
    for different azimuths the vertical attenuation will be different.
    """
    if has_vert_diagr_att == 1:  # if has an array as vertical attenuation diagram

        bearing_difference = abs(theta_bearing - phi_h_max_bear)
        if (
            bearing_difference > math.pi
        ):  # if difference between two bearing angles is to be taken,  for example between 350deg and 20deg, then difference is 30 and not 330!
            bearing_difference = 2 * math.pi - bearing_difference

        phi_v = theta_vert + bearing_difference / (math.pi / 2) * phi_v_max
        if phi_v > math.pi / 2 or phi_v < -math.pi / 2:
            logging.getLogger("PCL").error(
                "phi_v bad range!!!  theta_vert = %s, bearing_diff=%s, phi_v became %s",
                theta_vert * 180 / math.pi,
                bearing_difference * 180 / math.pi,
                phi_v * 180 / math.pi,
            )
        # ======================================================================= # testing if vert atten good
        # if theta_bearing < 20*pi/180 or theta_bearing > 340*pi/180:
        #     print "from theta_vert = %s, theta_bearing=%s, phi_v became %s" %(theta_vert*180/pi, theta_bearing*180/pi, phi_v*180/pi )
        # =======================================================================
        tmp_ind = np.argmin(abs(vert_angles - phi_v))
        vertical_att_out = vert_diagr_att[tmp_ind]

    elif (
        has_vert_diagr_att == 2
    ):  # if there is only one value given by the vertical attenuation diagram
        vertical_att_out = vert_diagr_att
    else:  # no entry given at all
        # assume the vertical attenuation to be that of a half-wave dipole
        vertical_att_out = vertic_att_half_wave_dipole(theta_vert)

    return vertical_att_out


def get_vertical_attenuation_easy_interpol(
    theta_vert, has_vert_diagr_att, vert_diagr_att, vert_angles
):
    """ 
    computes vertical attentuation (simple variant):
    vertical attenuation is considered the same for all azimuthal directions
    """
    if has_vert_diagr_att == 1:  # if has an array as vertical attenuation diagram
        tmp_ind = np.argmin(abs(vert_angles - theta_vert))
        vertical_att_out = vert_diagr_att[tmp_ind]

    elif (
        has_vert_diagr_att == 2
    ):  # if there is only one value given by the vertical attenuation diagram
        vertical_att_out = vert_diagr_att
    else:
        vertical_att_out = vertic_att_half_wave_dipole(theta_vert)
    return vertical_att_out


def setup_vertical_attenuation(tx_or_rx, _, tx_or_rx_horiz_diagr_att_interp):
    """ 
    Function to configure vertical attenuation.
    elevation angle defined such that 0rad denotes the horizontal plane, 
    pi/2 rad points upwards and -pi/2 rad points downwards
    has to be called after interpolation of horiz_diagr (needs np.array)
    """

    if isinstance(tx_or_rx.vert_diagr_att, str):
        # print "%s.vert_diagr_att is a string" %tx_or_rx_string
        tx_or_rx.phi_v_max = "UNDEFINED"
        tx_or_rx.vert_angles = "UNDEFINED"
        tx_or_rx.phi_h_max_bear = "UNDEFINED"
        tx_or_rx.has_vert_diagr_att = 0
    elif isinstance(tx_or_rx.vert_diagr_att, (int, float)):
        tx_or_rx.phi_v_max, tx_or_rx.vert_angles, tx_or_rx.phi_h_max_bear = 0, 0, 0
        tx_or_rx.has_vert_diagr_att = 2
    else:  # array

        tx_or_rx.vert_diagr_att = np.asarray(tx_or_rx.vert_diagr_att)
        # finding vertical angle (elevation angle) where maximal radiation pattern
        vert_angles = np.linspace(-math.pi / 2, math.pi / 2, len(tx_or_rx.vert_diagr_att))
        inds = np.where(tx_or_rx.vert_diagr_att == min(tx_or_rx.vert_diagr_att))[0]
        # If several maxima of radiation pattern/minima of attenuation diagram: taking the angle closest being radiated towards the horizontal plane
        ind_tmp = np.where(
            abs((len(tx_or_rx.vert_diagr_att) - 1) / 2.0 - inds)
            == min(abs((len(tx_or_rx.vert_diagr_att) - 1) / 2.0 - inds))
        )[0]
        if ind_tmp.size > 1:
            phi_v_max = (
                vert_angles[inds[ind_tmp[0]]] + vert_angles[inds[ind_tmp[1]]]
            ) / 2.0
        elif ind_tmp.size > 2:
            logging.getLogger("PCL").error("ERROR: ind_tmp.size > 2")
        else:
            ind_tmp = np.argmin(abs((len(tx_or_rx.vert_diagr_att) - 1) / 2.0 - inds))
            ind = inds[ind_tmp]
            phi_v_max = vert_angles[ind]

        # finding bearing where maximal horizontal radiation pattern/minimum of att. diagr: taking the one of the main lobe
        phi_h_max_bear = get_mainlobe_heading(tx_or_rx_horiz_diagr_att_interp)

        # saving data to struct
        tx_or_rx.phi_v_max, tx_or_rx.vert_angles, tx_or_rx.phi_h_max_bear = (
            phi_v_max,
            vert_angles,
            phi_h_max_bear,
        )
        tx_or_rx.has_vert_diagr_att = 1

    return tx_or_rx


def get_mainlobe_heading(horiz_diagr):
    """
    computes the heading of mainlobe.
    """
    horiz_diagr = np.asarray(horiz_diagr)
    if len(horiz_diagr) > 1:
        hor_angles = np.linspace(math.pi / 2, -3.0 * math.pi / 2, len(horiz_diagr) - 1 + 1)
        hor_angles = np.delete(hor_angles, -1)
        # -1 because horiz_diagr_att_interp has been closed in interpolate_attenuation
        inds = np.where(horiz_diagr == min(horiz_diagr))[0]

        if len(inds) > 1:
            difference = np.diff(inds)
            start = 0
            j = 0
            counter = [0]
            point = [0]
            for i in range(len(inds) - 1):
                stop = i
                point[j] = (stop + start) / 2
                if difference[i] == 1:
                    counter[j] += 1
                else:
                    counter.append(0)
                    point.append(0)
                    j = j + 1
                    start = i + 1
            stop += 1
            point[-1] = (stop + start) / 2

            ind_hor = inds[int(point[np.argmax(counter)])]
        else:
            ind_hor = inds[0]

        #"Previous Alternative"
        # ind_hor = int(round(np.mean(inds)));  # bad if two main lobes
        #"very simply alternative..."
        # ind_hor = inds[0]

        phi_h_max_bear = math.pi / 2 - hor_angles[ind_hor]

    else:  # horiz. attenuation is a single value
        phi_h_max_bear = 0

    return phi_h_max_bear

    # IMPORTANT THAT THE ATTEN_DIAGR_INTERP HAS LENGTH+1 to close the circle and to facilitate round operations


def interpolate_attenuation(atten_diagr, new_interpol_angles):
    """ 
    This function will interpolate the attenuation diagram by a set of new interpolation angles.
    Computationally efficient as interpolation all the angles in advance is carried out, 
    instead of interpolating for every target position.
    
    """

    if isinstance(atten_diagr, (int, float)):  # length == 1
        atten_diagr_interp = np.asarray([atten_diagr])
        angle_step = 1000
    elif isinstance(atten_diagr, str):
        atten_diagr_interp = np.asarray([0])
        angle_step = 1000

    else:
        angle_step = 2 * math.pi / new_interpol_angles.size

        angles_clock = np.linspace(0, 2 * math.pi, len(atten_diagr) + 1)
        # in northing frame
        atten_diagr = np.append(atten_diagr, atten_diagr[0])
        # close the circle, such that interpolation for angle close to 2pi can be done

        # This one interpolates the attenuation value respective of the wanted angle
        atten_diagr_interp = np.interp(new_interpol_angles, angles_clock, atten_diagr)
        atten_diagr_interp = np.append(atten_diagr_interp, atten_diagr[0])
        # close the circle
    return atten_diagr_interp, angle_step


def find_attenuation_for_angle(
    angle_bearing, atten_diagr_interp, angle_step, _
):
    """
    Finds the attenuation of a Tx or a Rx represented by its attenuation diagram for a
    specific angle. The angle_bearing is such that 0rad represents north whereas the first entry 
    of the atten_diagr represents 0rad north, or pi/2.
    - angle_bearing [rad]
    - if interpol_atten==1, will interpolate the attenuation matrix to the correct value
    
    todo: interpol_atten_in_advance ignored
    """

    atten_db_out = atten_diagr_interp[int(round(angle_bearing / angle_step))]

    # Alternative:
    # [~,tmp_ind] = min(abs(angles_clock-angle_north_fr));
    # atten_dB_out = atten_diagr(tmp_ind);

    return atten_db_out
