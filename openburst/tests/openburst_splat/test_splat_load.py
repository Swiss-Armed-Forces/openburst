""" 

this tests if the compiled openburst-splat shared library can be loaded

"""

import pytest
from openburst.functions import basefunctions


def test_set_system_path():
    try:
        basefunctions.set_openburst_system_path()
    except:
        pytest.fail("Could not set openburst system path ..")

def test_set_lib_path():
    try:
        basefunctions.set_openburst_linked_lib_path()
    except:
        pytest.fail("Could not set openburst shared library path ..")    


def test_import_libsplat():
    try:
        import libsplathd
    except ModuleNotFoundError:
        pytest.fail("Could not import libsplathd ..")
        

        