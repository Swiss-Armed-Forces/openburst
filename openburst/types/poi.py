"""Module for POI"""

class POI:
    """Class POI"""
    def __init__(self, id_nr, name, team, lat, lon):
        self.id_nr = id_nr
        name = name.replace("<br>", "")
        self.name = name
        self.team = team
        self.lat = lat
        self.lon = lon


def to_poi_params(dct):
    """returns a POI object instantiation"""
    return POI(dct["id"], dct["name"], "unknown", dct["lat"], dct["lon"])
