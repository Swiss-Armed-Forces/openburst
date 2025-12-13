import json
import numpy as np
import tornado

from openburst.functions.geofunctions import (
    calculate_bistatic_doppler,
    get_bistatic_range,
)
from openburst.constants.openburst_config import UTIL_SERVER_PORT
from openburst.types.raddetectionrunner import rad_pd_doppler_filtered
from openburst.types.rx import Rx
from openburst.types.splatmanager import SharedSPLAT
from openburst.types.target import Target
from openburst.types.tx import Tx


class BistaticRangeHandler(tornado.web.RequestHandler):
    def get(self):
        emitter_lat = float(self.get_argument("emitter_lat"))
        emitter_lon = float(self.get_argument("emitter_lon"))
        emitter_alt = float(self.get_argument("emitter_alt"))
        emitter_antenna_height = float(self.get_argument("emitter_antenna_height"))
        receiver_lat = float(self.get_argument("receiver_lat"))
        receiver_lon = float(self.get_argument("receiver_lon"))
        receiver_alt = float(self.get_argument("receiver_alt"))
        target_lat = float(self.get_argument("target_lat"))
        target_lon = float(self.get_argument("target_lon"))
        target_alt = float(self.get_argument("target_alt"))

        result = get_bistatic_range(
            (emitter_lat, emitter_lon, emitter_alt + emitter_antenna_height),
            (receiver_lat, receiver_lon, receiver_alt),
            (target_lat, target_lon, target_alt),
        )[0]

        self.write(str(result))


class BistaticDopplerHandler(tornado.web.RequestHandler):
    def get(self):
        emitter_lat = float(self.get_argument("emitter_lat"))
        emitter_lon = float(self.get_argument("emitter_lon"))
        emitter_alt = float(self.get_argument("emitter_alt"))
        emitter_antenna_height = float(self.get_argument("emitter_antenna_height"))
        receiver_lat = float(self.get_argument("receiver_lat"))
        receiver_lon = float(self.get_argument("receiver_lon"))
        receiver_alt = float(self.get_argument("receiver_alt"))
        receiver_antenna_height = float(self.get_argument("receiver_antenna_height"))
        target_lat = float(self.get_argument("target_lat"))
        target_lon = float(self.get_argument("target_lon"))
        target_alt = float(self.get_argument("target_alt"))
        # vx is the velocity along the lon axis [m / s].
        # vy is the velocity along the lat axis [m / s].
        # vz is the velocity along the   z axis [m / s].
        target_vx = float(self.get_argument("target_vlon"))
        target_vy = float(self.get_argument("target_vlat"))
        target_vz = float(self.get_argument("target_vz"))

        result = calculate_bistatic_doppler(
            # Receiver.
            Rx(
                rx_id=None,
                masl=receiver_alt,
                lat=receiver_lat,
                lon=receiver_lon,
                ahmagl=receiver_antenna_height,
                signal_type=None,
                limit_distance=None,
                lostxids=None,
                status=None,
                bandwidth=None,
                horiz_diagr_att=None,
                vert_diagr_att=None,
                gain=None,
                losses=None,
                temp_sys=None,
                name=None,
                txcallsigns=None,
            ),
            # Target.
            Target(
                id_nr=0,
                team=None,
                rcs=None,
                name="",
                running=None,
                velocity=np.sqrt(target_vx**2 + target_vy**2 + target_vz**2),
                lat=target_lat,
                lon=target_lon,
                height=target_alt,
                vx=target_vx,
                vy=target_vy,
                vz=target_vz,
                corridor_breadth=None,
                noftargets=None,
                typed=False,
                threeD_waypoints_id=None,
                status=None,
                maneuvring=None,
                classification=None,
                rec_time=None,
                update_time=None,
            ),
            # Emitter.
            Tx(
                tx_id=None,
                callsign=None,
                sitename=None,
                lat=emitter_lat,
                lon=emitter_lon,
                masl=emitter_alt,
                ahmagl=emitter_antenna_height,
                freq=-1,
                bandwidth=None,
                erp_h=None,
                erp_v=None,
                type_in=None,
                horiz_diagr_att=None,
                vert_diagr_att=None,
                pol=None,
                signal_type=None,
                losrxids=None,
                status=1,
            ),
        )

        self.write(str(result))


class RadDetectionHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._splat = SharedSPLAT()

    def get(self):
        radar_json = self.get_argument("radar")
        radar = json.loads(radar_json)

        target_json = self.get_argument("target")
        target = json.loads(target_json)

        doppler_shift_threshold = float(self.get_argument("doppler_shift_threshold", default="5.0"))

        pd = rad_pd_doppler_filtered(
            # Radar parameters.
            radar["lat"],
            radar["lon"],
            radar["alt"],
            radar["power"],
            radar["diameter"],
            radar["frequency"],
            radar["pulse_width"],
            radar["cpi_pulses"],
            radar["bandwidth"],
            radar["pfa"],
            # Target parameters.
            target["lat"],
            target["lon"],
            target["alt"],
            target["vlon"],
            target["vlat"],
            target["vz"],
            target["cross_section"],
            np.inf,
            self._splat,
            doppler_shift_threshold,
        )
        self.write(str(pd))


def make_app():
    return tornado.web.Application(
        [
            (r"/bistatic_range", BistaticRangeHandler),
            (r"/bistatic_doppler", BistaticDopplerHandler),
            (r"/rad_detection", RadDetectionHandler),
        ]
    )


if __name__ == "__main__":
    app = make_app()
    app.listen(UTIL_SERVER_PORT)
    tornado.ioloop.IOLoop.current().start()
