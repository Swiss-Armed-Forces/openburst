
"""Module providing a class for active monostatic sensor"""

from datetime import datetime, timezone

class ActiveMonostaticSensor:
    """Class for handling all active monostatic sensor (RAD)"""
    def __init__(
        self,
        id_nr,
        name,
        status,
        lat,
        lon,
        power,
        antenna_diam,
        freq,
        pulse_width,
        cpi_pulses,
        bandwidth,
        pfa,
        rotation_time,
        category,
        min_elevation,
        max_elevation,
        orientation,
        horiz_aperture,
        min_detection_range,
        max_detection_range,
        min_detection_height,
        max_detection_height,
        min_detection_tgt_speed,
        max_detection_tgt_speed,
    ):
        self.id_nr = id_nr
        name = name.replace("<br>", "")
        self.name = name
        self.status = status
        self.lat = lat
        self.lon = lon
        self.power = power
        self.antenna_diam = antenna_diam
        self.freq = freq
        self.pulse_width = pulse_width
        self.cpi_pulses = cpi_pulses
        self.bandwidth = bandwidth
        self.pfa = pfa
        self.rotation_time = rotation_time
        self.category = category
        self.min_elevation = min_elevation
        self.max_elevation = max_elevation
        self.orientation = orientation
        self.horiz_aperture = horiz_aperture
        self.min_detection_range = min_detection_range
        self.max_detection_range = max_detection_range
        self.min_detection_height = min_detection_height
        self.max_detection_height = max_detection_height
        self.min_detection_tgt_speed = min_detection_tgt_speed
        self.max_detection_tgt_speed = max_detection_tgt_speed
        now = datetime.now(timezone.utc)
        curr_time = datetime.timestamp(now)
        self.prev_update_time = curr_time  # this will be updated each time the sensor delivers plots (at the rotation time rate)

    def __str__(self):  # printing function
        return "<Active Sensor id:%s lat:%s lon:%s power:%s freq:%s>" % (
            self.id_nr,
            self.lat,
            self.lon,
            self.power,
            self.freq,
        )


def to_active_rad_params(dct):
    """Function ffor converting to rad parameters"""
    return ActiveMonostaticSensor(
        dct["id_nr"],
        dct["name"],
        dct["status"],
        dct["lat"],
        dct["lon"],
        dct["power"],
        dct["antenna_diam"],
        dct["freq"],
        dct["pulse_width"],
        dct["cpi_pulses"],
        dct["bandwidth"],
        dct["pfa"],
        dct["rotation_time"],
        dct["category"],
        dct["min_elevation"],
        dct["max_elevation"],
        dct["orientation"],
        dct["horiz_aperture"],
        dct["min_detection_range"],
        dct["max_detection_range"],
        dct["min_detection_height"],
        dct["max_detection_height"],
        dct["min_detection_tgt_speed"],
        dct["max_detection_tgt_speed"],
    )
