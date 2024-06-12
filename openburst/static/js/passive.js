//(function() { // use closure to avoid global variables to avoid memory leak in browser
// closure cannot be used as we have to call functions in this script from other scripts
// (e.g. app.js calls addNewPassiveRx

"use strict";
var Rx_circles = [];
var Tx_circles = [];
var rad_patt_layers = [];
var running_pass_sens_id = 0;
var layer_vector_lines = [];
var RCS_heatmap_layers = [];
var global_RCS_heat_map;

// this function will delete all entries in the table specified by
// table_id (e.g. "passive_Tx_table" or "passive_sensor_table")
function deleteAllTableEntries(table_id) {
  for (var i = document.getElementById(table_id).rows.length - 1; i > 1; i--) {
    document.getElementById(table_id).deleteRow(i);
  }
}

// This function adds a new row in the TxOfOpportunity Table
function addTxofOpportRow() {
  var $TABLE = $("#passive_Tx_table_div");

  var $clone = $TABLE
    .find("tr.hide")
    .clone(true)
    .removeClass("hide table-line");
  $TABLE.find("table").append($clone);
}

//This function adds a new row in the Passive Rx Table
function addPassiveSensorRow() {
  var $TABLE = $("#passive_sensor_table_div");

  var $clone = $TABLE
    .find("tr.hide")
    .clone(true)
    .removeClass("hide table-line");
  $TABLE.find("table").append($clone);

  var x = document.getElementById("passive_sensor_table").rows.length;
  var data = document.getElementById("passive_sensor_table").rows[x - 1].cells;
}

function loadSingleDiagrAttenFromTable(td_innerText) {
  var diagr_att, tmp2;
  if (td_innerText.indexOf(",") != -1) {
    // if has a comma: create array
    diagr_att = [];
    splitted_string = td_innerText.split(",");
    for (var k = 0; k < splitted_string.length; k++) {
      diagr_att[k] = parseFloat(splitted_string[k]);
    }
  } else {
    // no comma
    tmp2 = parseFloat(td_innerText);
    if (isNaN(tmp2)) {
      // is string?
      diagr_att = td_innerText;
    } else {
      // is number
      diagr_att = tmp2;
    }
  }
  return diagr_att;
}

function updatePassSensorTxCallSignsOnTable(
  lat,
  lon,
  signal_type,
  txcallsigns
) {
  for (
    var i = 2, l = document.getElementById("passive_sensor_table").rows.length;
    i < l;
    i++
  ) {
    var data = document.getElementById("passive_sensor_table").rows[i].cells;
    var curr_name = data[1].innerHTML;
    var curr_lat = parseFloat(data[5].innerHTML);
    var curr_lon = parseFloat(data[6].innerHTML);
    var curr_sig_type = data[9].innerHTML;
    var curr_status = parseInt(data[2].innerHTML);
    if (lat == curr_lat && lon == curr_lon && signal_type == curr_sig_type) {
      data[Rx_mapping_ind["txcallsigns"]].innerHTML = txcallsigns;
    }
  }
}

