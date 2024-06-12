"""Module for PET sensors"""

class PetSensor:
    """Class for PET sensors"""
    def __init__(self, pet_id, status, lat, lon, threshold, terrain_height):
        self.id_nr = pet_id
        self.status = status
        self.lat = lat
        self.lon = lon
        self.threshold = threshold
        self.height = terrain_height

    def __str__(self):  # printing function
        return "<PET id:%s lat:%s lon:%s height:%s>" % (
            self.id_nr,
            self.lat,
            self.lon,
            self.height,
        )

def to_pet(dct):
    """returns a PET sensor instantiation"""
    return PetSensor(
        dct["id_nr"],
        dct["status"],
        dct["lat"],
        dct["lon"],
        dct["threshold"],
        dct["height"],
    )
