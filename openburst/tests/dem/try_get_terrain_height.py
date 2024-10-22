""" 

tests terrain height can be computed for a given lat/lon position

"""

#import pytest
from openburst.functions import basefunctions
from openburst.functions import geofunctions
basefunctions.set_openburst_system_path()
basefunctions.set_openburst_linked_lib_path()
import libsplathd as splat


def try_get_terrain_height():
    try:
        lat = 47.0
        lon = 8.1
        #lat = 57.41
        #lon = -6.19
        alt = geofunctions.get_terrain_height(splat,lat, lon)
        print("alt = ", alt)
        #assert alt==916 # mASL = 916 at 47.0, 8.1
    except Exception: # pylint: disable=bare-except
        print("Could not read terrain height ..")


def main():
    try_get_terrain_height()


if __name__ == "__main__":
    main()