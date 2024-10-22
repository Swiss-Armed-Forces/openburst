""" 

tests if the SDF files for digital elevation model, used by radterrain and splat, is set properly

"""
import os
import pytest
from openburst.constants import splatconstants

def test_get_dem_files():
    try:
        sdf_found = False
        for fname in os.listdir(splatconstants.DEM_FILES_PATH):
          if fname.endswith('.sdf'):
            sdf_found = True

        if not sdf_found:
          pytest.fail("not a single.sdf file found in folder..please check the DEM folder configuration in splatconstants.py")
    except Exception: # pylint: disable=bare-except
        pytest.fail("Could not read sdf files from dem folder ..")