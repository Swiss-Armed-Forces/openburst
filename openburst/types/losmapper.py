"""Module for handling Line of Sight (LoS) mappings"""

import logging
import logging.config

from openburst.pcl import coverage
from openburst.types.callsignmapper import CallsignMapper


class TxToLocationLOSMapper:
    """ This class maps any possible Tx locations to a certain LOS array, for some trajectories. 
        This is helpful as several Tx might be at the exact same position (e.g. if same frequency). 
        tx_id_to_loc_id_map requires that there are no holes in the Tx ID range, i.e. every Tx"""
    
    def __init__(self, largest_tx_id):
        # print("largest Tx ID = ", largest_tx_id+1)
        self.tx_id_to_loc_id_map = [-1] * (
            largest_tx_id + 1
        )  # maps Tx ID to Location ID - simply list of strings
        # print("self.tx_id_to_loc_id_map = ", self.tx_id_to_loc_id_map)
        self.loc_to_loc_id_map = (
            CallsignMapper()
        )  # maps location to location ID: If new Tx added, checks if LOS already calc for this location, Dict with Location tuple as input, loc_ID output
        self.all_los_arr_tx_all_traj = (
            []
        )  # stores the LOS for all trajectories.   List with input: loc_ID
        self.los_grid_all_loc = (
            []
        )  # stores the LOS grid for a given location      List with input: loc_ID

    def get_tx_location(self, tx):
        """ function to return tx location as tuple"""
        return (tx.lat, tx.lon, tx.masl + tx.ahmagl)  

  
    def get_los_grid(self, tx_id):
        """ function to return los grid"""
        loc_id = self.tx_id_to_loc_id_map[tx_id]
        return self.los_grid_all_loc[loc_id]

    def calculate_los_grid_if_loc_not_done(
        self,
        tx,
        x_start,
        x_stop,
        x_step,
        y_start,
        y_stop,
        y_step,
        z_start,
        z_stop,
        z_step,
        radioprop_enabled,
        reverse_direction,
        nof_lats,
        nof_lons,
    ):
        """ function to return los grid"""
        logging.getLogger("PCL").info(
            "PRclasses.py: calculate_los_grid_if_loc_not_done: Tx.tx_id = %s, self.tx_id_to_loc_id_map = %s ",
            tx.tx_id,
            self.tx_id_to_loc_id_map,
        )
        if (
            self.tx_id_to_loc_id_map[tx.tx_id] == -1
        ):  # this should be queried if having > 1Rx that have same Tx: this test faster than checking new_pot_location

            new_pot_location = self.get_tx_location(tx)
            loc_id = self.loc_to_loc_id_map[new_pot_location]
            logging.getLogger("PCL").info(
                "PRclasses.py: calculate_los_grid_if_loc_not_done: new_pot_location = %s, loc_id = %s ",
                new_pot_location,
                loc_id,
            )
            if loc_id == -1:  # LOS not yet calc for this location
                loc_id = len(self.loc_to_loc_id_map)
                self.loc_to_loc_id_map[new_pot_location] = loc_id

                logging.getLogger("PCL").info(
                    "PRclasses.py calculate_los_grid_if_loc_not_done: calling calcCoverage.get_antenna_los_grid TX-TGT GRID: %s, %s",
                    tx.masl,
                    tx.ahmagl,
                )
                los_grid_tx = coverage.get_antenna_los_grid(
                    tx.lon,
                    tx.lat,
                    tx.masl + tx.ahmagl,
                    x_start,
                    x_stop,
                    x_step,
                    y_start,
                    y_stop,
                    y_step,
                    z_start,
                    z_stop,
                    z_step,
                    tx.callsign,
                    radioprop_enabled,
                    reverse_direction,
                    tx.getTxSignalType(),
                    nof_lats,
                    nof_lons,
                )

                self.los_grid_all_loc.append(los_grid_tx)
                logging.getLogger("PCL").info(
                    "------- PRclasses.py calculate_los_grid_if_loc_not_done: finished calculating LOS for Tx tx_id = %s at Location ID = %s : %s",
                    tx.tx_id,
                    loc_id,
                    new_pot_location,
                )

            logging.getLogger("PCL").info(
                "++++++ PRclasses.py calculate_los_grid_if_loc_not_done: setting loc_ID = %s at index = %s",
                loc_id,
                tx.tx_id,
            )
            self.tx_id_to_loc_id_map[tx.tx_id] = loc_id
