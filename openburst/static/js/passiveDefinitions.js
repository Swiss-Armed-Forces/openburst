"use strict";

var passiveRxArray = []; // will contain all the passive sensors placed by the user
var passiveTxArray = []; // will contain all the transmitters placed by the user

// Transmitter
function Tx() {
  this.tx_id = -1;
  this.callsign = "UNDEFINED";
  this.sitename = "UNDEFINED";
  this.status = 0;
  this.x = 0;
  this.y = 0;
  this.lat = 0;
  this.lon = 0;
  this.masl = 0; // Terrain height in meter above sea level
  this.ahmagl = 0; // antenna height in meter Above Ground Level
  this.freq = 0; // frequency in MHz
  this.bandwidth = 0; // bandwidth in kHz

  this.erp_h = "UNDEFINED";
  this.erp_v = "UNDEFINED";

  this.type = "UNDEFINED"; // Should be 'OMNI' or "directional'
  this.horiz_diagr_att = [];
  this.vert_diagr_att = [];

  this.pol = "UNDEFINED";
  this.signal_type = "UNDEFINED"; // should be 'DAB', 'DVB' or
  this.losrxids = [];
}

function calcRadPattH(Tx, pol) {
  var ERP;
  if (pol == "H") {
    if (Tx.erp_h == -1) {
      alert("sth went wrong erp_h is undefined (-1)!");
    }
    ERP = Tx.erp_h;
  } else if (pol == "V") {
    if (Tx.erp_v == -1) {
      alert("sth went wrong erp_v is undefined (-1)!");
    }
    ERP = Tx.erp_v;
  } else if (ERP == "M") {
    alert("dont give 'calcRadPattH' function the value 'M'");
  }

  return Tx.horiz_diagr_att.map(function (value) {
    return ERP - value;
  });
}

this.calcRadPattV = function () {
  // DOES NOT DO ANYTHING:
  // radiation pattern in vertical direction for either polarization can not be shown on plot
};

var Tx_mapping_ind = {
  tx_id: 0,
  callsign: 1,
  sitename: 2,
  "status[0/1]": 3,
  x: 4,
  y: 5,
  lat: 4,
  lon: 5,
  masl: 6,
  ahmagl: 7,
  signal_type: 8,
  "Freq[MHz]": 9,
  "BW[kHz]": 10,
  polarization: 11,
  type: 12,
  erp_h: 13,
  erp_v: 14,
  "horizontal attenuation": 15,
  "vertical attenuation": 16,
  "horizintal rad pattern": 17,
  "vertical rad pattern": 18,
  losrxids: 19,
  "Category[0=ground/1=airborne]": 20,
};

var Rx_mapping_ind = {
  rx_id: 0,
  name: 1,
  "status[0/1]": 2,
  x: 3,
  y: 4,
  lat: 5,
  lon: 6,
  masl: 7,
  ahmagl: 8,
  signal_type: 9,
  bandwidth: 10,
  horiz_diagr_att: 11,
  vert_diagr_att: 12,
  gain: 13,
  losses: 14,
  temp_sys: 15,
  limit_distance: 16,
  lostxids: 17,
  txcallsigns: 18,
};

// Receiver or passive sensors
function Rx() {
  this.name = "";
  this.rx_id = -1;
  this.x = 0;
  this.y = 0;
  this.masl = 0; // Terrain height in meter above sea level
  this.lat = 0;
  this.lon = 0;
  this.ahmagl = 15; // antenna height in meter Above Ground Level
  this.signal_type = "FM"; // should be one of the signal_type definitions in pcl server module subpackage
  this.limit_distance = 50000;
  this.lostxids = [];
  this.status = 1;
  this.txcallsigns = "";
  this.bandwidth = 8000; // kHz
  this.horiz_diagr_att = 0; // horizontal attenuation diagram
  this.vert_diagr_att = 0; //"";   	// vertical attenuation diagram , 0 for no attenuation, string for half-wave dipole atten., comma separated values for real atten. diagr
  this.gain = 0; // antenna gain in dB
  this.losses = 0; // losses: antenna to receiver input
  this.temp_sys = 300; // Receiving System noise temperature in K

  this.findTxInRange = function () {
    return this.color + " " + this.type + " apple";
  };
}

function getPassiveTxById(tx_id) {
  // TODO?
  return passiveTxArray[tx_id];
}

function passTarget() {
  // TODO: include
  this.x = 0;
  this.y = 0;
  this.masl = 0;
  // Maximal coherent integration time: rule of thumb:
  // sqrt(1/(transmitter.freq*A_r)), A_r: radial component of target acceleration/bistatic acceleration
  this.t_max = 1; // in s, maximal coherence/integration time
  this.roll = 0; // in degrees
  this.pitch = 0; // in degrees
  this.yaw = 0; // in degrees
  this.heading = 0;
}

// This request_wrapper is intended to handle data to the python server
function request_wrapper() {
  this.request_type = "NONE";
  this.nbr_args = 0;
  this.args = [];
}

// grid_params are some parameters which define where and how the passive coverage should be calculated
function grid_params() {
  this.lat_start = 47.15; // from bottom left corner point
  this.lat_stop = 47.52; // from top right corner point
  this.lon_start = 8.3; // from bottom left corner point
  this.lon_stop = 9; // from top right corner point
  this.min_x = -1; // Swissgrid
  this.max_x = -1; // Swissgrid
  this.min_y = -1; // Swissgrid
  this.max_y = -1; // Swissgrid
  this.min_z = -1; // masl
  this.max_z = -1; // masl
  this.res_z = 0; // tag 0 or put very high value if you don't wan to distinguish between height levels
  this.amt_pts_x = 100;
  this.amt_pts_y = 100;
  this.amt_pts_z = 1;
  this.res_x = -1; // meter
  this.res_y = -1; // meter

  // this function will make sure that the bounds of the lat and lon's are properly set (start<stop) and height_start < height_max
  this.adapt_bounds = function () {
    if (this.lat_start > this.lat_stop) {
      var tmp = this.lat_start;
      this.lat_start = this.lat_stop;
      this.lat_stop = tmp;
    }

    if (this.lon_start > this.lon_stop) {
      tmp = this.lon_start;
      this.lon_start = this.lon_stop;
      this.lon_stop = tmp;
    }

    if (this.height_start > this.height_stop) {
      tmp = this.height_start;
      this.height_start = this.height_stop;
      this.height_stop = tmp;
    }
    return this;
  };
}
