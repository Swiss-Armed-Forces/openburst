"use strict";

var ret_message_saved_for_debugging;
var passiveRxArrayBACKUP;
var passiveTxArrayBACKUP;
var heatmap_for_Rxs = [];
var testibus;

function updateHeightOfRx(lat, lon, worker) {
  console.log("----querying to update Rx height: ", lat, lon);
  worker.postMessage([6200903, lat, lon, 0, 0]); // ask for the terrain height
}

function updateHeightOfRxReturn(terrain_mid_point_height) {
  if (terrain_mid_point_height != -1) {
    updatePassSensorArrayFromTable();
    last_sensor = passiveRxArray[passiveRxArray.length - 1];
    last_sensor.masl = terrain_mid_point_height;
    // Update Rx height
    last_row = document.getElementById("passive_sensor_table").rows.length;
    var data = document.getElementById("passive_sensor_table").rows[
      last_row - 1
    ].cells;
    updateTableDataFromPassSensor(data, last_sensor);
  } else {
    timeout_ms = 5000;
    console.log(
      "---- received '-1' as Receiver height (masl), meaning something went wrong. Will retry to get the receiver height after" +
        timeout_ms +
        " ms"
    );
    console.log("passiveSendRequest.js : last_sensor = ", last_sensor);
    setTimeout(function () {
      // will wait for time specified by timeout_ms until executing code below
      updateHeightOfRx(last_sensor.lat, last_sensor.lon, last_sensor.name);
    }, timeout_ms);
  }
}

function findTxForRx(passive_worker) {
  loadGridParams();
  updatePassSensorArrayFromTable();
  var Rx_JSON_arr = returnArrOfJSONsOfRx();

  var also_take_non_LOS_Tx_from_Rx =
    !document.getElementById("Rx_Tx_LOS_req_inp").checked;

  var JSON_str_arr = [Rx_JSON_arr, also_take_non_LOS_Tx_from_Rx];

  var findTxrequest = new request_wrapper();
  findTxrequest.request_type = "findTxForRx_all";
  findTxrequest.nbr_args = 2;
  findTxrequest.args = JSON_str_arr;
  var query = JSON.stringify(findTxrequest);

  passive_worker.postMessage([findTxrequest.request_type, query]); // send query to passive_worker
}

function findTxForRxReturn(ret_msg, map) {
  var Rx_JSON_arr = ret_msg.args[0];
  var Tx_JSON_arr = ret_msg.args[1];

  // delete entries from Rx table
  deleteAllTableEntries("passive_sensor_table");

  // delete Rx array
  passiveRxArray = [];

  // reload the receivers from result, into the array and the table
  for (var i = 0; i < Rx_JSON_arr.length; i++) {
    var receiver_returned = JSON.parse(Rx_JSON_arr[i]);

    // add to Array
    passiveRxArray.push(receiver_returned);

    // add to table
    addPassiveSensorRow();
    var j = i + 2;
    data = document.getElementById("passive_sensor_table").rows[j].cells;
    updateTableDataFromPassSensor(data, receiver_returned);
  }

  // delete entries from Tx table
  deleteAllTableEntries("passive_Tx_table");

  // remove all Tx numbers from map
  for (var i = Tx_circles.length - 1; i >= 0; i--) {
    var layer = Tx_circles[i];
    layer.setRadius(0);
    var dump_ort = ol.proj.fromLonLat([-7, -40]); //
    layer.setCenter(dump_ort); // TBD: this has to be corrected to really remove the circle and not dump it
  }

  // delete Tx Array
  passiveTxArray = [];

  // reload the transmitters from result, into the array and the table
  for (var i = 0; i < Tx_JSON_arr.length; i++) {
    var single_tx = JSON.parse(Tx_JSON_arr[i]);
    // console.log("Tx found at "+single_tx.sitename);
    single_tx.status = 1;

    // add to Array
    passiveTxArray.push(single_tx);

    // add to table
    addTxofOpportRow();
    var j = i + 2;
    var data = document.getElementById("passive_Tx_table").rows[j].cells;
    updateTableDataFromTxOfOpport(data, single_tx);

    // adding Transmitters of Opportunity to map
    addPassiveTxToMap(single_tx, map);
  }
}

function returnArrOfJSONsOfRx() {
  var Rx_JSON_arr = [];
  for (var i = 0; i < passiveRxArray.length; i++) {
    passiveRxArray[i].lostxids = [];
    Rx_JSON_arr.push(JSON.stringify(passiveRxArray[i])); // transforming Rx-object to JSON string
  }
  return Rx_JSON_arr;
}

