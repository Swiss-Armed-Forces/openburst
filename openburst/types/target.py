import re

class Target:
    def __init__(
        self,
        id_nr,
        team,
        rcs,
        name,
        running,
        velocity,
        lat,
        lon,
        height,
        vx,
        vy,
        vz,
        corridor_breadth,
        noftargets,
        typed,
        threeD_waypoints_id,
        status,
        maneuvring,
        classification,
        rec_time,
        update_time=-1,
    ):
        # make sure id_nr is an integer
        if isinstance(id_nr, int):
            self.id_nr = id_nr
        else:
            self.id_nr = int(
                re.sub("\D", "", str(id_nr))
            )  # remove all characters except digits

        self.team = team
        self.rcs = rcs
        name = name.replace("<br>", "")
        self.name = name
        self.running = running
        self.velocity = velocity  # [m/s]
        self.lat = lat
        self.lon = lon
        self.height = height
        self.vx = vx  # [m/s] on lon axis
        self.vy = vy  # [m/s] on lat axis
        self.vz = vz  # [m/s] on Z axis
        if self.vx is None:
            self.vx = 0
        if self.vy is None:
            self.vy = 0
        if self.vz is None:
            self.vz = 0
        self.corridor_breadth = corridor_breadth
        self.nofTargets = noftargets
        self.typed = typed
        self.threeD_waypoints_id = threeD_waypoints_id
        self.status = status
        self.maneuvring = maneuvring
        self.classification = classification
        self.waypoints = []
        self.waypoints_index = -1
        self.update_time = update_time
        # this will be the current simulation time
        self.recording_time = rec_time
        # this will the time as in the recording file
        self.terrainHeight = -1

    def __str__(self):
        return (
            "<Target id:%s vel:%s rcs:%s corridor_breadth:%s waypoints_name:%s team:%s running:%s status:%s terrainHeight:%s>"
            % (
                self.id_nr,
                self.velocity,
                self.rcs,
                self.corridor_breadth,
                self.threeD_waypoints_id,
                self.team,
                self.running,
                self.status,
                self.terrainHeight,
            )
        )


def to_target_params(dct):
    return Target(
        dct["id"],
        "team-unknown",
        dct["rcs"],
        dct["name"],
        dct["running"],
        dct["velocity"],
        -1,
        -1,
        -1,
        0,
        0,
        0,
        dct["corridor_breadth"],
        dct["noftargets"],
        dct["type"],
        dct["threeD_waypoints_id"],
        dct["status"],
        dct["maneuvring"],
        "unknown",
        -1,
        -1,
    )

