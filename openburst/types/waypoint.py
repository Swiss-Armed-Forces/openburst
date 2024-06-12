
class Waypoint:
    def __init__(self, id_nr, name, team, agl_asl):
        self.id_nr = id_nr
        name = name.replace("<br>", "")
        self.name = name
        self.team = team
        self.agl_asl = agl_asl
        self.waypoints = []

    def __str__(self):  # printing function
        return "<Waypoint id:%s, waypoints:%s >" % (self.id_nr, self.waypoints)


def to_waypoint_params(dct):
    return Waypoint(dct["id"], dct["name"], "unknown", dct["agl_asl"])