function updatePassSensorArrayFromTable() {
  for (
    var i = 2, l = document.getElementById("passive_sensor_table").rows.length;
    i < l;
    i++
  ) {
    var data = document.getElementById("passive_sensor_table").rows[i].cells;
    var curr_id = parseInt(data[0].innerHTML);

    console.log(
      "updatePassSensorArrayFromTable: rows = ",
      document.getElementById("active_sensor_table").rows.length,
      ", i = ",
      i,
      ", current rx_id = ",
      parseInt(data[0].innerHTML),
      ", ",
      data[1].innerHTML,
      ", txcallsigns = ",
      String(data[Rx_mapping_ind["txcallsigns"]].innerHTML),
      ", status = ",
      parseInt(data[Rx_mapping_ind["status[0/1]"]].innerHTML)
    );

    var j = i - 2;

    passiveRxArray[j].rx_id = parseInt(data[Rx_mapping_ind["rx_id"]].innerHTML);
    passiveRxArray[j].name = String(data[Rx_mapping_ind["name"]].innerHTML);
    console.log(
      "=**********************Rx initial name length : ",
      passiveRxArray[j].name.length
    );
    if (passiveRxArray[j].name.length == 0) {
      passiveRxArray[j].name = "PCL_SENSOR_" + j.toString();
      console.log(
        "======================================= Rx name set to : ",
        passiveRxArray[j].name
      );
    }
    passiveRxArray[j].status = parseInt(
      data[Rx_mapping_ind["status[0/1]"]].innerHTML
    );
    passiveRxArray[j].x = parseFloat(data[Rx_mapping_ind["x"]].innerHTML);
    passiveRxArray[j].y = parseFloat(data[Rx_mapping_ind["y"]].innerHTML);
    passiveRxArray[j].lat = parseFloat(data[Rx_mapping_ind["lat"]].innerHTML);
    passiveRxArray[j].lon = parseFloat(data[Rx_mapping_ind["lon"]].innerHTML);
    passiveRxArray[j].masl = parseFloat(data[Rx_mapping_ind["masl"]].innerHTML);
    passiveRxArray[j].ahmagl = parseFloat(
      data[Rx_mapping_ind["ahmagl"]].innerHTML
    );
    passiveRxArray[j].txcallsigns = String(
      data[Rx_mapping_ind["txcallsigns"]].innerHTML
    ).replace("<br>", "");

    var tmp = String(data[Rx_mapping_ind["signal_type"]].innerHTML);
    var tmp2 = tmp.indexOf("<"); // To remove </br> when enter was pressed
    if (tmp2 != -1) {
      tmp = tmp.substr(0, tmp2);
    }
    passiveRxArray[j].signal_type = String(tmp);

    passiveRxArray[j].bandwidth = parseFloat(
      data[Rx_mapping_ind["bandwidth"]].innerHTML
    );

    passiveRxArray[j].horiz_diagr_att = loadSingleDiagrAttenFromTable(
      data[Rx_mapping_ind["horiz_diagr_att"]].innerText
    );
    passiveRxArray[j].vert_diagr_att = loadSingleDiagrAttenFromTable(
      data[Rx_mapping_ind["vert_diagr_att"]].innerText
    );

    passiveRxArray[j].gain = parseFloat(data[Rx_mapping_ind["gain"]].innerHTML);
    passiveRxArray[j].losses = parseFloat(
      data[Rx_mapping_ind["losses"]].innerHTML
    );
    passiveRxArray[j].temp_sys = parseFloat(
      data[Rx_mapping_ind["temp_sys"]].innerHTML
    );
    passiveRxArray[j].limit_distance = parseInt(
      data[Rx_mapping_ind["limit_distance"]].innerHTML
    );
    if (data[Rx_mapping_ind["lostxids"]].innerHTML == "") {
      passiveRxArray[j].lostxids = [];
    } else {
    }
  }
  console.log(
    "DONE updatePassSensorArrayFromTable: passiveRxArray=",
    passiveRxArray
  );
}

// This functions updates a single table entry from a single passive Sensor
function updateTableDataFromPassSensor(data, Rx) {
  // The following will return keys:	Object.keys(Rx_mapping_ind)
  data[Rx_mapping_ind["rx_id"]].innerHTML = Rx.rx_id;
  data[Rx_mapping_ind["name"]].innerHTML = Rx.name;
  data[Rx_mapping_ind["status[0/1]"]].innerHTML = Rx.status;
  data[Rx_mapping_ind["x"]].innerHTML = Rx.x;
  data[Rx_mapping_ind["y"]].innerHTML = Rx.y;
  data[Rx_mapping_ind["lat"]].innerHTML = Rx.lat;
  data[Rx_mapping_ind["lon"]].innerHTML = Rx.lon;
  data[Rx_mapping_ind["masl"]].innerHTML = Rx.masl;
  data[Rx_mapping_ind["ahmagl"]].innerHTML = Rx.ahmagl;
  data[Rx_mapping_ind["signal_type"]].innerHTML = Rx.signal_type;
  data[Rx_mapping_ind["bandwidth"]].innerHTML = Rx.bandwidth;
  data[Rx_mapping_ind["horiz_diagr_att"]].innerHTML = Rx.horiz_diagr_att;
  data[Rx_mapping_ind["vert_diagr_att"]].innerHTML = Rx.vert_diagr_att;
  data[Rx_mapping_ind["gain"]].innerHTML = Rx.gain;
  data[Rx_mapping_ind["losses"]].innerHTML = Rx.losses;
  data[Rx_mapping_ind["temp_sys"]].innerHTML = Rx.temp_sys;
  data[Rx_mapping_ind["limit_distance"]].innerHTML = Rx.limit_distance;
  data[Rx_mapping_ind["txcallsigns"]].innerHTML = Rx.txcallsigns;
}