function returnArrOfJSONsOfActivatedRxTx() {
  var JSON_str_arr_Rx = [];
  for (var i = 0; i < passiveRxArray.length; i++) {
    if (passiveRxArray[i].status == 1) {
      // only add Receiver if it's status is active
      var at_least_one_active_status_Tx = 0;
      for (var j = 0; j < passiveRxArray[i].lostxids.length; j++) {
        var Tx_ID = passiveRxArray[i].lostxids[j];
        var Tx = getPassiveTxById(Tx_ID);
        if (Tx.status == 1) {
          at_least_one_active_status_Tx = 1;
          break;
        }
      }
      if (at_least_one_active_status_Tx == 1) {
        // only add Receiver if it has at least one Transmitter with active status
        JSON_str_arr_Rx.push(JSON.stringify(passiveRxArray[i])); // transforming Rx-object to JSON string
      }
    }
  }
  var JSON_str_arr_Tx = [];
  for (var i = 0; i < passiveTxArray.length; i++) {
    if (passiveTxArray[i].status == 1) {
      // only add Transmitter if it's status is active - might send Tx if respective LOS Receivers are inactive though
      JSON_str_arr_Tx.push(JSON.stringify(passiveTxArray[i])); // transforming Rx-object to JSON string
    }
  }
  return [JSON_str_arr_Rx, JSON_str_arr_Tx];
}

function returnArrOfJSONsOfActivatedRxAndCorrespondingTx() {
  var JSON_str_arr_Rx = [];
  var txCallSigns = "";
  for (var i = 0; i < passiveRxArray.length; i++) {
    console.log("passiveRxArray[i] = ", passiveRxArray[i]);
    if (passiveRxArray[i].status == 1) {
      // only add Receiver if it's status is active
      JSON_str_arr_Rx.push(JSON.stringify(passiveRxArray[i])); // transforming Rx-object to JSON string
      txCallSigns = txCallSigns + ", " + passiveRxArray[i].txcallsigns;
    }
  }
  console.log("txCallSigns  = ", txCallSigns);
  var JSON_str_arr_Tx = [];
  for (var i = 0; i < passiveTxArray.length; i++) {
    // add transmitter if
    if (txCallSigns.includes(passiveTxArray[i].callsign)) {
      // only add Transmitter its callsign is in the list
      JSON_str_arr_Tx.push(JSON.stringify(passiveTxArray[i])); // transforming Rx-object to JSON string
    }
  }
  return [JSON_str_arr_Rx, JSON_str_arr_Tx];
}

function calcMinDetRCS(
  nofRunningCoverages,
  passive_worker,
  radio_prop_enabled,
  radio_prop_params
) {
  console.log("radio_prop_enabled = ", radio_prop_enabled);
  console.log("prop params = ", radio_prop_params);

  if (nofRunningCoverages <= 0) {
    var RCS_grid_params = loadGridParams();

    updateRCSHeightPlotSlider(RCS_grid_params);

    var JSON_RCS_grid_params = JSON.stringify(RCS_grid_params);

    var SNR_thresh = parseFloat(
      document.getElementById("SNR_thresh_inp").value
    );
    var delay_thresh = parseFloat(
      document.getElementById("delay_tresh_inp").value
    );
    var t_max = parseFloat(document.getElementById("t_max_inp").value);

    updatePassSensorArrayFromTable();
    updateTxOfOpportArrayFromTable();

    var tmp = returnArrOfJSONsOfActivatedRxAndCorrespondingTx();
    var JSON_str_arr_Rx = tmp[0];
    var JSON_str_arr_Tx = tmp[1];

    if (JSON_str_arr_Tx.length == 0 || JSON_str_arr_Tx.length == 0) {
      console.log(
        "--- either no Receiver or Transmitter, aborting calculation of coverage"
      );
      return;
    }

    var JSON_str_arr = [
      JSON_str_arr_Rx,
      JSON_str_arr_Tx,
      JSON.stringify(SNR_thresh),
      JSON.stringify(delay_thresh),
      JSON.stringify(t_max),
      JSON_RCS_grid_params,
      JSON.stringify(radio_prop_enabled),
      radio_prop_params,
    ];

    var calcMinDetRCSrequest = new request_wrapper();
    calcMinDetRCSrequest.request_type = "calcMinDetRCScoverage";
    calcMinDetRCSrequest.args = JSON_str_arr;
    calcMinDetRCSrequest.nbr_args = 8;

    var query = JSON.stringify(calcMinDetRCSrequest);
    passive_worker.postMessage([calcMinDetRCSrequest.request_type, query]); // send query to passive_worker

    nofRunningCoverages++;
    passiveRxArrayBACKUP = passiveRxArray;
    passiveTxArrayBACKUP = passiveTxArray;
    alert(
      "Coverage calculation running now, don't do anything (deleting/changing/adding Transmitters/receivers) until it is done (you will be notified again)"
    );
  } else {
    alert("Coverage still running... Please wait until it finishes!");
  }
}

