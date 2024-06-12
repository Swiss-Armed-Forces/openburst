"""
tests if openburst-splat integration for paralellized matrix grid propagation computation works
"""

import os
import time
import scipy.constants as sc
import numpy as np
import pytest

from openburst.functions import basefunctions 
basefunctions.set_openburst_system_path()
basefunctions.set_openburst_linked_lib_path()


import libsplathd as splat


def test_openburst_splat_parallel():

    # compiled splat shared library searches for for splat compiled code in ./SPLAT_RADIOPROP/
    # so run from the directory of "radterrrain"
    openburst_root_dir = basefunctions.get_openburst_root_dir()
    os.chdir(openburst_root_dir+"/radterrain")

    nof_lats = 4
    nof_lons = 4
    nofprocs = 6  # number of processes for MPI (ideally equal to number of cores)

    for uu in range(1):
        p_site = splat.prop_site()
        lat_min = 44
        lat_max = 46
        lon_min = 360 - 4
        lon_max = 360 - 3
        p_site.setLatLonBoundaries(lat_min, lat_max, lon_min, lon_max)
        # Caution: if lat, lon outside the available SDF files, it will not return (it hangs)
        # Caution splat convention for lon: 0 and then go west +1, +2...and 360 is again at 0 (so e.g lat:47,lon:7 is actually 47,360-7)

        dest_lat_arr = np.array([46.2, 46.4, 46.8, 47.0, 48.0])
        dest_lon_arr = np.array([360 - 5.0, 360.0 - 5.2, 360.0 - 4.8])
        dest_alt = (
            712 / sc.foot
        )  # random.uniform(1000, 3000) / sc.foot # splat expects alt in feet
        src_lat = 47
        src_lon = 360 - 6.1
        src_alt = (
            899 / sc.foot
        )  # random.uniform(0, 12000) / sc.foot # splat expects alt in feet
        freq = 88.0  # MHz

        i = 0

        # send the lat-lon 2D array, masl and lat,lon, freq, int_masl to C++
        # C++ code will use mpi to solve this and return a 2D array of 0/1 for the los
        start = time.time()

        justLos = 0
        asl = 1

        ############# compute LoS, prop_loss and free_space loss or just Los (set justLos= 1)
        reverseDirection = 1
        ret = p_site.getLosAndLossMatrix(
            src_lat,
            src_lon,
            src_alt,
            dest_lat_arr.tolist(),
            dest_lon_arr.tolist(),
            dest_alt,
            freq,
            asl,
            nofprocs,
            justLos,
            reverseDirection,
        )

        end = time.time()
        print(
            "########### elapsed time [s] ",
            end - start,
            ", for ",
            nof_lats * nof_lons,
            " splat calls with ",
            nofprocs,
            " parallel processes",
        )

        ####### and now get the matrices required
        los_arr = np.array(ret.readLosMatrix())
        dist_arr = np.array(ret.readDistMatrix())
        print(
            "--------------------------reverseDirection = ",
            reverseDirection,
            "------------------",
        )
        print("dest_lat_arr = ", dest_lat_arr)
        print("dest_lon_arr = ", dest_lon_arr)
        print("dest_alt = ", dest_alt)
        print("src = ", src_lat, ", ", src_lon, ", ", src_alt)
        print("los array = ", los_arr)
        print("dist array = ", dist_arr)

        if justLos == 0:
            try:
                loss_arr = np.array(ret.readLossMatrix())  # this can only be done if getLosAndLossMatrix was called
                assert True
            except Exception: # pylint: disable=bare-except
                pytest.fail("Could not read propagation losses array ..")

            try:
                free_loss_arr = np.array(ret.readFreeLossMatrix())  # this can only be done if getLosAndLossMatrix was called
                assert True
            except Exception: # pylint: disable=bare-except
                pytest.fail("Could not read free space losses array ..")
            print("loss array = ", loss_arr)
            print("free_loss array = ", free_loss_arr)



#if __name__ == "__main__":
#    test_openburst_splat_parallel()
