"""Module providing a class for detection"""

class Detection:
    """Class for all detection attributes"""
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