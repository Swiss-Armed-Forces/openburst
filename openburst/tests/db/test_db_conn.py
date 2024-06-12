"""
test connection to postgres db
"""

import pytest
from openburst.functions import dbfunctions

def test_db_conn():
    try:
        conn = dbfunctions.connect_to_db()
        if (conn is None):
            pytest.fail("Could not connect to db ..")
    except Exception: # pylint: disable=bare-except
        pytest.fail("Could not connect to db ..")


if __name__ == "__main__":
    test_db_conn()