// This functions updates a single table entry from a single passive ToO
function updateTableDataFromTxOfOpport(data, Tx) {
  data[Tx_mapping_ind["tx_id"]].innerHTML = Tx.tx_id;
  data[Tx_mapping_ind["callsign"]].innerHTML = Tx.callsign;
  data[Tx_mapping_ind["sitename"]].innerHTML = Tx.sitename;
  data[Tx_mapping_ind["status[0/1]"]].innerHTML = Tx.status;
  data[Tx_mapping_ind["lat"]].innerHTML = Tx.lat;
  data[Tx_mapping_ind["lon"]].innerHTML = Tx.lon;
  data[Tx_mapping_ind["masl"]].innerHTML = Tx.masl;
  data[Tx_mapping_ind["ahmagl"]].innerHTML = Tx.ahmagl;
  data[Tx_mapping_ind["signal_type"]].innerHTML = Tx.signal_type;
  data[Tx_mapping_ind["Freq[MHz]"]].innerHTML = Tx.freq;
  data[Tx_mapping_ind["BW[kHz]"]].innerHTML = Tx.bandwidth;
  data[Tx_mapping_ind["polarization"]].innerHTML = Tx.pol;
  data[Tx_mapping_ind["type"]].innerHTML = Tx.type;
  data[Tx_mapping_ind["erp_h"]].innerHTML = Tx.erp_h;
  data[Tx_mapping_ind["erp_v"]].innerHTML = Tx.erp_v;
  data[Tx_mapping_ind["horizontal attenuation"]].innerHTML = Tx.horiz_diagr_att;
  data[Tx_mapping_ind["vertical attenuation"]].innerHTML = Tx.vert_diagr_att;
  data[Tx_mapping_ind["losrxids"]].innerHTML = Tx.losrxids;
}

//This functions rewrites the Transmitter of Opport Array from the HTML5 table
function updateTxOfOpportArrayFromTable() {
  for (
    var i = 2, l = document.getElementById("passive_Tx_table").rows.length;
    i < l;
    i++
  ) {
    var data = document.getElementById("passive_Tx_table").rows[i].cells;
    // loop through the array as below
    for (var j = 0; j < passiveTxArray.length; j++) {
      if (passiveTxArray[j].callsign == data[1].innerHTML) {
        passiveTxArray[j].status = parseInt(
          data[Tx_mapping_ind["status[0/1]"]].innerHTML
        );
      }
    }
  }
}

// converts string attenuation array to float attenuation array
function parseStringArrayToFloatArray(strarr) {
  if (strarr == "UNDEFINED") {
    return strarr;
  }
  var arr_string = strarr.split(",");
  var arr = [];
  for (var k = 0; k < arr_string.length; k++) {
    arr.push(parseFloat(arr_string[k]));
  }
  return arr;
}

function addNewPassiveTxFromDB(data, map) {
  var tx = new Tx();
  var x = document.getElementById("passive_Tx_table").rows.length;
  tx.tx_id = data.tx_id;
  tx.callsign = data.callsign;
  tx.sitename = data.sitename;
  tx.status = data.status;
  tx.x = 0;
  tx.y = 0;
  tx.lat = data.lat;
  tx.lon = data.lon;
  tx.masl = data.masl; // Terrain height in meter above sea level
  tx.ahmagl = data.ahmagl; // antenna height in meter Above Ground Level
  tx.freq = data.freq; // frequency in MHz
  tx.bandwidth = data.bandwidth; // bandwidth in kHz

  if (data.erp_h != "-1") {
    tx.erp_h = data.erp_h;
  } else {
    tx.erp_h = "UNDEFINED";
  }
  if (data.erp_v != "-1") {
    tx.erp_v = data.erp_v;
  } else {
    tx.erp_v = "UNDEFINED";
  }

  tx.type = "directional";
  var tmp1 = data.horiz_diagr_att.replace(/{|}/gi, "");
  tx.horiz_diagr_att = parseStringArrayToFloatArray(tmp1);
  var tmp2 = data.vert_diagr_att.replace(/{|}/gi, "");
  tx.vert_diagr_att = parseStringArrayToFloatArray(tmp2);

  tx.pol = data.pol;
  tx.signal_type = data.signal_type;
  tx.losrxids = [];

  passiveTxArray.push(tx);

  // add to table
  addTxofOpportRow();
  var datad = document.getElementById("passive_Tx_table").rows[x - 1].cells; //
  updateTableDataFromTxOfOpport(datad, tx);

  // adding Transmitters of Opportunity to map
  addPassiveTxToMap(tx, map);
}

