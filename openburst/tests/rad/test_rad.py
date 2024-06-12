"""
tests rad functionality
"""

import pytest
from openburst.functions import radfunctions

def test_rad_function():
    try:
        ret = radfunctions.radar_eq_pd(20000, 1.0, 1.0, 43.0, 4, 3,0.000001,1,51000)
    except Exception:
        pytest.fail("Could not run radfunction routine ..")
        

    
