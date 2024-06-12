function Sim() {
  // use closure to avoid global variables to avoid memory leak in browser

  //------------ OBJECT IDS for communication with the sim server
  var SIM_DATA_CAPTURE_QUERY_ID = 196;
  var SIM_START_QUERY_ID = 1;
  var SIM_STOP_QUERY_ID = 0;

  // get the waypoints and set this as the target trajectory
  this.captureData = function () {
    document.getElementById("green-led").className = "led-green";
    if (targetArray.length < 1) {
      alert("Please enter atleast one target before capturing.");
      return;
    }
    if (activeMonostaticArray.length < 1) {
      alert("Please input atleast one sensor before capturing");
      return;
    }

    // reset the target circles array
    for (var i = 0, l = targetCircleArray.length; i < l; i++) {
      map.removeLayer(targetCircleArray[i].markerLayer);
    }
    targetCircleArray = [];

    // reset the time analysis
    resetTimeAnalysis();

    // update target array from table
    updateTargetArrayFromTable();

    // update the sensor array from the html
    updateSensorArrayFromTable();

    // update waypoints
    updateWaypointsArrayFromTable();

    // update POI
    updatePOIfromTable();

    // update trigger array
    updateTriggerArrayFromTable();

    // set the object Id, QUERY_ID for capture, and target parameters
    var data_capture_msg = JSON.stringify([
      { object_id: SIM_DATA_CAPTURE_QUERY_ID },
    ]);

    updateTargetCirclesArray(); // update the target circles

    // -------------------------include threat
    // targets
    var msg_json_threat_1 = stringifyTarget(targetArray);
    // 3d waypoints
    var msg_json_threat_2 = JSON.stringify(three_d_waypoints_array, [
      "object_id",
      "id",
      "name",
      "poi_name",
      "agl_asl",
      "targetLocationArray",
      "lat",
      "lon",
      "terrainHeight",
      "flightHeight",
    ]);
    // include the poi
    var msg_json_threat_3 = JSON.stringify(poi, [
      "object_id",
      "name",
      "lat",
      "lon",
    ]);
    msg_json_threat_3 = "[" + msg_json_threat_3 + "]";

    // triggers
    var msg_json_threat_4 = JSON.stringify(triggerArray, [
      "object_id",
      "name",
      "id",
      "source_target_id",
      "dest_target_id",
      "dist_to_poi",
      "poi_name",
    ]);

    // --------------------------include assets
    // active sensors
    var msg_json_assets_1 = stringifySensor(activeMonostaticArray);

    // concatenate all json strings
    var total_msg_json = [
      data_capture_msg,
      msg_json_threat_1,
      msg_json_threat_2,
      msg_json_threat_3,
      msg_json_threat_4,
      msg_json_assets_1,
      msg_json_assets_2,
    ];

    // now call the worker
    targ_sim_worker.postMessage(total_msg_json);

    document.getElementById("start_targ_sim").disabled = false;
    document.getElementById("stop_targ_sim").disabled = true;
    document.getElementById("capture_waypoints").disabled = true;
  };

  // start the simulation of a target
  function startTargetSimulation() {
    document.getElementById("red-led").className = "led-red";
    document.getElementById("green-led").className = "";

    var msg_json = JSON.stringify([{ object_id: SIM_START_QUERY_ID }]);
    var total_msg_json = [msg_json];
    //console.log("launching targ_sim_worker with: ", total_msg_json);
    targ_sim_worker.postMessage(total_msg_json);
    document.getElementById("capture_waypoints").disabled = true;
    document.getElementById("stop_targ_sim").disabled = false;
    document.getElementById("start_targ_sim").disabled = true;

    simulationRunning = true;
  }
  // stop the simulation of a target
  function stopTargetSimulation() {
    document.getElementById("red-led").className = "";

    var msg_json = JSON.stringify([{ object_id: SIM_STOP_QUERY_ID }]);
    var total_msg_json = [msg_json];

    targ_sim_worker.postMessage(total_msg_json);
    document.getElementById("start_targ_sim").disabled = true;
    document.getElementById("capture_waypoints").disabled = false;
    simulationRunning = false;
  }
}