// This function adds a new passive Rx from data received from DB
function addNewPassiveRxFromDB(data, map) {
  //
  var SensorID = running_pass_sens_id;
  running_pass_sens_id += 1;
  var curr_ort = ol.proj.fromLonLat([data.lon, data.lat]);
  var circle_Rx = new ol.geom.Circle(
    ol.proj.transform([1.5, 5.5], "EPSG:4326", "EPSG:3857"),
    200
  );
  var circleFeatureRx = new ol.Feature(circle_Rx);

  var radarFeatureOverlay = new ol.FeatureOverlay({
    map: map,
    features: [circleFeatureRx],
    style: new ol.style.Style({
      fill: new ol.style.Fill({
        color: "rgba(220, 200, 150, 0.3)",
      }),
      stroke: new ol.style.Stroke({
        //
        width: 4,
        color: "rgba(255,150,102, 0.8)",
      }),
      text: new ol.style.Text({
        text: SensorID.toString(),
        scale: 1.3,
        fill: new ol.style.Fill({
          color: "rgba(255,150,102, 0.8)",
        }),
        stroke: new ol.style.Stroke({
          color: "#FFFF99",
          width: 3.5,
        }),
      }),
    }),
  });
  circle_Rx.setCenter(curr_ort);

  // write the ID of the sensor above it
  Rx_circles.push(circle_Rx);
  // add empty row to sensor table
  addPassiveSensorRow();
  // set some receiver values
  var sensor = new Rx();
  sensor.lat = data.lat;
  sensor.lon = data.lon;
  sensor.masl = data.masl;
  sensor.name = data.name;
  sensor.status = data.status;
  sensor.signal_type = data.signal_type;
  sensor.bandwidth = data.bandwidth;
  sensor.horiz_diagr_att = data.horiz_diagr_att;
  sensor.vert_diagr_att = data.vert_diagr_att;
  sensor.gain = data.gain;
  sensor.losses = data.losses;
  sensor.temp_sys = data.temp_sys;
  sensor.limit_distance = data.limit_distance;
  sensor.txcallsigns = data.txcallsigns;
  sensor.ahmagl = data.ahmagl;

  sensor.rx_id = SensorID;

  // write the receiver data to the array
  passiveRxArray.push(sensor);

  var last_row = document.getElementById("passive_sensor_table").rows.length;
  var datad = document.getElementById("passive_sensor_table").rows[last_row - 1]
    .cells;

  // write the receiver data to the table
  updateTableDataFromPassSensor(datad, sensor);
}

// This function adds a new passive Rx:   this happens if alt+shift+ left clicking on a map
function addNewPassiveRx(c_lat, c_lon, map, terrain_mid_point_height) {
  var curr_ort = ol.proj.fromLonLat([c_lon, c_lat]);

  var SensorID = running_pass_sens_id; //passiveRxArray.length
  running_pass_sens_id += 1;

  var circle_Rx = new ol.geom.Circle(
    ol.proj.transform([1.5, 5.5], "EPSG:4326", "EPSG:3857"),
    200
  );
  var circleFeatureRx = new ol.Feature(circle_Rx);

  var radarFeatureOverlay = new ol.FeatureOverlay({
    map: map,
    features: [circleFeatureRx],
    style: new ol.style.Style({
      fill: new ol.style.Fill({
        color: "rgba(220, 200, 150, 0.3)",
      }),
      stroke: new ol.style.Stroke({
        //
        width: 4,
        color: "rgba(255,150,102, 0.8)",
      }),
      text: new ol.style.Text({
        text: SensorID.toString(),
        scale: 1.3,
        fill: new ol.style.Fill({
          color: "rgba(255,150,102, 0.8)",
        }),
        stroke: new ol.style.Stroke({
          color: "#FFFF99",
          width: 3.5,
        }),
      }),
    }),
  });
  circle_Rx.setCenter(curr_ort);

  // write the ID of the sensor above it
  Rx_circles.push(circle_Rx);

  // add empty row to sensor table
  addPassiveSensorRow();

  // set some receiver values
  var sensor = new Rx();
  sensor.lat = c_lat;
  sensor.lon = c_lon;
  sensor.masl = terrain_mid_point_height;
  sensor.name = name;

  sensor.rx_id = SensorID;

  // write the receiver data to the array
  passiveRxArray.push(sensor);

  var last_row = document.getElementById("passive_sensor_table").rows.length;
  var data = document.getElementById("passive_sensor_table").rows[last_row - 1]
    .cells;

  // write the receiver data to the table
  updateTableDataFromPassSensor(data, sensor);
}

