"""Module providing a class for a geographical grid"""

class GridParameters:
    """Class for a geographical grid"""
    def __init__(
        self,
        lat_start,
        lat_stop,
        lon_start,
        lon_stop,
        res_x,
        res_y,
        res_z,
        min_x,
        max_x,
        min_y,
        max_y,
        min_z,
        max_z,
        amt_pts_x,
        amt_pts_y,
        amt_pts_z,
    ):
        self.lat_start = lat_start  # from bottom left corner point      # 47.15
        self.lat_stop = lat_stop  # from top right corner point        # 47.52
        self.lon_start = lon_start  # from bottom left corner point      # 8.3
        self.lon_stop = lon_stop  # from top right corner point        # 9
        self.res_x = (lon_stop - lon_start) / amt_pts_x  # res_x              # meter
        self.res_y = (lat_stop - lat_start) / amt_pts_y  # res_y              # meter
        self.res_z = res_z  # tag 0 or put very high value if you don't wan to distinguish between height levels
        self.min_x = lon_start
        self.max_x = lon_stop
        self.min_y = lat_start
        self.max_y = lat_stop
        self.min_z = min_z  # Swissgrid
        self.max_z = max_z  # Swissgrid
        self.amt_pts_x = amt_pts_x
        self.amt_pts_y = amt_pts_y
        self.amt_pts_z = amt_pts_z



def to_grid_params(dct):
    """returns an instance of GridParameters"""
    return GridParameters(
        dct["lat_start"],
        dct["lat_stop"],
        dct["lon_start"],
        dct["lon_stop"],
        dct["res_x"],
        dct["res_y"],
        dct["res_z"],
        dct["min_x"],
        dct["max_x"],
        dct["min_y"],
        dct["max_y"],
        dct["min_z"],
        dct["max_z"],
        dct["amt_pts_x"],
        dct["amt_pts_y"],
        dct["amt_pts_z"],
    )