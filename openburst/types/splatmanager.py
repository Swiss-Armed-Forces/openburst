"""
This manages the integration with Splat! propagation modelling library and boost
"""
from multiprocessing.managers import (
    BaseManager,
)  # to share the SPLAT object between all processes

import scipy.constants as sc
from openburst.functions import basefunctions
from openburst.constants import splatconstants

basefunctions.set_openburst_linked_lib_path()
basefunctions.set_openburst_system_path()
import libsplathd as splat



# one instance of this class will be shared
class SharedSPLAT():
    """
    Class for sharing a splat object
    """
    def __init__(self, min_lat=44, max_lat=50, min_lon=348, max_lon=357):
        self.min_lat = min_lat  
        self.max_lat = max_lat  
        self.min_lon = min_lon  
        self.max_lon = max_lon  

        self.p_site = splat.prop_site()
        self.p_site.initialize_heavy(
            self.min_lat,
            self.max_lat,
            self.min_lon,
            self.max_lon,
            splatconstants.DIEL_CONST,
            splatconstants.EARTH_COND,
            splatconstants.AT_BEND,
            splatconstants.RADIO_CLIMATE,
            splatconstants.POL,
            splatconstants.FRAC_OF_SITU,
            splatconstants.FRAC_OF_TIME,
            splatconstants.GROUND_CLUTTER,
        )

    def getRawLosAndLoss(
        self,
        src_lat,
        src_lon,
        src_h,
        dst_lat,
        dst_lon,
        dst_h,
        freq,
        masl,
        justLos,
        rev_dir,
    ):
        """ returns a query for LoS and propagation loss between two locations """
        ret = self.p_site.getLosAndLoss(
            src_lat,
            360.0 - src_lon,
            src_h / sc.foot,
            dst_lat,
            360.0 - dst_lon,
            dst_h / sc.foot,
            freq,
            masl,
            justLos,
            rev_dir,
        )
        # returns:
        # LOS[0/1], PROP_LOSS[dB], FREE_SPACE_LOSS[dB], dist[m], source_elev[masl], dest_elev[masl], p_to_pdist[m], first_fresnel_zone_free
        return (ret[0], ret[1], ret[2], ret[3], ret[4], ret[5], ret[0], ret[6], ret[7])

    def getLosAndLossProxy(
        self,
        src_lat,
        src_lon,
        src_h,
        dst_lat,
        dst_lon,
        dst_h,
        freq,
        masl,
        justLos,
        rev_dir,
    ):
        """ proxy for LoS and propagation loss between two locations, for not calculating Loss if not queried """
        ret = self.p_site.getLosAndLoss(
            src_lat,
            360.0 - src_lon,
            src_h / sc.foot,
            dst_lat,
            360.0 - dst_lon,
            dst_h / sc.foot,
            freq,
            masl,
            justLos,
            rev_dir,
        )
        # std::vector<float> ret_b { ret.los, ret.propagation_path_loss, ret.free_space_loss, ret.surface_distance, ret.source_elevation, ret.dest_elevation, ret.point_to_point_distance, ret.first_fresnel_zone_clear};
        #print(" los, propagation_path_loss, free_space_loss, surface_distance, source_elevation, dest_elevation, point_to_point_distance, first_fresnel_zone_clear")
        #print(ret[0], ret[1], ret[2], ret[3], ret[4], ret[5], ret[6], ret[7])
        if justLos == 1:
            return (ret[0], ret[3])  # return los and dist
        
        total_loss = ret[2]
        if ret[1] > ret[2]:
            total_loss = ret[1]
        return (
            ret[0],
            ret[6],
            total_loss,
        )  # return los and dist and total_loss (prop and free space and atmospheric attenuatation)

    def testBoundaries(self, lat, lon):
        """ test max boundaries WGS84 """
        if (
            (lat < self.min_lat)
            or (lat > self.max_lat)
            or (lon > (360.0 - self.min_lon))
            or (lon < (360.0 - self.max_lon))
        ):
            return 0.0
        else:
            return 1.0

    def get_elevation(self, lat, lon):
        """ returns elevation masl for lat/lon"""
        ret = self.p_site.getElevationAtLocWithoutLoadingDEM(lat, 360.0 - lon)
        return ret


class StateManager(BaseManager):
    pass

# register our class to be maintained by the managers (one shared memory splat for pcl-online, pcl-coverage and rad-online)
StateManager.register("pclrunnersplat", SharedSPLAT)
StateManager.register("pclcoveragesplat", SharedSPLAT)
StateManager.register("radrunnersplat", SharedSPLAT)