function addPassiveTxToMap(Tx, map) {
  var curr_ort = ol.proj.fromLonLat([Tx.lon, Tx.lat]);
  var txid = Tx.tx_id;
  console.log("Tx = ", Tx);
  var pow = "";
  if (Tx.erp_h.toString() == "UNDEFINED") {
    pow = Tx.erp_v.toFixed(0).toString();
  } else {
    pow = Tx.erp_h.toFixed(0).toString();
  }

  var circle_Tx = new ol.geom.Circle(
    ol.proj.transform([1.5, 5.5], "EPSG:4326", "EPSG:3857"),
    200
  );
  var circleFeatureTx = new ol.Feature(circle_Tx);
  var TxOverlay = new ol.FeatureOverlay({
    map: map,
    features: [circleFeatureTx],
    style: new ol.style.Style({
      fill: new ol.style.Fill({
        color: "rgba(255,20,0, 0.8)",
      }),
      stroke: new ol.style.Stroke({
        //
        width: 4,
        color: "rgba(255,250,202, 0.8)",
      }),
      text: new ol.style.Text({
        text: Tx.tx_id.toString() + "-" + pow,
        scale: 1.3,
        fill: new ol.style.Fill({
          color: "rgba(255, 255, 255, 1.0)",
        }),
        stroke: new ol.style.Stroke({
          color: "#FF2222",
          width: 3.5,
        }),
      }),
    }),
  });
  circle_Tx.setCenter(curr_ort);

  Tx_circles.push(circle_Tx);
}

function removeAllTxRadPatternsOnMap(map) {
  if (rad_patt_layers.length > 0) {
    for (var i = 0; i < rad_patt_layers.length; i++) {
      map.removeLayer(rad_patt_layers.splice(i, 1)[0]);
    }
  }
}

function plotTxRadPatternOnMap(map) {
  var rad_pattern, Tx_single;
  // need to remove all layers independent of which Tx there are currently set
  removeAllTxRadPatternsOnMap(map);
  updateTxOfOpportArrayFromTable();

  for (var Tx_nbr = 0; Tx_nbr < passiveTxArray.length; Tx_nbr++) {
    Tx_single = passiveTxArray[Tx_nbr];
    if (Tx_single.status == 0) {
      continue;
    }
    if (Tx_single.type == "directional") {
      if (Tx_single.pol == "V" || Tx_single.pol == "H") {
        rad_pattern = calcRadPattH(Tx_single, Tx_single.pol);
      } else {
        //alert("this polarization type has not yet been implemented for directional antenna type");
        continue;
      }
    } else if (Tx_single.type == "OMNI") {
      //alert("this transmitter type has not yet been implemented");
      continue;
    } else {
      //alert("this transmitter type has not yet been implemented");
      continue;
    }

    var polygon_vertices = [];
    var dBW = 1; // TODO: not sure if dBW==0 works
    var scaling_fact_pattern = 100;
    var scaling_offs_pattern = -Math.min(Math.min.apply(null, rad_pattern), 0); // this is to prevent negative dBWs to be plotted in the wrong direction
    for (var i = 0; i < rad_pattern.length; i++) {
      var x_easting;
      var y_northing;
      if (dBW == 1) {
        y_northing =
          Math.cos((2 * Math.PI * i) / rad_pattern.length) *
          (rad_pattern[i] + scaling_offs_pattern) *
          scaling_fact_pattern;
        x_easting =
          Math.sin((2 * Math.PI * i) / rad_pattern.length) *
          (rad_pattern[i] + scaling_offs_pattern) *
          scaling_fact_pattern;
      } else {
        y_northing =
          (Math.cos((2 * Math.PI * i) / rad_pattern.length) * 10) ^
          ((rad_pattern[i] / 10) * scaling_fact_pattern);
        x_easting =
          (Math.sin((2 * Math.PI * i) / rad_pattern.length) * 10) ^
          ((rad_pattern[i] / 10) * scaling_fact_pattern);
      }

      var coord = ol.proj.transform(
        [Tx_single.lon, Tx_single.lat],
        "EPSG:4326",
        "EPSG:3857"
      );
      x_easting += coord[0];
      y_northing += coord[1];
      polygon_vertices.push([x_easting, y_northing]);
    }
    polygon_vertices.push(polygon_vertices[0]);

    var polygon = new ol.geom.Polygon([polygon_vertices]);
    //// Create feature with polygon.
    var feature = new ol.Feature(polygon);

    var layer = new ol.layer.Vector({
      source: new ol.source.Vector({
        features: [feature],
      }),
    });

    rad_patt_layers.push(layer);
    map.addLayer(layer);
  }
}

