import math
from oct2py import octave
import time

class Tx:
    def __init__(
        self,
        tx_id,
        callsign,
        sitename,
        lat,
        lon,
        masl,
        ahmagl,
        freq,
        bandwidth,
        erp_h,
        erp_v,
        type_in,
        horiz_diagr_att,
        vert_diagr_att,
        pol,
        signal_type,
        losrxids,
        status=1,
    ):
        self.tx_id = tx_id
        self.callsign = callsign
        self.sitename = sitename
        self.lat = lat
        self.lon = lon
        self.masl = masl  # Terrain height in meter above sea level
        self.ahmagl = ahmagl  # Antenna height in meter above ground level
        self.freq = freq  # frequency in MHz
        self.bandwidth = bandwidth  # bandwidth in kHz
        self.erp_h = erp_h  # ERP in horizontal polarization in dBW
        self.erp_v = erp_v  # ERP in horizontal polarization in dBW
        self.type = type_in  # Should be 'OMNI' or "directional'
        self.horiz_diagr_att = horiz_diagr_att
        self.vert_diagr_att = vert_diagr_att
        self.pol = pol
        self.signal_type = signal_type
        self.losrxids = losrxids
        self.status = status
        if isinstance(self.erp_v, float):
            self.power = self.erp_v
        else:
            self.power = self.erp_h


    def getTxSignalType(self):  # this returns a string FM/DAB/DVB-T for passive radar...which is necessary for SPLAT to compute the path free space and prop losses
        if "FM" in self.signal_type:
            return "FM"
        if "DAB" in self.signal_type:
            return "DAB"
        if "DVB" in self.signal_type:
            return "DVB"
        return ""



    def return_beam_width(self):  # TBD
        if self.type == "OMNI":
            # print("OMNI")
            return 2 * math.pi  # should be possibly inf
        else:
            # print np.where(self.horiz_diagr_att == 0)[0]
            # print("not OMNI")
            "TODO: checkout 'get_mainlobe_heading' of 'findMinRCSwithLOS.py'"
            "TODO"  # hard to calculate beamwidth for cross-range resolution, as often not on main lobe

            return 2 * math.pi

        return 5 * math.pi / 180

    def updatePolToHighest(
        self,
    ):  # Converts the transmitter polarization 'M' (mixed) to 'V' or 'H', depending on which ERP is highest
        if self.pol == "M":
            if self.erp_h > self.erp_v:
                ERP = self.erp_h
                self.pol = "H"
            else:
                ERP = self.erp_v
                self.pol = "V"
        return self

    def returnERP(self):
        ERP = -1
        if self.pol == "H":
            ERP = self.erp_h
        elif self.pol == "V":
            ERP = self.erp_v
        elif self.pol == "M":
            ERP = self.updatePolToHighest().returnERP()
        else:
            pass  # print('undefined polarization')
        return ERP

    def plotHorizDiagrAtt(self, nbr_secs):
        if len(self.horiz_diagr_att) > 0:
            octave.makePolarPlot(
                self.horiz_diagr_att, "ERP reduction for North/East/South/West"
            )
            time.sleep(nbr_secs)
        else:
            pass  # print("no horizontal diagram data available")

    def plotVertDiagrAtt(self, nbr_secs):
        if len(self.vert_diagr_att) > 0:  # plot only if data available
            octave.makePolarPlot(self.vert_diagr_att, "ERP vertical reduction")
            time.sleep(nbr_secs)
        else:
            pass  # print("no vertical diagram data available")

    def radiation_patt_hor(
        self, nbr_secs, plot_unit
    ):  # nbr_secs: how many secs should sleep after plotting, #plot_unit='W' or 'dBW'
        if self.pol == "H":
            ERP = self.erp_h
        elif self.pol == "V":
            ERP = self.erp_v

        if self.type == "OMNI":
            if plot_unit == "W":
                ERP = 10 ** (ERP / 10)  # convert dBW to W
            octave.makePolarPlot(ERP, "Rad pattern for North/East/South/West")
            time.sleep(nbr_secs)

        elif self.type == "directional":
            if (self.horiz_diagr_att) > 0:  # plot only if data available
                if plot_unit == "dBW":
                    pow_dBW = [ERP - x for x in self.horiz_diagr_att]
                    octave.makePolarPlot(
                        pow_dBW,
                        "Rad pattern for North/East/South/West [" + plot_unit + "]",
                    )
                elif plot_unit == "W":
                    pow_W = [10 ** ((ERP - x) / 10) for x in self.horiz_diagr_att]
                    octave.makePolarPlot(
                        pow_W,
                        "Rad pattern for North/East/South/West [" + plot_unit + "]",
                    )
                time.sleep(nbr_secs)



def to_Tx(dct):
    #print("tx dct = ", dct)
    return Tx(
        dct["tx_id"],
        dct["callsign"],
        dct["sitename"],
        dct["lat"],
        dct["lon"],
        dct["masl"],
        dct["ahmagl"],
        dct["freq"],
        dct["bandwidth"],
        dct["erp_h"],
        dct["erp_v"],
        dct["type"],
        dct["horiz_diagr_att"],
        dct["vert_diagr_att"],
        dct["pol"],
        dct["signal_type"],
        dct["losrxids"],
        dct["status"],
    )


def findTxByIdLooper(Tx_all, Tx_ID):
    there_is_Tx = -1
    for where_is_Tx in range(len(Tx_all)):
        if Tx_all[where_is_Tx].tx_id == Tx_ID:
            there_is_Tx = where_is_Tx
            return Tx_all[there_is_Tx], True
    if there_is_Tx == -1:
        #     print "---------- This LOS-transmitter (ID=%s) has not been found (most probably deactivated)" %Tx_ID
        return None, False


def findTxByCallsign(Tx_all, Tx_callsign):
    for tx_nbr in range(len(Tx_all)):
        tx = Tx_all[tx_nbr]
        if tx.callsign == Tx_callsign:
            return tx, True
    return None, False


def findTxById(
    Tx_all, Tx_ID
):  # Looking for where the Tx is - with which the current Rx has LOS
    if Tx_ID < len(Tx_all):  # faster query: if no Tx ID is missing in Tx_all array
        if Tx_all[Tx_ID].tx_id == Tx_ID:
            return Tx_all[Tx_ID], True
        else:
            return findTxByIdLooper(
                Tx_all, Tx_ID
            )  # slower query: linear search for where Tx_ID is within Tx_all
    else:
        return findTxByIdLooper(Tx_all, Tx_ID)  # COuld also do this in reverse order