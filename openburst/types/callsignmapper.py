"""Module providing a class for call sign mapping"""

class CallsignMapper(dict):
    """Class for callsign mapping"""
    def add_if_not_incl(self, key, value):
        """function for adding key if not already added"""
        if self[key] == -1:  # if missing key: add it
            self[key] = value
        
        return self[key]
    
    def __missing__(self, key):
        # if missing key
        return -1

    def is_included(self, key):
        """function for checking if key is used"""
        if self[key] == -1:
            return False
        else:
            return True