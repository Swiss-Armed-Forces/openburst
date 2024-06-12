class TargetLocation:
    def __init__(
        self,
        object_id,
        ID,
        lat,
        lon,
        terrainHeight,
        flightHeight,
        roll,
        pitch,
        yaw,
        velocity,
        corridor_width,
        corridor_height,
        x,
        y,
        corridor_bearing,
    ):
        self.object_id = object_id
        self.id = ID
        self.lat = lat
        self.lon = lon
        self.terrainHeight = terrainHeight
        self.flightHeight = flightHeight

        self.roll = roll  # in degrees
        self.pitch = pitch  # in degrees
        self.yaw = yaw  # in degrees
        self.velocity = velocity

        self.corridor_width = corridor_width
        # m
        self.corridor_height = corridor_height
        # m

        self.x = x
        self.y = y
        self.corridor_bearing = corridor_bearing




def toTargetLocation(dct):
    return TargetLocation(
        dct["object_id"],
        dct["id"],
        dct["lat"],
        dct["lon"],
        dct["terrainHeight"],
        dct["flightHeight"],
        dct["roll"],
        dct["pitch"],
        dct["yaw"],
        dct["velocity"],
        dct["corridor_width"],
        dct["corridor_height"],
        dct["x"],
        dct["y"],
        dct["corridor_bearing"],
    )
