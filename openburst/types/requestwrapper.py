""" Module for request wrapping """

class RequestWrapper(object):
    """ Class for handling request wrapping """
    def __init__(self, request_type, nbr_args, args):
        self.request_type = request_type
        self.nbr_args = nbr_args
        self.args = args

def to_request(dct):
    """ returns an object of RequestWrapper"""
    return RequestWrapper(dct["request_type"], dct["nbr_args"], dct["args"])
