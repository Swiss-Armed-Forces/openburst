"""Module for online running of PCL sensors"""

import multiprocessing as mp
import logging
import time
import math
import numpy as np
import scipy.constants as sc
from openburst.constants import pclconstants
from openburst.functions import basefunctions
from openburst.types import tx as txclass
from openburst.types import target
from openburst.types import dbpersistentaccess
from openburst.pcl.minrcs import calculate_min_rcs_with_los, calculate_min_rcs_without_los_single_pos
from openburst.functions import geofunctions
from openburst.pcl.minrcs import interpolate_attenuation, setup_vertical_attenuation

# ------------------------------ runs PCL Sensor detections in a single process for each PCL sensor
class PCLRunnerClass(mp.Process):
    """Class for PCL Running online"""
    def __init__(self, rx, txs, pcl_start_time, splat_obj, rcs, use_prop, team):
        # must call this before anything else
        mp.Process.__init__(self)
        self.daemon = False
        self.alive = mp.Event()
        self.rx = basefunctions.get_pcl_rx_attributes(rx)
        self.pcl_start_time = pcl_start_time
        self.id_nr = None
        self.splat_obj = splat_obj
        self.target_rcs = rcs
        self.use_prop = use_prop
        self.txs = txs
        self.update_time = pclconstants.SENSOR_UPDATE_TIME  # 1Hz update rate for PCL
        self.team = team
        self.dbaccess = dbpersistentaccess.DbConnector(logging.getLogger(__name__), "PCL_DETECTION_RUNNER")

    def run(self):

        while not self.alive.is_set():
            time1 = basefunctions.get_time()
            targets = self.dbaccess.get_targets("blue")
            if targets is None:
                time.sleep(self.update_time)
                continue

            tx_count = 0
            for txx in self.txs:
                tx = txclass.Tx(
                    txx[0],
                    txx[1],
                    txx[2],
                    txx[4],
                    txx[5],
                    txx[7],
                    txx[8],
                    txx[10],
                    txx[13],
                    txx[11],
                    txx[12],
                    "directional",
                    txx[14],
                    txx[15],
                    txx[16],
                    txx[9],
                    None,
                    1,
                )
                tgt_count = 0
                for tgtt in targets:
                    [
                        id_nr,
                        team,
                        rcs,
                        name,
                        running,
                        velocity,
                        lat,
                        lon,
                        targ_height,
                        vx,
                        vy,
                        vz,
                        corridor_breadth,
                        noftargets,
                        typed,
                        threed_waypoints_id,
                        status,
                        maneuvring,
                        classification,
                        _,
                        _,
                        update_time,
                        _,
                        recording_time,
                    ] = basefunctions.get_target_attributes(tgtt)
                    tgt = target.Target(
                        id_nr,
                        team,
                        rcs,
                        name,
                        running,
                        velocity,
                        lat,
                        lon,
                        targ_height,
                        vx,
                        vy,
                        vz,
                        corridor_breadth,
                        noftargets,
                        typed,
                        threed_waypoints_id,
                        status,
                        maneuvring,
                        classification,
                        recording_time,
                        update_time,
                    )

                    self.set_pcl_live_detection(
                        self.rx, tx, tgt, self.splat_obj, self.use_prop
                    )
                    tgt_count = tgt_count + 1

                tx_count = tx_count + 1

            time2 = basefunctions.get_time()
            delta_t = (time2 - time1) / 1000
        
            ## now delete PCL detections that were not updated fast enough
            self.dbaccess.remove_inactive_pcl_detections(basefunctions.get_time(), self.rx.rx_id)

            # now let the runner process sleep if it was fast enough
            if delta_t > self.update_time:
                logging.getLogger("SENSOR_CONTROL").info(
                    "PCL_Rx %s detection loop in %s seconds (delay: %s)  \n ",
                    self.rx.name,
                    delta_t,
                    delta_t - self.update_time,
                )
            else:
                logging.getLogger("SENSOR_CONTROL").info(
                    "PCL_Rx %s detection loop too quick by %s seconds..sleeping !!! \n ",
                    self.rx.name,
                    self.update_time - delta_t,
                )
                time.sleep(self.update_time - delta_t)

    def stop(self):
        """ stops running sensor"""
        self.alive.clear()
        logging.getLogger("SENSOR_CONTROL").info("quitting pcl rx runner %s, ", self.rx)
        for txx in self.txs:
            tx = txclass.Tx(
                txx[0],
                txx[1],
                txx[2],
                txx[4],
                txx[5],
                txx[7],
                txx[8],
                txx[10],
                txx[13],
                txx[11],
                txx[12],
                "directional",
                txx[14],
                txx[15],
                txx[16],
                txx[9],
                None,
                1,
            )
            self.dbaccess.remove_pcl_rx_tx_detections(self.rx.name, tx.callsign)


    def set_pcl_live_detection(self, rx, tx, tgt, splat_obj, radioprop_enabled):
        """ sets PCL live detections """
        ######################### set necessary thresholds #####################
        snr_thresh = pclconstants.SNR_THRESHOLD  # [dB]
        doppler_thresh = pclconstants.DOPPLER_THRESHOLD  # [dB]
        minimal_rcs_threshold = pclconstants.MIN_RCS_THRESHOLD  # [m2]
        ##################################################################
        ### setting just_los to 0 will invoke the usage of propagation loss computation in SPLAT
        ### setting just_los to 1 makes the SPLAT computation easier, ie without propagation losses
        just_los = 0

        ###############check targets height and leave if it is zero ####################
        if tgt.height <= 0:
            return
        ##############################################################################

        ## get bistatic range
        tx_pos = [tx.lat, tx.lon, tx.masl + tx.ahmagl]
        rx_pos = [rx.lat, rx.lon, rx.masl + rx.ahmagl]
        tgt_pos = [tgt.lat, tgt.lon, tgt.height]
        (bistatic_range_km, tgt_rx_range, tgt_tx_range, baseline_range)  = geofunctions.get_bistatic_range(tx_pos, rx_pos, tgt_pos)


        if (tgt_rx_range > pclconstants.MAX_TGT_RX_RANGE) or (
            tgt_tx_range > pclconstants.MAX_TGT_TX_RANGE
        ):  # we constraint the distance to ease computation (rule of thumb max dist for PCL)
            return
        
        ################## now check bistatic Doppler and return if Doppler shift too low
        doppler = 0
        doppler = geofunctions.calculate_bistatic_doppler(rx, tgt, tx) # [Hz]

        # discontinue without detection if bistatic Doppler is too low
        if abs(doppler) < doppler_thresh:
            return


        ################# now compute SNR ############################
        snr = 0
        t_max = pclconstants.MAX_COHERENT_INTEGRATION_TIME_FM  # maximum coherent integration time in [s], e.g. 0.5
        delay_thresh = 1  # [micro secs]
        static_rcs = 0.0 
        tgt_lon = np.array([[tgt.lon]])
        tgt_lat = np.array([[tgt.lat]])
        tgt_height = np.array([[tgt.height]])

        if radioprop_enabled == 1:
            just_los = 0

        if just_los == 1:
            (tgt_rx_los, _) = splat_obj.getLosAndLossProxy(
                rx.lat,
                rx.lon,
                rx.masl + rx.ahmagl,
                tgt.lat,
                tgt.lon,
                tgt.height,
                tx.freq,
                1,
                just_los,
                0,
            )
            (tgt_tx_los, _) = splat_obj.getLosAndLossProxy(
                tgt.lat,
                tgt.lon,
                tgt.height,
                tx.lat,
                tx.lon,
                tx.masl + tx.ahmagl,
                tx.freq,
                1,
                just_los,
                0,
            )
        else:
            (tgt_rx_los, _, tgt_rx_loss) = splat_obj.getLosAndLossProxy(
                rx.lat,
                rx.lon,
                rx.masl + rx.ahmagl,
                tgt.lat,
                tgt.lon,
                tgt.height,
                tx.freq,
                1,
                just_los,
                0,
            )
            (tgt_tx_los, _, tgt_tx_loss) = splat_obj.getLosAndLossProxy(
                tgt.lat,
                tgt.lon,
                tgt.height,
                tx.lat,
                tx.lon,
                tx.masl + tx.ahmagl,
                tx.freq,
                1,
                just_los,
                0,
            )
      
        if ((tgt_rx_los < 0) or (tgt_tx_los < 0)): # los value will eb set < 0 if source or destination below ground etc. see: method getLosAndLoss in splatBurst.cpp
            return # i.e. do not compute further
        
        # Converts the transmitter polarization 'M' (mixed) to 'V' or 'H', depending on which ERP is highest
        erp = tx.returnERP()

        interpol_atten_in_advance = 1
        # defines whether attenuation values should be interpolated in advance or not
        nbr_interpol_angles_atten = 2 * 360
        # defines how many angles should be taken if attenuation values are to be interpolated in advance
        # # # # # nbr_interpol_angles_LOS=2*360; # defines how many angles should be taken for the max_LOS distance # Interpolation not done here anymore

        ## Setting & Calculating of some constants which are independent of target position
        atten_db_km = geofunctions.get_clear_sky_attenuation(tx.freq)
        k = 1.38064852 * 1e-23 # Boltzmann constant in m^2 kg s^-2 K^-1
        g_proc = 10 * math.log10(t_max * tx.bandwidth * 1000) # processing gain [dB] where BW in [kHz]
        c = 299792458.0 # speed of light

        # for the computation of snr_const: see the snr formula in P. Mousel master thesis ETH ZH, equations 2.15 to 2.17 on p.17
        # + 2.15 [dB] = 1.64 scalar from converting erp to EIRP.
        snr_const = (
            erp
            + 2.15
            + g_proc
            + rx.gain
            - abs(rx.losses)
            + 10
            * math.log10(
                (c / (tx.freq * 1e6)) ** 2
                / ((4.0 * math.pi) ** 3 * k * rx.temp_sys * rx.bandwidth * 1000)
            )
        )
        # for usage with splat! propagation losses, we remove all the factors of free space loss for this snr_const
        snr_const_splat = (
            erp
            + 2.15
            + g_proc
            + rx.gain
            - abs(rx.losses)
            - 10 * math.log10(k * rx.temp_sys * rx.bandwidth * 1000)
        )

        if interpol_atten_in_advance == 1:
            new_interpol_angles = np.linspace(0, 2 * math.pi, nbr_interpol_angles_atten + 1)
            new_interpol_angles = np.delete(new_interpol_angles, -1)
            rx_horiz_diagr_att_interp, rx.hor_att_angle_step = interpolate_attenuation(
                rx.horiz_diagr_att, new_interpol_angles
            )
            tx_horiz_diagr_att_interp, tx.hor_att_angle_step = interpolate_attenuation(
                tx.horiz_diagr_att, new_interpol_angles
            )
        else:
            rx_horiz_diagr_att_interp = rx.horiz_diagr_att
            tx_horiz_diagr_att_interp = rx.horiz_diagr_att
            rx.hor_att_angle_step = 1000
            tx.hor_att_angle_step = 1000

        Tx = setup_vertical_attenuation(tx, "Tx", tx_horiz_diagr_att_interp)

        Rx = setup_vertical_attenuation(rx, "Rx", rx_horiz_diagr_att_interp)



        # for usage with splat! propagation losses, we remove all the factors of free space loss for this snr_const
        snr_const_splat = (
            erp
            + 2.15
            + g_proc
            + rx.gain
            - abs(rx.losses)
            - 10 * math.log10(k * rx.temp_sys * rx.bandwidth * 1000)
        )


        dist_delay_limit = delay_thresh * c / 1e6 + (baseline_range * 1000) # dist_delay_limit [m], delay_thresh [us], baseline_range in [km] * 1000 in [m]

        rcs, snr = calculate_min_rcs_without_los_single_pos(
                tgt_lon,
                tgt_lat,
                tgt_height,
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
                tgt_rx_loss + tgt_tx_loss,
        )

        if (rcs > pclconstants.MIN_BISTATIC_RCS_ONLINE_DETECTION): # this means that the target with set bistatic RCS cannot be detected with SNR above SNR_threshold 
            return
        if (rcs < 0): # the snr computation could not be completed
            return
        
        # Doppler shift was good enough if we reached this far, see above. 
        # So just check the snr and the rcs_thresholds
        if (snr > snr_thresh) and (rcs < minimal_rcs_threshold): # snr and snr_thresh in [dB]
            # doppler velocity
            bistatic_velocity = doppler * (sc.speed_of_light/(tx.freq * 1000000)) # [Hz] * [m/s]/[Hz] = [m/s]

            # write PCL detections to DB 
            now = basefunctions.get_time()
            writelist = []
            # pcl_rx_name, pcl_tx_callsign, targ_id, det_time, range, doppler, tgt_lat, tgt_lon, tgt_height, recording_time
            #print("doppler shift, bistatic_velocity, snr = ", doppler, bistatic_velocity, snr[0][0])
            currstr = (
                rx.rx_id,
                tx.tx_id,
                rx.name,
                tx.callsign,
                str(tgt.id_nr),
                str(now),
                str(bistatic_range_km),
                str(doppler),
                str(tgt.lat),
                str(tgt.lon),
                str(tgt.height),
                str(tgt.recording_time),
                str(tgt.vx),
                str(tgt.vy),
                str(tgt.vz),
                str(tgt.velocity),
                str(bistatic_velocity),
                str(snr) 
            )
            writelist.append(currstr)
            self.dbaccess.write_pcl_dets(tuple(writelist))
