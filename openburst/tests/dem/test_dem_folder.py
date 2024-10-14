""" 

tests if the SDF files for digital elevation model, used by radterrain and splat, is set properly

"""
import os
import pytest
from openburst.constants import splatconstants

def test_get_dem_files():
    try:
        for fname in os.listdir(splatconstants.DEM_FILES_PATH):
          if not fname.endswith('.sdf'):
            pytest.fail("non .sdf file found in folder..please remove all non .sdf files from this folder")
    except Exception: # pylint: disable=bare-except
        pytest.fail("Could not read sdf files from dem folder ..")