function calcMinDetRCSReturn(ret_msg, nofRunningCoverages) {
  ret_message_saved_for_debugging = ret_msg;
  var heatmaps_json_for_activated_Rx = JSON.parse(ret_msg.args[0]);

  heatmap_for_Rxs = [];

  // delete all checkboxes
  var checkbox_table = document.getElementById(
    "table_for_choosing_Rx_Cov_to_plot"
  );
  while (checkbox_table.firstChild) {
    checkbox_table.removeChild(checkbox_table.firstChild);
  }

  var ind_rx_response = 0; // this has to be used if some Rx are disabled to correctly map the response to the right Rx

  for (var i = 0; i < passiveRxArray.length; i++) {
    if (passiveRxArray[i].status == 1) {
      // only add Receiver if it's status is active
      var at_least_one_active_status_Tx = 0;
      for (var j = 0; j < passiveRxArray[i].lostxids.length; j++) {
        var Tx_ID = passiveRxArray[i].lostxids[j];
        var Tx = getPassiveTxById(Tx_ID);
        if (Tx.status == 1) {
          at_least_one_active_status_Tx = 1;
          break;
        }
      }

      var combined_heatmaps_json =
        heatmaps_json_for_activated_Rx[ind_rx_response];
      ind_rx_response++;
      var combined_heatmap = JSON.parse(combined_heatmaps_json);

      heatmap_for_Rxs.push(combined_heatmap);

      console.log(
        "passiveSendRequests: calcMinDetRCSReturn: combined_heatmap = ",
        combined_heatmap
      );

      var tableRow = document.createElement("tr");
      var td = document.createElement("td");
      var checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = "checked";

      td.appendChild(checkbox);
      tableRow.append(td);

      var td = document.createElement("td");
      td.innerHTML = "Rx ID = " + passiveRxArray[i].rx_id;
      tableRow.append(td);
      checkbox_table.appendChild(tableRow);
    }
  }

  nofRunningCoverages--;
  passiveRxArray = passiveRxArrayBACKUP;
  passiveTxArray = passiveTxArrayBACKUP;
  alert(
    "Coverage calculation finished now, you are allowed to safely work again..."
  );
  return nofRunningCoverages;
}

// is called when button clicked
function plotRCScontours(geoplot_worker) {
  // test which height is the correct one to be plotted (will only plot one height at once)
  var flight_level_to_plot = parseInt(
    document.getElementById("flight_level_to_plot").innerHTML
  );
  var height_start = parseInt(
    document.getElementById("height_start_inp").value
  );
  var height_stop = parseInt(document.getElementById("height_stop_inp").value);
  var height_step = parseInt(document.getElementById("height_step_inp").value);

  var ind = 0;
  var ind_out = -1;
  parseInt(flight_level_to_plot.innerHTML);
  for (
    var height = height_start;
    height <= height_stop;
    height = height + height_step
  ) {
    if (flight_level_to_plot == height) {
      ind_out = ind;
    }
    ind++;
  }
  if (ind_out == -1) {
    alert("plotRCScontours: Something went terribly wrong");
  }

  // tests which of the Receivers are ticked to be plotted:
  var checkbox_table = document.getElementById(
    "table_for_choosing_Rx_Cov_to_plot"
  );
  for (var i = 0; i < checkbox_table.childElementCount; i++) {
    var is_checked = checkbox_table.children[i].children[0].children[0].checked;
    if (is_checked) {
      var RCS_heatmap = heatmap_for_Rxs[i];

      var RCS_heatmap_one_height = [];

      if (RCS_heatmap[0][0].length > 0) {
        // if more than one z-height stored
        var len2 = RCS_heatmap[0].length;

        for (var loop_ind1 = 0; loop_ind1 < RCS_heatmap.length; loop_ind1++) {
          var inner_arr = [];
          for (var loop_ind2 = 0; loop_ind2 < len2; loop_ind2++) {
            inner_arr.push(RCS_heatmap[loop_ind1][loop_ind2][ind_out]);
          }
          RCS_heatmap_one_height.push(inner_arr);
        }
      } else {
        RCS_heatmap_one_height = RCS_heatmap;
      }

      console.log(
        "passiveSendRequests.js: RCS_heatmap_one_height = " +
          RCS_heatmap_one_height
      );

      var RCS_grid_params = loadGridParams();

      var plotRCSgrid_request = new request_wrapper();
      plotRCSgrid_request.request_type = "createKMLforRCSgrid";

      plotRCSgrid_request.nbr_args = 2;
      plotRCSgrid_request.args = [
        JSON.stringify(RCS_grid_params),
        JSON.stringify(RCS_heatmap_one_height),
        JSON.stringify(flight_level_to_plot),
      ];

      var query = JSON.stringify(plotRCSgrid_request);
      // now call the worker to get all the triggers saved on the server
      geoplot_worker.postMessage([plotRCSgrid_request.request_type, query]);
    }
  }
}
