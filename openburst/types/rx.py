""" Module for PCL Rx"""
import math

class Rx():
    """ Class for Rx"""
    def __init__(
        self,
        rx_id,
        masl,
        lat,
        lon,
        ahmagl,
        signal_type,
        limit_distance,
        lostxids,
        status,
        bandwidth,
        horiz_diagr_att,
        vert_diagr_att,
        gain,
        losses,
        temp_sys,
        name="",
        txcallsigns=""
    ):
        self.rx_id = rx_id
        self.masl = masl  # Terrain height in meter above sea level
        self.lat = lat
        self.lon = lon
        self.ahmagl = ahmagl  # Antenna height in meter above ground level
        self.signal_type = signal_type  # DVB, DAB, or .....
        self.limit_distance = limit_distance  # in meter
        self.lostxids = lostxids
        self.status = status

        self.bandwidth = bandwidth  # kHz
        self.horiz_diagr_att = horiz_diagr_att  # horizontal radiation pattern
        self.vert_diagr_att = vert_diagr_att  # vertical attenuation diagram
        self.gain = gain  # antenna gain in dB
        self.losses = losses  # losses: antenna to receiver input in dB
        self.temp_sys = temp_sys  # Receiving System noise temperature in K
        self.name = name
        self.update_time = -1
        self.txcallsigns = (
            txcallsigns  # a comma separated string list of callsigns of Txs
        )
        

    def return_beam_width(self):  # TBD
        """rerurn beamwith of Rx"""
        return 5 * math.pi / 180


    def get_rx_signal_type(self):  # this returns a string FM/DAB/DVB-T for passive radar...which is necessary for SPLAT to compute the path free space and prop losses
        """ returns Rx signal type"""
        if "FM" in self.signal_type:
            return "FM"
        if "DAB" in self.signal_type:
            return "DAB"
        if "DVB" in self.signal_type:
            return "DVB"
        return ""



def to_Rx(dct):
    """ returns an Rx instance """
    return Rx(
        dct["rx_id"],
        dct["masl"],
        dct["lat"],
        dct["lon"],
        dct["ahmagl"],
        dct["signal_type"],
        dct["limit_distance"],
        dct["lostxids"],
        dct["status"],
        dct["bandwidth"],
        dct["horiz_diagr_att"],
        dct["vert_diagr_att"],
        dct["gain"],
        dct["losses"],
        dct["temp_sys"],
        dct["name"],
        dct["txcallsigns"]
    )