function removePassSensor($row) {
  var rx_id = $row.text().split("\n")[1].trim();

  console.log("removing passive sensor with rx_id: ", rx_id);

  // now go through the array and remove the feature
  var ind = -1;
  for (var i = 0, l = passiveRxArray.length; i < l; i++) {
    if (parseInt(passiveRxArray[i].rx_id) == rx_id) {
      var layer = Rx_circles.splice(i, 1);
      layer = layer[0];
      layer.setRadius(0);
      var dump_ort = ol.proj.fromLonLat([-7, -40]);
      layer.setCenter(dump_ort); // TBD: this has to be corrected to really remove the circle and not dump it
      ind = i;

      break;
    }
  }
  if (ind > -1) {
    passiveRxArray.splice(ind, 1);
  }
}

function removeAllLinesBetwAllRxAndTx(map) {
  if (layer_vector_lines.length > 0) {
    for (var i = 0; i < layer_vector_lines.length; i++) {
      map.removeLayer(layer_vector_lines.splice(i, 1)[0]);
    }
  }
}

function drawLinesBetwAllActiveRxAndTx(map) {
  removeAllLinesBetwAllRxAndTx(map);

  updateTxOfOpportArrayFromTable();
  updatePassSensorArrayFromTable();

  for (var i = 0; i < passiveRxArray.length; i++) {
    var receiver = passiveRxArray[i];
    if (receiver.status == 1) {
      drawLinesBetwRxAndTx(receiver, map);
    }
  }
}

function drawLinesBetwRxAndTx(receiver, map) {
  // only draws for Tx which have status==1
  var Rx_point = ol.proj.transform(
    [receiver.lon, receiver.lat],
    "EPSG:4326",
    "EPSG:3857"
  );
  var vector = new ol.source.Vector();
  var cnt = 0;
  if (isNaN(parseInt(receiver.lostxids))) {
    return; // skip receiver, as no valid lostxids
  }
  for (var i = 0; i < receiver.lostxids.length; i++) {
    var tx_id = receiver.lostxids[i];
    var trans = passiveTxArray[tx_id];
    if (trans.status == 1) {
      cnt = cnt + 1;
      var Tx_point = ol.proj.transform(
        [trans.lon, trans.lat],
        "EPSG:4326",
        "EPSG:3857"
      );
      var line = new ol.geom.LineString([Rx_point, Tx_point]);
      vector.addFeatures([new ol.Feature(line)]);
    }
  }
  if (cnt > 0) {
    var layer = new ol.layer.Vector({
      source: vector,
    });
    map.addLayer(layer);
    layer_vector_lines.push(layer);
    console.log(
      "adding " + cnt + " LOS lines for receiver rx_id: " + receiver.rx_id
    );
  }
}

function removeRCSHeatMapLayers(map) {
  // remove previous layers
  while (RCS_heatmap_layers.length > 0) {
    map.removeLayer(RCS_heatmap_layers.splice(i, 1)[0]);
  }
}

function change_flight_level_slider() {
  var slider = document.getElementById("flight_level_slider_inp");
  var flight_level_to_plot = document.getElementById("flight_level_to_plot");
  flight_level_to_plot.innerHTML = slider.value;
}

