"""Module for running RAD sensor"""

import multiprocessing as mp
import logging
import time
import math

from openburst.functions import geofunctions
from openburst.functions import basefunctions
from openburst.functions import radfunctions
from openburst.types import dbpersistentaccess


class RADRunnerClass(mp.Process):
    """ class for running RAD Sensor detections in a single process for each RAD sensor"""

    def __init__(self, rad, rad_start_time, splat_obj, rcs, use_prop):
        # must call this before anything else
        mp.Process.__init__(self)
        self.daemon = False
        self.alive = mp.Event()
        self.rad = rad
        self.rad_start_time = rad_start_time
        self.rad_id_nr = None
        self.splat_obj = splat_obj
        self.target_rcs = rcs
        self.max_det_range_km = 0
        self.use_prop = use_prop
        self.rad_height_masl = -1 # will be written later
        self.dbaccess = dbpersistentaccess.DbConnector(logging.getLogger(__name__), "RAD_DETECTION_RUNNER")

    def run(self):
        [
            rad_id_nr,
            rad_name,
            rad_status,
            rad_lat,
            rad_lon,
            rad_power,
            rad_antenna_diam,
            rad_freq,
            rad_pulse_width,
            rad_cpi_pulses,
            rad_bandwidth,
            rad_pfa,
            rad_rotation_time,
            rad_category,
            rad_min_elevation,
            rad_max_elevation,
            rad_orientation,
            rad_horiz_aperture,
            rad_min_detection_range,
            rad_max_detection_range,
            rad_min_detection_height,
            rad_max_detection_height,
            rad_min_detection_tgt_speed,
            rad_max_detection_tgt_speed,
            rad_update_time,
            rad_team,
        ] = basefunctions.get_rad_attributes(self.rad)
        self.rad_id_nr = rad_id_nr

        self.max_det_range_km = radfunctions.radar_eq_max_dist(
            rad_power,
            rad_antenna_diam,
            rad_freq,
            rad_pulse_width,
            rad_cpi_pulses,
            rad_bandwidth,
            rad_pfa,
            self.target_rcs,
        )
        try:
            self.rad_height_masl = self.splat_obj.get_elevation(rad_lat, rad_lon)
        except Exception: # pylint: disable=bare-except
            self.rad_height_masl = 1000

        while not self.alive.is_set():
            n1 = basefunctions.get_time()
            self.run_rad(
                self.splat_obj,
                rad_id_nr,
                rad_name,
                rad_status,
                rad_lat,
                rad_lon,
                rad_power,
                rad_antenna_diam,
                rad_freq,
                rad_pulse_width,
                rad_cpi_pulses,
                rad_bandwidth,
                rad_pfa,
                rad_rotation_time,
                rad_category,
                rad_min_elevation,
                rad_max_elevation,
                rad_orientation,
                rad_horiz_aperture,
                rad_min_detection_range,
                rad_max_detection_range,
                rad_min_detection_height,
                rad_max_detection_height,
                rad_min_detection_tgt_speed,
                rad_max_detection_tgt_speed,
                rad_update_time,
                rad_team,
                self.rad_start_time,
                self.max_det_range_km,
                self.rad_height_masl,
                self.use_prop,
            )
            n2 = basefunctions.get_time()
            delta_t = (n2 - n1) / 1000

            if delta_t > rad_rotation_time:
                logging.getLogger("SENSOR_CONTROL").info(
                    "RAD %s too slow by %s seconds !!! \n ", rad_id_nr, delta_t
                )
            else:
                logging.getLogger("SENSOR_CONTROL").info(
                    "RAD %s was quicker by %s seconds..sleeping !!! \n ",
                    rad_id_nr,
                    rad_rotation_time - delta_t,
                )
                time.sleep(rad_rotation_time - delta_t)

    def stop(self):
        """stops running rad sensor"""
        self.alive.clear()
        logging.getLogger("SENSOR_CONTROL").info("quitting rad runner %s, ", self.rad)
        self.dbaccess.remove_rad_detections(
            self.rad_id_nr
        )  

    def run_rad(self,
        splat_obj,
        rad_id_nr,
        _,
        rad_status,
        rad_lat,
        rad_lon,
        rad_power,
        rad_antenna_diam,
        rad_freq,
        rad_pulse_width,
        rad_cpi_pulses,
        rad_bandwidth,
        rad_pfa,
        rad_rotation_time,
        _rad_category,
        _rad_min_elevation,
        _rad_max_elevation,
        _rad_orientation,
        _rad_horiz_aperture,
        _rad_min_detection_range,
        _rad_max_detection_range,
        _rad_min_detection_height,
        _rad_max_detection_height,
        _rad_min_detection_tgt_speed,
        _rad_max_detection_tgt_speed,
        _rad_update_time,
        rad_team,
        _rad_start_time,
        max_det_range_km,
        rad_height_masl,
        _use_prop,
    ):
        """ reads rad int from db and runs them """ 
        if rad_status == 0:  # do not start status==0 rads
            return

        logging.getLogger("SENSOR_CONTROL").info(
            "::::::::::::::::updating detections for rad: %s (, rad at masl = %s)",
            rad_id_nr,
            rad_height_masl,
        )
        team = rad_team

        targets = self.dbaccess.get_targets(
            team
        )  # targets need to be read again and again
        if targets is not None:
            logging.getLogger("SENSOR_CONTROL").info(
                "*********run_rad %s: got targets.....: nof = %s", rad_id_nr, len(targets)
            )
        else:
            return

        all_dets_list = None
        if targets is not None:
            seen = set()
            all_dets_list = []
            for i in range(len(targets)):
                curr_target = targets[i]
                [
                    id_nr,
                    team,
                    rcs,
                    _name,
                    _running,
                    _velocity,
                    lat,
                    lon,
                    targ_height,
                    vx,
                    vy,
                    vz,
                    _corridor_breadth,
                    _noftargets,
                    _typed,
                    _threed_waypoints_id,
                    _status,
                    _maneuvring,
                    _classification,
                    _waypoints,
                    _waypoints_index,
                    _update_time,
                    _terrain_height,
                    _recording_time,
                ] = basefunctions.get_target_attributes(curr_target)
                curr_dist_km = geofunctions.get_2d_distance_between_locs_heights(
                    rad_lat, rad_lon, rad_height_masl, lat, lon, targ_height
                )
                if (
                    curr_dist_km > max_det_range_km
                ):  # do not further consider targets too far away
                    continue

                pd = radfunctions.get_rad_pd(
                    rad_power,
                    rad_antenna_diam,
                    rad_freq,
                    rad_pulse_width,
                    rad_cpi_pulses,
                    rad_bandwidth,
                    rad_pfa,
                    rcs,
                    curr_dist_km,
                    max_det_range_km,
                    rad_lat,
                    rad_lon,
                    rad_height_masl,
                    lat,
                    lon,
                    targ_height,
                    splat_obj,
                )

                doppler_shift = geofunctions.monostatic_doppler(
                    rad_freq,
                    rad_lat,
                    rad_lon,
                    rad_height_masl,
                    lat,
                    lon,
                    targ_height,
                    vx,
                    vy,
                    vz,
                )
                doppler_ok = True
                if doppler_shift is None:
                    doppler_ok = False
                else:
                    if (
                        math.fabs(doppler_shift) < 5.0
                    ):  # dopp shift threshold set arbitrarily to 5Hz (theoretically the integration time of each RAD has to be considered)
                        doppler_ok = False

                if (doppler_ok) and (pd > 0.0):
                    now = basefunctions.get_time()
                    # curr_det should contain: targ_id, sensor_id, team, pd, plot, track, det_time, lat, lon, height, vx, vy, vz, cpx, cpy, cpz, cvx, cvy, cvz, recording_time
                    curr_det = (
                        id_nr,
                        rad_id_nr,
                        "blue",
                        pd,
                        1.0,
                        3.0,
                        now,
                        targets[i][6],
                        targets[i][7],
                        targets[i][8],
                        targets[i][9],
                        targets[i][10],
                        targets[i][11],
                        0,
                        0,
                        0,
                        0,
                        0,
                        0,
                        targets[i][23],
                    )
                    curr_det_id = (id_nr, rad_id_nr)

                    if curr_det_id not in seen:
                        all_dets_list.append(curr_det)
                        seen.add(curr_det_id)

        # now remove the detection that were not updated anymore by this rad
        self.dbaccess.remove_inactive_rad_detections(rad_id_nr, rad_rotation_time)

        # now add all the new detections at once
        if (all_dets_list is not None) and (len(all_dets_list) > 0):
            logging.getLogger("SENSOR_CONTROL").info(
                "++++++++++++++++++in run_rad %s: goign to write RAD detections: %s ",
                rad_id_nr,
                len(all_dets_list),
            )
            self.dbaccess.write_rad_dets(tuple(all_dets_list))
