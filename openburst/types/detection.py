"""Module providing a class for detection"""

class Detection:
    """Class for all RAD detection attributes"""
    def __init__(
        self,
        targ_id,
        sensor_id,
        team,
        pd,
        plot,
        track,
        det_time,
        lat,
        lon,
        height,
        vx,
        vy,
        vz,
        cpx,
        cpy,
        cpz,
        cvx,
        cvy,
        cvz,
    ):
        self.targ_id = targ_id
        self.sensor_id = sensor_id
        self.team = team
        self.pd = pd
        self.plot = plot
        self.track = track
        self.det_time = det_time
        self.lat = lat
        self.lon = lon
        self.height = height
        self.vx = vx
        self.vy = vy
        self.vz = vz
        self.cpx = cpx
        self.cpy = cpy
        self.cpz = cpz
        self.cvx = cvx
        self.cvy = cvy
        self.cvz = cvz

def to_detection(dct):
    """Function to return a detection instance"""
    return Detection(
        dct["targ_id"],
        dct["sensor_id"],
        dct["team"],
        dct["pd"],
        dct["plot"],
        dct["track"],
        dct["det_time"],
        dct["lat"],
        dct["lon"],
        dct["height"],
        dct["vx"],
        dct["vy"],
        dct["vz"],
        dct["cpx"],
        dct["cpy"],
        dct["cpz"],
        dct["cvx"],
        dct["cvy"],
        dct["cvz"],
    )


class PCL_Detection:
    """Class for all PCL detection attributes"""
    def __init__(
        self,
        team,
        det_time,
        targ_id,
        rx_id,
        tx_id,
        bi_range,
        bi_doppler,
        bi_velocity,
        range_std_dev,
        vel_std_dev,
    ):
        self.team = team
        self.det_time = det_time
        self.targ_id = targ_id
        self.rx_id = rx_id
        self.tx_id = tx_id
        self.bi_range = bi_range
        self.bi_doppler = bi_doppler
        self.bi_velocity = bi_velocity
        self.range_std_dev = range_std_dev
        self.vel_std_dev = vel_std_dev


def to_pcl_detection(dct):
    """Function to return a PCL detection instance"""
    return PCL_Detection(
        dct["team"],
        dct["det_time"],
        dct["targ_id"],
        dct["rx_id"],
        dct["tx_id"],
        dct["bi_range"],
        dct["bi_doppler"], 
        dct["bi_velocity"],
        dct["range_std_dev"],
        dct["vel_std_dev"])