function setStatusAllTx(status) {
  for (
    var i = 2, l = document.getElementById("passive_Tx_table").rows.length;
    i < l;
    i++
  ) {
    var data = document.getElementById("passive_Tx_table").rows[i].cells;
    var j = i - 2;

    // set status in table
    data[Tx_mapping_ind["status[0/1]"]].innerHTML = status;

    // set status in passiveTxArray
    passiveTxArray[j].status = parseInt(
      data[Tx_mapping_ind["status[0/1]"]].innerHTML
    );
  }
}

function loadGridParams() {
  var RCS_grid_params = new grid_params();
  RCS_grid_params.lat_start = parseFloat(
    document.getElementById("lat_start_inp").value
  );
  RCS_grid_params.lat_stop = parseFloat(
    document.getElementById("lat_stop_inp").value
  );
  RCS_grid_params.lon_start = parseFloat(
    document.getElementById("lon_start_inp").value
  );
  RCS_grid_params.lon_stop = parseFloat(
    document.getElementById("lon_stop_inp").value
  );
  RCS_grid_params.amt_pts_x = parseInt(
    document.getElementById("nbr_x_pts_inp").value
  );
  RCS_grid_params.amt_pts_y = parseInt(
    document.getElementById("nbr_y_pts_inp").value
  );
  RCS_grid_params.min_z = parseInt(
    document.getElementById("height_start_inp").value
  );
  RCS_grid_params.max_z = parseInt(
    document.getElementById("height_stop_inp").value
  );
  RCS_grid_params.res_z = parseInt(
    document.getElementById("height_step_inp").value
  );
  RCS_grid_params = RCS_grid_params.adapt_bounds();

  RCS_grid_params.min_x = RCS_grid_params.lon_start;
  RCS_grid_params.min_y = RCS_grid_params.lat_start;

  RCS_grid_params.max_x = RCS_grid_params.lon_stop;
  RCS_grid_params.max_y = RCS_grid_params.lat_stop;

  RCS_grid_params.res_x =
    (RCS_grid_params.max_x - RCS_grid_params.min_x) /
    (RCS_grid_params.amt_pts_x - 1);
  RCS_grid_params.res_y =
    (RCS_grid_params.max_y - RCS_grid_params.min_y) /
    (RCS_grid_params.amt_pts_y - 1);

  // Calc how many levels will be used in z-direction, and what the new maximum will be
  if (
    RCS_grid_params.res_z == 0 ||
    RCS_grid_params.max_z - RCS_grid_params.min_z < RCS_grid_params.res_z
  ) {
    // Catch division by zero and empty array
    RCS_grid_params.amt_pts_z = 1;
    RCS_grid_params.max_z = RCS_grid_params.min_z;
  } else {
    RCS_grid_params.amt_pts_z =
      Math.floor(
        (RCS_grid_params.max_z - RCS_grid_params.min_z) / RCS_grid_params.res_z
      ) + 1;
    RCS_grid_params.max_z =
      RCS_grid_params.min_z +
      (RCS_grid_params.amt_pts_z - 1) * RCS_grid_params.res_z;
  }

  document.getElementById("height_stop_inp").value = RCS_grid_params.max_z;
  document.getElementById("res_x_outp").innerHTML = RCS_grid_params.res_x;
  document.getElementById("res_y_outp").innerHTML = RCS_grid_params.res_y;
  document.getElementById("amt_z_pts_outp").innerHTML =
    RCS_grid_params.amt_pts_z;

  return RCS_grid_params;
}

function updateRCSHeightPlotSlider(RCS_grid_params) {
  var slider = document.getElementById("flight_level_slider_inp");
  slider.min = RCS_grid_params.min_z;
  slider.max = RCS_grid_params.max_z;
  slider.step = RCS_grid_params.res_z;
  change_flight_level_slider();
}

var layers_tracks = [];

function addTrackLayer(url_in) {
  var vector = new ol.layer.Vector({
    source: new ol.source.Vector({
      url: url_in,
      format: new ol.format.KML(),
    }),
  });
  map.addLayer(vector);

  layers_tracks.push(vector);
}

function removeTrackLayers() {
  while (layers_tracks.length > 0) {
    map.removeLayer(layers_tracks.splice(i, 1)[0]);
  }
}
