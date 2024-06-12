function getRandomInt(min, max) {
  min = Math.ceil(min);
  max = Math.floor(max);
  return Math.floor(Math.random() * (max - min)) + min;
}

(function () {
  // use closure to avoid global variables (otherwise memory leak in browser)

  var activeMonostaticArray = []; // wil contain all the active sensors placed by the user

  var petArray = []; // wil contain all the PET sensors placed by the user

  ("use strict");

  //var sim_container, stats;

  var curr_lat;
  var curr_lon;

  var terrain_mid_point_height;

  //---------------important interdependent values for DEM resolution and slippy map tiles
  var slippy_zoom = 17; //17
  var elem_width = 200; //200 // 100 for slippy_zoom = 18, 500 for slippy_zoom = 16 // simple width of elem in the simulation
  var plane_width_meters = 200; // 200 // 100 for slippy_zoom = 18, 450 for slippy_zoom=16, this is width and height of ONE mesh in meter, should be divisible by  25: see graha_wsh.py function getDEM (where pixelWidth = 25), this should also be divisible by elem_max_res
  //------------------------------------------

  var mid_tile_x = -1;
  var mid_tile_y = -1;

  var anz_x = 40; // this has to be copied into pdf_Worker.js (as workers do not see this)
  var anz_y = anz_x; // this has to be copied into pdf_Worker.js (as workers do not see this)

  var runningSensorID = getRandomInt(500, 600);
  var runningTargetID = getRandomInt(0, 500);
  var runningWaypId = getRandomInt(0, 9999999);
  var runningTriggersId = getRandomInt(0, 9999999);
  var running_poi_id = getRandomInt(700, 800);
  var runningRoadBlockID = getRandomInt(700, 800);

  var currentActiveTargetID = -1;

  var tmpLayersArray = [];

  var poi_mesh, poi;

  var worker,
    geoplot_worker,
    pdf_worker,
    sensor_control_worker,
    detection_sim_worker,
    passive_worker,
    replay_worker,
    pet_worker,
    radioprop_worker;

  var geoplot_layers = [];
  var geoplot_track_layers = []; // this will be a 2D array

  var sim = new Sim();
  var waypoint = new Waypoint();

  var nofWorkersLaunched = 0;
  var nofRunningCoverages = 0;
  var bern = ol.proj.fromLonLat([10.3, 46.7]);

  var view;
  var map;
  var heatMapLayer;

  var sensorAnimationSource;

  var dataNr = 0; // for space charts

  // the following variables say if the reference track ID and the test track IDs are unicode (=1) or not (=0)
  // they will be changed according to browser check box
  var test_track_id_is_unicode = 0;
  var ref_track_id_is_unicode = 1;

  // html5 local data storage: to store scenarios
  //see: https://jsfiddle.net/james2doyle/jC9ms/

  // for replay of reference tgts
  var RUN_REPLAY = false;
  var ref_replay_vectorSource = new ol.source.Vector({
    features: [],
  });
  var ref_replay_vector = new ol.layer.Vector({
    source: ref_replay_vectorSource,
  });

  // for replay of test tgts
  var test_replay_vectorSource = new ol.source.Vector({
    features: [],
  });
  var test_replay_vector = new ol.layer.Vector({
    source: test_replay_vectorSource,
  });

  // for live blue targets (i.e. not replay, but user defined)
  var live_blue_target_vectorSource = new ol.source.Vector({
    features: [],
  });
  var live_blue_target_vector = new ol.layer.Vector({
    source: live_blue_target_vectorSource,
  });
  // for live red targets (i.e. not replay, but user defined)
  var live_red_target_vectorSource = new ol.source.Vector({
    features: [],
  });
  var live_red_target_vector = new ol.layer.Vector({
    source: live_red_target_vectorSource,
  });

  //----------------------------------POP UP--------------------------------------
  // Elements that make up the popup.
  var popup_container = document.getElementById("popup");
  var popup_content = document.getElementById("popup-content");
  var popup_closer = document.getElementById("popup-closer");

  /**
   * Add a click handler to hide the popup.
   * @return {boolean} Don't follow the href.
   */
  popup_closer.onclick = function () {
    popup_overlay.setPosition(undefined);
    popup_closer.blur();
    return false;
  };
  /**
   * Create an overlay to anchor the popup to the map.
   */
  var popup_overlay = new ol.Overlay({
    element: popup_container,
  });

  function existsTarg(id) {
    for (var i = 0, l = targetArray.length; i < l; i++) {
      if (targetArray[i].id == id) {
        return i;
      }
    }
    return null;
  }

  // this will be called whenever the PCL or the Team tabs are selected
  function updatePCLRxTxCallsigns() {
    updatePassSensorArrayFromTable();
    updateTxOfOpportArrayFromTable();
    //console.log("updatePCLRxTxCallsigns called!!!")
    // update the txcallsigns ////
    var tmp1 = returnArrOfJSONsOfActivatedRxTx();
    var tmp2 = returnArrOfJSONsOfActivatedRxAndCorrespondingTx();
    var JSON_str_arr_Rx = tmp2[0];
    var JSON_str_arr_Tx = tmp1[1];
    console.log("updatePCLRxTxCallsigns; Txs = ", JSON_str_arr_Tx);
    console.log("updatePCLRxTxCallsigns; Rxs = ", JSON_str_arr_Rx);
    callsigns_str = "";
    for (var i = 0, l = JSON_str_arr_Tx.length; i < l; i++) {
      var res = JSON.parse(JSON_str_arr_Tx[i]);
      if (res.status == 1) {
        //console.log("tx callsign = ", res.callsign)//////
        if (i > 0) {
          callsigns_str = callsigns_str + "," + res.callsign;
        } else {
          callsigns_str = res.callsign;
        }
      }
    }

    // now find the Rx with the status = 1 and set the callsigns
    for (var i = 0, l = JSON_str_arr_Rx.length; i < l; i++) {
      var res = JSON.parse(JSON_str_arr_Rx[i]);
      if (res.status == 1) {
        passiveRxArray[i].txcallsigns = callsigns_str;
        // now update table from array
        updatePassSensorTxCallSignsOnTable(
          res.lat,
          res.lon,
          res.signal_type,
          callsigns_str
        );
      }
    }
  }

  function existsDetection(targ_id, sensor_id) {
    for (var i = 0, l = detectionArray.length; i < l; i++) {
      if (
        detectionArray[i].targ_id == targ_id &&
        detectionArray[i].sensor_id == sensor_id
      ) {
        return i;
      }
    }
    return null;
  }

  function existsRad(id) {
    for (var i = 0, l = activeMonostaticArray.length; i < l; i++) {
      if (activeMonostaticArray[i].id_nr == id) {
        return i;
      }
    }
    return null;
  }

  function checkAddRad(data, action) {
    if (data.status == "1") {
      var rad_id = parseInt(data.id_nr);
      var ind = existsRad(rad_id);

      if (ind != null) {
        activeMonostaticArray[ind].lat = data.lat;
        activeMonostaticArray[ind].lon = data.lon;
        activeMonostaticArray[ind].power = data.power;
        activeMonostaticArray[ind].antenna_diam = data.antenna_diam;
        activeMonostaticArray[ind].freq = data.freq;
        activeMonostaticArray[ind].pulse_width = data.pulse_width;
        activeMonostaticArray[ind].cpi_pulses = data.cpi_pulses;
        activeMonostaticArray[ind].bandwidth = data.bandwidth;
        activeMonostaticArray[ind].pfa = data.pfa;
        activeMonostaticArray[ind].rotation_time = data.rotation_time;
        activeMonostaticArray[ind].category = data.category;
        activeMonostaticArray[ind].name = data.name;
        activeMonostaticArray[ind].status = data.status;

        activeMonostaticArray[ind].min_elevation = data.min_elevation;
        activeMonostaticArray[ind].max_elevation = data.max_elevation;
        activeMonostaticArray[ind].orientation = data.orientation;
        activeMonostaticArray[ind].horiz_aperture = data.horiz_aperture;
        activeMonostaticArray[ind].min_detection_range =
          data.min_detection_range;
        activeMonostaticArray[ind].max_detection_range =
          data.max_detection_range;
        activeMonostaticArray[ind].min_detection_height =
          data.min_detection_height;
        activeMonostaticArray[ind].max_detection_height =
          data.max_detection_height;
        activeMonostaticArray[ind].min_detection_tgt_speed =
          data.min_detection_tgt_speed;
        activeMonostaticArray[ind].max_detection_tgt_speed =
          data.max_detection_tgt_speed;

        updateTableFromRadArray(ind);
      } else {
        addRadRowWithID(data.id_nr);
        // update the radar array
        var curr_ort = ol.proj.fromLonLat([data.lon, data.lat]);
        var radar_circle = getRadarCircle(curr_ort, data.id_nr);
        var sensor = new ActiveMonostaticSensor(
          sim.ACTIVE_MONOSTATIC_SENSOR_PARAM_ID,
          parseInt(data.id_nr),
          "",
          data.lat,
          data.lon,
          radar_circle
        );

        sensor.lat = data.lat;
        sensor.lon = data.lon;
        sensor.power = data.power;
        sensor.antenna_diam = data.antenna_diam;
        sensor.freq = data.freq;
        sensor.pulse_width = data.pulse_width;
        sensor.cpi_pulses = data.cpi_pulses;
        sensor.bandwidth = data.bandwidth;
        sensor.pfa = data.pfa;
        sensor.rotation_time = data.rotation_time;
        sensor.category = data.category;
        sensor.name = data.name;
        sensor.status = data.status;

        sensor.min_elevation = data.min_elevation;
        sensor.max_elevation = data.max_elevation;
        sensor.orientation = data.orientation;
        sensor.horiz_aperture = data.horiz_aperture;
        sensor.min_detection_range = data.min_detection_range;
        sensor.max_detection_range = data.max_detection_range;
        sensor.min_detection_height = data.min_detection_height;
        sensor.max_detection_height = data.max_detection_height;
        sensor.min_detection_tgt_speed = data.min_detection_tgt_speed;
        sensor.max_detection_tgt_speed = data.max_detection_tgt_speed;

        activeMonostaticArray.push(sensor);

        var ind = existsRad(sensor.id_nr);
        updateTableFromRadArray(ind);

        initTimeAnalysis();

        var sens_arr = [];
        for (var i = 0, l = activeMonostaticArray.length; i < l; i++) {
          sens_arr.push(activeMonostaticArray[i].id_nr.toString());
        }
      }
    }

    // update the DB table with radar if not in table!! //
    var rowCount = document.getElementById("db_table").rows.length;
    var isknown = 0;
    while (rowCount > 1) {
      var dd = document.getElementById("db_table").rows[rowCount - 1].cells;
      if (dd[0].innerHTML == data.id_nr && dd[2].innerHTML == data.name) {
        isknown = 1;
      }
      rowCount = rowCount - 1;
    }
    if (isknown == 0) {
      $("#db_table tbody").append(
        "<tr> <td /><td /><td /><td /><td /><td /> <td /> </tr >"
      );
      var x = document.getElementById("db_table").rows.length;
      var datad = document.getElementById("db_table").rows[x - 1].cells;
      datad[0].innerHTML = data.id_nr;
      datad[1].innerHTML = "RAD";
      datad[2].innerHTML = data.name;
      datad[3].innerHTML = data.lat;
      datad[4].innerHTML = data.lon;
      datad[5].innerHTML = data.freq;
      datad[6].innerHTML = data.status;
    } else {
      // update the known RAD
      var datad = document.getElementById("db_table").rows[rowCount].cells;
      datad[0].innerHTML = data.id_nr;
      datad[1].innerHTML = "RAD";
      datad[2].innerHTML = data.name;
      datad[3].innerHTML = data.lat;
      datad[4].innerHTML = data.lon;
      datad[5].innerHTML = data.freq;
      datad[6].innerHTML = data.status;
    }
  }

  function checkAddTarget(targ_id, data) {
    console.log("got to add target: ", data);
    var ind = existsTarg(targ_id);
    if (ind != null) {
      targetArray[ind].rcs = parseFloat(data.rcs);
      targetArray[ind].name = data.name;
      targetArray[ind].running = parseInt(data.running); // 0= not running, 1 = running
      targetArray[ind].velocity = parseFloat(data.velocity);
      targetArray[ind].corridor_breadth = parseInt(data.corridor_breadth);
      targetArray[ind].noftargets = parseInt(data.noftargets);
      targetArray[ind].type = data.typed;
      targetArray[ind].threeD_waypoints_id = parseInt(data.threed_waypoints_id);
      targetArray[ind].status = parseInt(data.status); // dead = 0/ alive = 1/
      targetArray[ind].maneuvring = parseInt(data.maneuvring);
      targetArray[ind].lat = parseFloat(data.lat);
      targetArray[ind].lon = parseFloat(data.lon);
      targetArray[ind].height = parseFloat(data.height);
      targetArray[ind].terrainHeight = parseFloat(data.terrainHeight);
    } else {
      addTargetRowWithID(targ_id);
      // update the target array
      var target = new Target(
        sim.TARGET_PARAM_ID,
        parseInt(targ_id),
        parseFloat(data.rcs),
        data.name,
        parseInt(data.running),
        parseFloat(data.velocity),
        parseInt(data.corridor_breadth),
        parseInt(data.noftargets),
        data.typed,
        parseInt(data.threed_waypoints_id),
        1.0,
        parseInt(data.maneuvring)
      );
      targetArray.push(target);
    }
  }

  function detection_sim_worker_listener(data) {
    var res = JSON.parse(data);
    if (res.request_type == "db_update") {
      var action = res.action;
      var table = res.table;
      var node = res.node;
      var fdata = res.data;
    }
  }

  function displayLiveTargets(targ_coordinates, tgt_type) {
    if (tgt_type == 1) {
      // blue targets
      var colorr = "rgba(0, 0, 220, 0.3)";
    } else {
      var colorr = "rgba(220, 0, 0, 0.3)";
    }

    var featureCount = targ_coordinates.length;
    var features = new Array(featureCount);
    var feature, geometry, coord;

    for (i = 0; i < featureCount; ++i) {
      var curr_ort = ol.proj.fromLonLat([
        targ_coordinates[i].lon,
        targ_coordinates[i].lat,
      ]);
      var resolution = map.getView().getResolution();
      var units = map.getView().getProjection().getUnits();
      var dpi = 25.4 / 0.28;
      var mpu = ol.proj.METERS_PER_UNIT[units];
      var scale = resolution * mpu * 39.37 * dpi;
      var divScale = 400; // to adjusting
      var radius = scale / divScale;

      geometry = new ol.geom.Circle(curr_ort, radius); //

      feature = new ol.Feature(geometry);

      feature.setStyle(
        new ol.style.Style({
          fill: new ol.style.Fill({
            color: colorr,
          }),
          stroke: new ol.style.Stroke({
            width: 2,
            color: colorr,
          }),
          radius: radius,
          text: new ol.style.Text({
            text: targ_coordinates[i].id,
            scale: 1.0,
            fill: new ol.style.Fill({
              color: "rgba(255, 255, 255, 1.0)",
            }),
            stroke: new ol.style.Stroke({
              color: "rgba(255, 255, 255, 1.0)",
              width: 1.5,
            }),
          }),
        })
      );

      features[i] = feature;
    }

    if (tgt_type == 1) {
      // reference targets
      live_blue_target_vectorSource.clear();
      live_blue_target_vectorSource.addFeatures(features);
      map.addLayer(live_blue_target_vector);
    }
    if (tgt_type == 0) {
      live_red_target_vectorSource.clear();
      live_red_target_vectorSource.addFeatures(features);
      map.addLayer(live_red_target_vector);
    }
  }

  function displayReplayTargets(targ_coordinates, tgt_type) {
    if (tgt_type == 1) {
      // reference targets
      var colorr = "rgba(0, 0, 220, 0.3)";
    } else {
      var colorr = "rgba(220, 0, 0, 0.3)";
    }

    var featureCount = targ_coordinates.length;
    var features = new Array(featureCount);
    var feature, geometry, coord;

    for (i = 0; i < featureCount; ++i) {
      var curr_ort = ol.proj.fromLonLat([
        targ_coordinates[i].lon,
        targ_coordinates[i].lat,
      ]);
      var resolution = map.getView().getResolution();
      var units = map.getView().getProjection().getUnits();
      var dpi = 25.4 / 0.28;
      var mpu = ol.proj.METERS_PER_UNIT[units];
      var scale = resolution * mpu * 39.37 * dpi;
      var divScale = 400; // to adjusting
      var radius = scale / divScale;

      geometry = new ol.geom.Circle(curr_ort, radius); //

      feature = new ol.Feature(geometry);
      id = targ_coordinates[i].id.toString();
      if (id.length > 3) {
        id = id.substr(3);
      }

      feature.setStyle(
        new ol.style.Style({
          fill: new ol.style.Fill({
            color: colorr,
          }),
          stroke: new ol.style.Stroke({
            width: 2,
            color: colorr,
          }),
          radius: radius,
          text: new ol.style.Text({
            text: id.substr(id.length - 3),
            scale: 1.0,
            fill: new ol.style.Fill({
              color: "rgba(255, 255, 255, 1.0)",
            }),
            stroke: new ol.style.Stroke({
              color: "rgba(255, 255, 255, 1.0)",
              width: 1.5,
            }),
          }),
        })
      );

      features[i] = feature;
    }

    if (tgt_type == 1) {
      // reference targets
      map.removeLayer(ref_replay_vector);
      ref_replay_vectorSource.clear();
      ref_replay_vectorSource.addFeatures(features);
      map.addLayer(ref_replay_vector);
    }
    if (tgt_type == 0) {
      map.removeLayer(test_replay_vector);
      test_replay_vectorSource.clear();
      test_replay_vectorSource.addFeatures(features);
      map.addLayer(test_replay_vector);
    }
  }

  function sensor_control_worker_listener(data) {
    var res = JSON.parse(data);

    // this is the new method (April 2019) for replay of targets, where the worker does most of the work
    if (res.request_type == "REF_TGT_UPDATE" && RUN_REPLAY == true) {
      //
      tracks = res.data;
      if (tracks.length > 0) {
        displayReplayTargets(tracks, 1);
      }
      return;
    }
    // this is the new method (April 2019) for replay of targets, where the worker does most of the work
    if (res.request_type == "TEST_TGT_UPDATE" && RUN_REPLAY == true) {
      tracks = res.data;
      if (tracks.length > 0) {
        displayReplayTargets(tracks, 0);
      }
      return;
    }

    if (res.request_type == "LIVE_BLUE_TGT_UPDATE") {
      // this is a live blue target (not replay)

      tracks = res.data;
      map.removeLayer(live_blue_target_vector);
      if (tracks.length > 0) {
        for (var i = 0; i < tracks.length; i++) {
          targ_id = tracks[i].id;
          displayLiveTargets(tracks, 1);
          checkAddTarget(targ_id, tracks[i]);
        }
      }
      return;
    }

    if (res.request_type == "LIVE_RED_TGT_UPDATE") {
      tracks = res.data;
      map.removeLayer(live_red_target_vector);
      if (tracks.length > 0) {
        displayLiveTargets(tracks, 0);
      }
      return;
    }

    if (res == "OPEN" && node == "gbad") {
      ignore_rad();
      ignoreTARGETS();
    } else if (res.request_type == "db_update_pcl_rx_tx") {
      // this is a pcl rx or tx update

      changes = res.args[0];
      var action = changes.action;
      var table = changes.table;

      // -------------------------DB UPDATED RAD----------------------------------------
      if (action == "UPDATE" && table == "blue_live_pcl_rx") {
        console.log(
          "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%   updating pcl_rx....: ",
          changes.data
        );
        // insert to TABLE //
        addNewPassiveRxFromDB(changes.data, map);
      }
      if (action == "UPDATE" && table == "blue_live_pcl_tx") {
        console.log(
          "::::::::::::::::::::::::::::::::::::::::::: updating pcl_tx....: ",
          changes.data
        );
        addNewPassiveTxFromDB(changes.data, map);
      }
    } else if (res.request_type == "db_update") {
      // the data bank changed
      changes = res.args[0];
      var action = changes.action;
      var table = changes.table;
      // -------------------------DB UPDATED RAD----------------------------------------
      if (action == "UPDATE" && table == "blue_live_rad") {
        console.log("updating rad....");
        checkAddRad(changes.data, action);
      }
      if (action == "INSERT" && table == "blue_live_rad") {
        console.log("inserting rad....");
        checkAddRad(changes.data, action);
      }
      if (action == "INSERT" && table == "blue_live_pcl_rx") {
        console.log("inserting pcl rx....");
      }

      if (action == "INSERT" && table == "blue_live_target" && node != "gbad") {
        var targ_id = parseInt(changes.data.id_nr);
        var name = changes.data.name;
        if (name != "ref" && name != "test") {
          checkAddTarget(targ_id, changes);
        }
      }
    }
  }

  function passive_worker_listener(data) {
    var res = JSON.parse(data);
    var los = parseFloat(res[0]);

    if (los == 6200901) {
      terrain_mid_point_height = parseFloat(res[1]);

      updateHeightOfRxReturn(terrain_mid_point_height);
      return;
    }

    ret_msg = JSON.parse(data);

    if (ret_msg.request_type.search("findTxForRx_all_response") != -1) {
      findTxForRxReturn(ret_msg, map);
      updatePCLRxTxCallsigns();
      return;
    }

    if (ret_msg.request_type.search("calcMinDetRCScoverage_response") != -1) {
      nofRunningCoverages = calcMinDetRCSReturn(ret_msg, nofRunningCoverages);
      if (nofRunningCoverages < 0) {
        nofRunningCoverages = 0;
      }
      console.log("nofRunningCoverages = ", nofRunningCoverages);
      return;
    }

    if (ret_msg.request_type.search("calcDetRoute_response") != -1) {
      calcMinDetRCSForRouteReturn(ret_msg);
      return;
    }

    if (ret_msg.request_type.search("calcCoverageCorridor_response") != -1) {
      calcPassCoverageCorridorReturn(ret_msg);
      return;
    }

    if (ret_msg.request_type.search("findOptRxPos_response") != -1) {
      runOptAlgoReturn(ret_msg);
      return;
    }
  }

  function replay_worker_listener(data) {
    var res = JSON.parse(data);

    ret_msg = JSON.parse(data);
    if (ret_msg == "REPLAY_COMPLETED") {
      console.log("replay completed.................");
      stopReplay(replay_worker);
      stopRadTracking();

      forceKillAllTargets();
      removeDeadTargets();

      stopAirSimulation();
      removeAllReplaytargets();

      alert("Replaying data completed...");
    } else if (ret_msg.request_type.search("REPLAY_STATS") != -1) {
      var results = JSON.parse(ret_msg.args[0]);
      replay_speed = results[0];
      mean_det = results[1];
      distinct_dets = results[2];
      total_targets = results[3];
      mean_load = results[4];
      reptime = results[5]; // this is the time of replayed data in secs (not real time)
      replay_runtime = results[6]; // real replay runtime in seconds
      replay_server_time = results[7]; // time of sending this message at server
      var curr_time = Date.now();
      setReplayAnalysis(
        mean_det,
        replay_speed,
        mean_load,
        total_targets,
        reptime,
        replay_runtime
      );
    } else if (
      ret_msg.request_type.search("GET_REPLAY_REF_DATA_response") != -1
    ) {
      var results = JSON.parse(ret_msg.args[0]);
      var selectbox = document.getElementById(
        "replay_ref_file_download_selectbox"
      );
      selectbox.innerHTML = "";
      var dataArray = results[1];
      console.log("result size = ", results.length);
      for (var i = 0; i < results.length; i++) {
        var option = document.createElement("option");
        option.text = results[i];
        selectbox.appendChild(option);
      }
      return;
    } else if (
      ret_msg.request_type.search("GET_REPLAY_TEST_DATA_response") != -1
    ) {
      console.log("replay test data files received");
      var results = JSON.parse(ret_msg.args[0]);
      var selectbox = document.getElementById(
        "replay_test_file_download_selectbox"
      );
      selectbox.innerHTML = "";
      var dataArray = results[1];
      for (var i = 0; i < results.length; i++) {
        var option = document.createElement("option");
        option.text = results[i];
        selectbox.appendChild(option);
      }
    }

    // for replay of targets, where the worker does most of the work
    else if (res.request_type == "REF_TGT_UPDATE" && RUN_REPLAY == true) {
      //
      tracks = res.data;
      if (tracks.length > 0) {
        displayReplayTargets(tracks, 1);
      }
      return;
    }
    // for replay of targets, where the worker does most of the work
    else if (res.request_type == "TEST_TGT_UPDATE" && RUN_REPLAY == true) {
      tracks = res.data;
      if (tracks.length > 0) {
        displayReplayTargets(tracks, 0);
      }
      return;
    }
  }

  function radioprop_worker_listener(data) {
    var res = JSON.parse(data);
    var txt_file = res["tx-rx.txt"];
    var png_file = res["tx-rx.png"];

    document.getElementById("ItemPreview").src =
      "data:image/png;base64," + png_file;

    var myJSONString = JSON.stringify(txt_file);
    var myEscapedJSONString = myJSONString
      .replace(/\\n/g, "\n")
      .replace(/\\t/g, "  ");

    document.getElementById("prop_txt").value = myEscapedJSONString;
  }

  function pet_worker_listener(data) {
    var res = JSON.parse(data);
    var los = parseFloat(res[0]);
    console.log("los = ", los);
    if (los === 559999) {
      // this is coverage data return
      var active_coverage_request = new request_wrapper();
      active_coverage_request.request_type = "activeCoveragePoints";
      active_coverage_request.nbr_args = 1;
      active_coverage_request.args = [JSON.stringify(data)];
      var query = JSON.stringify(active_coverage_request);
      var rad_id = parseFloat(res[1]);
      console.log(
        "sending pet coverage plot to geoplot for pet sensor id: ",
        rad_id
      );
      geoplot_worker.postMessage([active_coverage_request.request_type, query]);
      nofRunningCoverages--;
      return;
    }

    if (res.request_type == "computeCoverage_response") {
      nofRunningCoverages--;
      var kmlstring = JSON.parse(res.args[0]);
      var kml = new ol.format.KML({
        extractStyles: true,
        extractAttributes: true,
        maxDepth: 2,
      });
      var kml_features = kml.readFeatures(kmlstring, {
        dataProjection: "EPSG:4326",
        featureProjection: "EPSG:3857",
      });

      if (kml_features.length > 0) {
        var currind = geoplot_track_layers.length;
        geoplot_track_layers[currind] = [];
        for (var i = 0; i < kml_features.length; i++) {
          var ssource = new ol.source.Vector();
          var vector = new ol.layer.Vector({
            source: ssource,
            format: kml,
            opacity: 0.3,
          });
          ssource.addFeature(kml_features[i]);
          geoplot_layers.push(vector);
          map.addLayer(vector);
          geoplot_track_layers[currind].push(vector);
          var kml_name = kml_features[i].get("name");
          // add this to table
          if (kml_name != "") {
            var kml_file_name = kml_name;
            $("#kml_table tbody").append(
              $("#kml_table tbody tr:first").clone()
            );
            $("#kml_table tbody tr:last td:first").html(kml_file_name);
            $("#kml_table tr:last td:last input").attr("disabled", "disabled");
            $("#kml_table tr:last")
              .find('input[type="checkbox"]')
              .prop("checked", true);
          }
        }
      }
    }
  }

  function geoplot_worker_listener(data) {
    var res = JSON.parse(data);
    console.log("geoplot_worker_listener: request_type = ", res.request_type);

    var tmpstring = JSON.parse(res.args[0]);
    console.log("res[0] = ", tmpstring);

    if (
      res.request_type == "activeCoveragePoints_response" ||
      res.request_type == "activeCoveragePointsPropagation_response"
    ) {
      // active coverage
      var kmlstring = JSON.parse(res.args[0]);
      console.log("results = ", kmlstring);

      //--------------
      var kml = new ol.format.KML({
        extractStyles: true,
        extractAttributes: true,
        maxDepth: 2,
      });
      var kml_features = kml.readFeatures(kmlstring, {
        dataProjection: "EPSG:4326",
        featureProjection: "EPSG:3857",
      });

      var colorpicker = document.getElementById("color_picker1");
      ////console.log ("color = ", colorpicker.value)
      var custom_color = document.getElementById(
        "color_picker_checker"
      ).checked;

      // ------------customized style by user
      var hexColor1 = colorpicker.value;
      var color = ol.color.asArray(hexColor1);
      var linecolor = ol.color.asArray(hexColor1);
      color = color.slice();
      color[3] = 0.4;
      // -------------set the style of the tracks------------
      var style = new ol.style.Style({
        fill: new ol.style.Fill({
          color: color,
        }),
        stroke: new ol.style.Stroke({
          width: 2,
          color: linecolor,
        }),
      });

      // -----------default_style
      var dhexColor = "rgba(255, 99, 132, 0.7)";
      var dcolor = ol.color.asArray(dhexColor);
      var dlinecolor = ol.color.asArray(dhexColor);
      dcolor = dcolor.slice();
      dcolor[3] = 0.4;
      // -------------set the style of the tracks------------
      var default_style = new ol.style.Style({
        fill: new ol.style.Fill({
          color: dcolor,
        }),
        stroke: new ol.style.Stroke({
          width: 2,
          color: dlinecolor,
        }),
      });

      var currind = geoplot_track_layers.length;
      geoplot_track_layers[currind] = [];
      for (var i = 0; i < kml_features.length; i++) {
        var kml_name = kml_features[i].get("name");

        var ssource = new ol.source.Vector();
        var vector = new ol.layer.Vector({
          source: ssource,
          format: kml,
          opacity: 0.5,
        });

        if (custom_color) {
          kml_features[i].setStyle(style);
        } else {
          kml_features[i].setStyle(default_style);
        }

        ssource.addFeature(kml_features[i]);
        geoplot_track_layers[currind].push(vector);
        map.addLayer(vector);

        // add this to table
        if (kml_name != "") {
          var kml_file_name = kml_name;
          if ($("#prop_enabled").is(":checked") == true) {
            kml_file_name = kml_file_name + ":+prop";
          }

          $("#kml_table tbody").append($("#kml_table tbody tr:first").clone());
          $("#kml_table tbody tr:last td:first").html(kml_file_name);
          $("#kml_table tr:last td:last input").attr("disabled", "disabled");
          $("#kml_table tr:last")
            .find('input[type="checkbox"]')
            .prop("checked", true);
        }
      }
    } else if (res.request_type == "getKMLFileList_response") {
      // this are kml file names
      console.log(":::::::::::::: kml files received ");
      var results = JSON.parse(res.args[0]);

      var selectbox = document.getElementById("kml_file_download_selectbox");
      selectbox.innerHTML = "";
      var dataArray = results[1];
      for (var i = 0; i < results.length; i++) {
        var option = document.createElement("option");
        option.text = results[i];
        selectbox.appendChild(option);
      }
    } else if (res.request_type == "getKMLFile_response") {
      // these are kml files from disk
      console.log(":::::::::::::::::::geoplot_worker received a kml file ");
      var kmlstring = JSON.parse(res.args[0]); //JSON.parse(res[1]);;

      var kml = new ol.format.KML({
        extractStyles: true,
        extractAttributes: true,
        maxDepth: 2,
      });
      var kml_features = kml.readFeatures(kmlstring, {
        dataProjection: "EPSG:4326",
        featureProjection: "EPSG:3857",
      });

      console.log("found features:", kml_features.length);

      var colorpicker = document.getElementById("color_picker1");
      console.log("color = ", colorpicker.value);
      var custom_color = document.getElementById(
        "color_picker_checker"
      ).checked;

      var hexColor = colorpicker.value;
      var color = ol.color.asArray(hexColor);
      color = color.slice();
      color[3] = 1.0;
      // -------------set the style of the tracks------------
      var style = new ol.style.Style({
        fill: new ol.style.Fill({
          color: color, //'rgba(220, 0, 0, 0.6)'
        }),
        stroke: new ol.style.Stroke({
          width: 5,
          color: color, //'rgba(220, 0, 0, 0.6)'
        }),
      });

      var currind = geoplot_track_layers.length;
      geoplot_track_layers[currind] = [];
      for (var i = 0; i < kml_features.length; i++) {
        var ssource = new ol.source.Vector();
        var vector = new ol.layer.Vector({
          source: ssource,
          format: kml,
          opacity: 0.5,
        });
        if (custom_color) {
          kml_features[i].setStyle(style);
        } else {
        }
        ssource.addFeature(kml_features[i]);
        geoplot_track_layers[currind].push(vector);
        map.addLayer(vector);
      }
    } else {
      // these are coverage kml files (e.g. PCL coverage)
      console.log("kml file for coverage received  ");
      var kmlstring = JSON.parse(res.args[0]);
      console.log("geoplot_worker got kmlstring: ", kmlstring);

      //--------------
      var kml = new ol.format.KML({
        extractStyles: true,
        extractAttributes: true,
        maxDepth: 2,
      });
      var kml_features = kml.readFeatures(kmlstring, {
        dataProjection: "EPSG:4326",
        featureProjection: "EPSG:3857",
      });

      var currind = geoplot_track_layers.length;
      geoplot_track_layers[currind] = [];
      console.log("found kml features: ", kml_features.length);

      for (var i = kml_features.length - 1; i > -1; i--) {
        var kml_name = kml_features[i].get("name");
        console.log("kml name = ", kml_name);
        var ssource = new ol.source.Vector();
        var vector = new ol.layer.Vector({
          source: ssource,
          format: kml,
          opacity: 0.5,
        });

        ssource.addFeature(kml_features[i]);
        geoplot_track_layers[currind].push(vector);
        map.addLayer(vector);

        // add this to table
        if (kml_name != "") {
          var kml_file_name = kml_name;
          $("#kml_table tbody").append($("#kml_table tbody tr:first").clone());
          $("#kml_table tbody tr:last td:first").html(kml_file_name);
          $("#kml_table tr:last td:last input").attr("disabled", "disabled");
          $("#kml_table tr:last")
            .find('input[type="checkbox"]')
            .prop("checked", true);
        }
        //}
      }
    }
  }

  function pdf_worker_listener(data) {
    console.log("pdf Worker said: ", data);

    var res = JSON.parse(data);
    console.log("jsondata = ", res);

    var los = parseFloat(res[0]);

    if (los === 0) {
    } else if (los == 2340902) {
      // this is to set the position of a sensor
      updateRadarPosition(e.data);
    } else if (los == 5340906) {
      // this is to set the position of poi mesh
      updatePOIPosition(e.data);
    } else if (los == 6200902) {
      // this is terrain height for PET computations
      terrain_mid_point_height = parseFloat(res[1]);
      addNewPETRx(curr_lat, curr_lon);
    } else if (los == 6200903) {
      // this is terrain height for PCL computations
      terrain_mid_point_height = parseFloat(res[1]);
      addNewPassiveRx(curr_lat, curr_lon, map, terrain_mid_point_height);
    } else if (los == 6200901) {
      // this is terrain height
      terrain_mid_point_height = parseFloat(res[1]);

      dist_to_poi = parseFloat(res[2]);
      // show popup
      var coordinate = ol.proj.transform(
        [curr_lon, curr_lat],
        "EPSG:4326",
        "EPSG:3857"
      );
      var lat_str = String(curr_lat).substring(0, 6);
      var lon_str = String(curr_lon).substring(0, 6);
      var terrain_str = String(terrain_mid_point_height);
      var dist_to_poi_str = String(dist_to_poi).substring(0, 6);
      var hdms =
        lat_str + ", " + lon_str + ", " + terrain_str + ", " + dist_to_poi_str; //ol.coordinate.toStringHDMS(ol.proj.transform(coordinate, 'EPSG:3857', 'EPSG:4326'));//

      popup_content.innerHTML =
        "<p>Lat:<code>" +
        lat_str +
        "</code><p>" +
        "<p>Lon: <code>" +
        lon_str +
        "</code><p>" +
        "<p>[masl]:<code>" +
        terrain_str +
        "</code><p>" +
        "<p>Dist POI [km]: <code>" +
        dist_to_poi_str +
        "</code><p>";
      popup_overlay.setPosition(coordinate); //
    } else if (los == 559765) {
      // this is radar coverage return
      // plot all the points in a polygon
      nofRunningCoverages--;
      var res = JSON.parse(data);
      var count = 0;
      for (k in res) {
        count++;
      }

      if (nofRunningCoverages == 0) {
        document.getElementById("blue-led").className = "";
      }

      if (count > 5) {
        // -   --------------new also send this to the geoplot server-------------
        var active_coverage_request = new request_wrapper();
        active_coverage_request.request_type = "activeCoveragePoints";
        active_coverage_request.nbr_args = 1;
        active_coverage_request.args = [JSON.stringify(data)];
        var query = JSON.stringify(active_coverage_request);
        var rad_id = parseFloat(res[1]);
        geoplot_worker.postMessage([
          active_coverage_request.request_type,
          query,
        ]);
      }
    } else if (los == 919765) {
      // this is radar coverage return, but using propgation losses
      nofRunningCoverages--;
      var res = JSON.parse(data);
      var count = 0;
      for (k in res) {
        count++;
      }

      if (nofRunningCoverages == 0) {
        document.getElementById("blue-led").className = "";
      }

      if (count > 5) {
        // -   --------------new also send this to the geoplot server-------------
        var active_coverage_request = new request_wrapper();
        active_coverage_request.request_type =
          "activeCoveragePointsPropagation";
        active_coverage_request.nbr_args = 1;
        active_coverage_request.args = [JSON.stringify(data)];
        var query = JSON.stringify(active_coverage_request);
        var rad_id = parseFloat(res[1]);
        console.log(
          "sending active radar PROPAGATION coverage plot to geoplot for rad id: ",
          rad_id
        );
        geoplot_worker.postMessage([
          active_coverage_request.request_type,
          query,
        ]);
      }
    } else if (los == 29824733) {
      // propgation point to point return

      var res = JSON.parse(data);
      ress = res[1];
      var txt_file = ress["TX_-to-RX_.txt"];
      var png_file = ress["height_profile.png"];

      document.getElementById("ItemPreview").src =
        "data:image/png;base64," + png_file;

      var myJSONString = JSON.stringify(txt_file);
      var myEscapedJSONString = myJSONString
        .replace(/\\n/g, "\n")
        .replace(/\\t/g, "  ");

      document.getElementById("prop_txt").value = myEscapedJSONString;
    } else if (los == 3456178) {
      var res = JSON.parse(data);
      z_data = res[1];
      dist_ns_m = res[2];
      dist_ew_m = res[3];
      x_data = res[4];
      y_data = res[5];
      console.log("ranges [m] = ", dist_ns_m, dist_ew_m);
      var data = [
        {
          x: x_data,
          y: y_data,
          z: z_data,
          type: "surface",
          contours: {
            z: {
              show: true,
              usecolormap: true,
              highlightcolor: "#42f462",
              project: { z: true },
            },
          },
        },
      ];

      var layout = {
        title: "POI 10x10km Backdrop",
        scene: {
          aspectmode: "data",
          camera: {
            eye: { x: 0.0, y: -1.0, z: 4.5 },
            up: { x: 0, y: 0, z: 1 },
          },
          xaxis: {
            title: "+East:West- [m] from POI",
            titlefont: {
              family: "Courier New, monospace",
              size: 14,
              color: "#7f7f7f",
            },
          },
          yaxis: {
            title: "+North:South-[m] from POI",
            titlefont: {
              family: "Courier New, monospace",
              size: 14,
              color: "#7f7f7f",
            },
          },
          zaxis: {
            title: "[masl]",
            titlefont: {
              family: "Courier New, monospace",
              size: 14,
              color: "#7f7f7f",
            },
          },
        },
        autosize: true,
        width: 700,
        height: 700,
        margin: {
          l: 10,
          r: 50,
          b: 65,
          t: 40,
        },
      };

      Plotly.newPlot("terrDiv", data, layout);
    }
  }

  // queries the proxy server and inits the workers with the correct ws addresses
  // assumes that the global variable proxy_server is set
  function initWorkersWithServers() {
    var proxy_ws = new WebSocket(proxy_server);

    proxy_ws.onmessage = function (evt) {
      var msg = JSON.parse(evt.data);
      console.log("got message from proxy server: ", msg);
      console.log("for: ", msg[0]);

      switch (msg[0]) {
        case "dem":
          pdf_worker = new Worker("/static/js/pdfWorker.js");
          var s_prim = msg[1];
          console.log("######### dem ip and port: ", s_prim);
          pdf_worker.postMessage([8993493, s_prim]); // set the correct dem server address and port
          pdf_worker.addEventListener("message", function (e) {
            pdf_worker_listener(e.data);
          });
          break;
        case "geoplot":
          geoplot_worker = new Worker("/static/js/geoPlotWorker.js");
          var s_prim = msg[1];
          //console.log("..............in geoplot, ", s_prim)
          geoplot_worker.postMessage([8993493, s_prim]); // set the correct geoplot server address and port
          geoplot_worker.addEventListener("message", function (e) {
            geoplot_worker_listener(e.data);
          });
          break;

        case "sensor_control":
          sensor_control_worker = new Worker(
            "/static/js/sensorControlWorker.js"
          );
          var s_prim = msg[1];
          sensor_control_worker.postMessage([8993493, s_prim]); //
          sensor_control_worker.addEventListener("message", function (e) {
            sensor_control_worker_listener(e.data);
          });

          break;
        case "detection_sim":
          detection_sim_worker = new Worker("/static/js/detectionSimWorker.js");
          var s_prim = msg[1];
          detection_sim_worker.postMessage([8993493, s_prim]); // set the correct detection_sim server address and port
          detection_sim_worker.addEventListener("message", function (e) {
            detection_sim_worker_listener(e.data);
          });
          break;
        case "pet":
          console.log("starting pet worker....");
          pet_worker = new Worker("/static/js/petWorker.js");
          var s_prim = msg[1];
          pet_worker.postMessage([8993493, s_prim]); // set the correct pet server address and port
          pet_worker.addEventListener("message", function (e) {
            console.log("pet Worker said: ", e.data);
            pet_worker_listener(e.data);
          });
          break;
        case "radioprop":
          radioprop_worker = new Worker("/static/js/radioPropWorker.js");
          var s_prim = msg[1];
          radioprop_worker.postMessage([8993493, s_prim]); // set the correct radioprop server address and port
          radioprop_worker.addEventListener("message", function (e) {
            radioprop_worker_listener(e.data);
          });
          break;
        case "pcl":
          console.log(
            "=============================== starting pcl worker...."
          );
          passive_worker = new Worker("/static/js/passiveworker.js");
          var s_prim = msg[1];
          console.log("in pcl, ", s_prim);
          passive_worker.postMessage([8993493, s_prim]); // set the correct pcl server address and port
          passive_worker.addEventListener("message", function (e) {
            passive_worker_listener(e.data);
          });
          break;
        case "replay":
          console.log(
            "=============================== starting replay worker...."
          );
          replay_worker = new Worker("/static/js/replayWorker.js");
          var s_prim = msg[1];
          console.log("in replay, ", s_prim);
          replay_worker.postMessage([8993493, s_prim]); // set the correct replay server address and port
          replay_worker.addEventListener("message", function (e) {
            replay_worker_listener(e.data);
          });
          break;

        default:
          //Statements executed when none of the values match the value of the expression
          console.log("ERROR: app.js initing an unknown worker");
          break;
      }
    };
    proxy_ws.onopen = function (event) {};
    proxy_ws.onclose = function (evt) {};

    proxy_ws.onopen = function () {
      console.log("**opening workers...");

      proxy_ws.send("sensor_control");
      console.log("*opened sensor_control...");

      proxy_ws.send("detection_sim");
      console.log("*opened det_sim...");

      proxy_ws.send("pcl");
      console.log("*opened pcl...");

      proxy_ws.send("pet");
      console.log("*opened pet...");

      proxy_ws.send("geoplot");
      console.log("*opened geoplot...");

      proxy_ws.send("dem");
      console.log("*opened dem...");

      proxy_ws.send("radioprop");
      console.log("*opened radioprop...");

      proxy_ws.send("replay");
      console.log("*opened replay...");
    };
  }

  //////////////////////////////////////////////////////////////////////////////////////7
  // Start Target Class
  //////////////////////////////////////////////////////////////////////////////////////

  function TargetLocation(
    object_id,
    id,
    lat,
    lon,
    terrainHeight,
    flightHeight
  ) {
    // object_id = TRACK_LOCATION_PARAM_ID for target location
    //"object_id", "id", "name", "lat", "lon", "terrainHeight", "flightHeight", "poi_name", "agl_asl"
    this.object_id = object_id;
    this.id = id;
    this.lat = lat;
    this.lon = lon;
    this.terrainHeight = terrainHeight;
    this.flightHeight = flightHeight;

    this.roll = 0;
    this.pitch = 0;
    this.yaw = 0;
    this.velocity = 0;

    this.corridor_width = 0; // m
    this.corridor_height = 0; // m

    this.x = 0; // swissgrid
    this.y = 0; // swissgrid
    this.corridor_bearing = 0; // degrees, bearing of corridor width, alternative to store would be dir. vector
  }
  var targetLocationArray = []; // this will contain the target locations, e.g. for pd computation

  function Target(
    object_id,
    id,
    rcs,
    name,
    running,
    velocity,
    corridor_breadth,
    noftargets,
    type,
    threeD_waypoints_id,
    status,
    maneuvring
  ) {
    this.object_id = object_id;
    this.id = id;
    this.rcs = rcs;
    this.name = name;
    this.running = running; // 0= not running, 1 = running
    this.velocity = velocity;
    this.corridor_breadth = corridor_breadth;
    this.noftargets = noftargets;
    this.type = type;
    this.threeD_waypoints_id = threeD_waypoints_id;
    this.status = status; // dead = 0/ alive = 1/
    this.maneuvring = maneuvring;
  }
  var targetArray = []; // this will contain all the targets

  function Detection(object_id, targ_id, lat, lon, height, sensor_id) {
    this.object_id = object_id;
    this.targ_id = targ_id;
    this.sensor_id = sensor_id;
    this.lat = lat;
    this.lon = lon;
    this.height = height;
  }
  var detectionArray = []; // this will contain all the detection

  function TargetTrigger(
    object_id,
    id,
    name,
    source_target_id,
    dest_target_id,
    dist_to_poi,
    poi_name
  ) {
    this.object_id = object_id;
    this.id = id;
    this.name = name;
    this.source_target_id = source_target_id;
    this.dest_target_id = dest_target_id;
    this.dist_to_poi = dist_to_poi; // triggers if distance to poi is equal or less than this [km]
    this.poi_name = poi_name;
  }

  var triggerArray = [];
  var curTriggerID = runningTriggersId;

  function ThreatScenario(
    object_id,
    name,
    triggerArray,
    targetArray,
    three_d_waypoints_array,
    poi
  ) {
    this.object_id = object_id;
    this.name = name;
    this.triggerArray = triggerArray;
    this.targetArray = targetArray;
    this.three_d_waypoints_array = three_d_waypoints_array;
    this.poi = poi;
  }

  function getTargetFromID(id) {
    var tgt = null;
    for (var i = 0, l = targetArray.length; i < l; i++) {
      if (targetArray[i].id == id) {
        return targetArray[i];
      }
    }

    return tgt;
  }

  function getTriggerFromID(id) {
    var trigger = null;
    for (var i = 0, l = triggerArray.length; i < l; i++) {
      if (triggerArray[i].id == id) {
        return triggerArray[i];
      }
    }

    return trigger;
  }

  function getTotalNofTargets() {
    var noftargs = 0;
    for (var j = 0, ll = targetArray.length; j < ll; j++) {
      noftargs = noftargs + parseInt(targetArray[j].noftargets);
    }
    return noftargs;
  }

  function stringifyTarget(target) {
    var retval = JSON.stringify(target, [
      "object_id",
      "id",
      "rcs",
      "name",
      "running",
      "velocity",
      "corridor_breadth",
      "noftargets",
      "type",
      "threeD_waypoints_id",
      "status",
      "maneuvring",
    ]);
    return retval;
  }

  function stringifyThreatScenario(threat_scenario) {
    var retval = JSON.stringify(threat_scenario, [
      "object_id",
      "threat_scenario_name",
      "triggerArray",
      "targetArray",
      "three_d_waypoints_array",
      "poi",
      "id",
      "rcs",
      "name",
      "running",
      "velocity",
      "corridor_breadth",
      "noftargets",
      "type",
      "threeD_waypoints_id",
      "status",
      "source_target_id",
      "dest_target_id",
      "dist_to_poi",
      "poi_name",
      "agl_asl",
      "lat",
      "lon",
      "terrainHeight",
      "flightHeight",
      "targetLocationArray",
      "maneuvring",
    ]);
    return retval;
  }

  function resetTargetLocationArray() {
    targetLocationArray = [];
    mapLayersArray = [];
    targetLocationArray.length = 0;
    mapLayersArray.length = 0;
  }

  // returns rcs of a target from user input
  function getTargetRCSNew() {
    return document.getElementById("coverage_rcs").value;
  }
  // returns rcs of a target from user input for PCL online detection
  function getPCLTargetRCSNew() {
    return document.getElementById("pcl_detection_rcs").value;
  }

  // returns ERP of a target from user input
  function getTargetERP() {
    return document.getElementById("pet_coverage_erp").value;
  }
  function getTargetHeight() {
    return document.getElementById("flightheight").value;
  }

  function getPetGrid() {
    return [
      document.getElementById("pet_lat_min").value,
      document.getElementById("pet_lat_max").value,
      document.getElementById("pet_lon_min").value,
      document.getElementById("pet_lon_max").value,
    ];
  }

  function getRadioPropGrid() {
    return [
      document.getElementById("prop-model-select").options[
        document.getElementById("prop-model-select").selectedIndex
      ].value,
      document.getElementById("diel_const").value,
      document.getElementById("earth_cond").value,
      document.getElementById("at_bend").value,
      document.getElementById("radio_climate").value,
      document.getElementById("ground_clutter").value,
      document.getElementById("p2p_prop_tx_lat").value,
      document.getElementById("p2p_prop_tx_lon").value,
      document.getElementById("p2p_prop_tx_ant_h").value,
      document.getElementById("p2p_prop_tx_pol").value,
      document.getElementById("p2p_prop_tx_erp").value,
      document.getElementById("p2p_prop_tx_freq").value,
      document.getElementById("p2p_prop_rx_lat").value,
      document.getElementById("p2p_prop_rx_lon").value,
      document.getElementById("p2p_prop_rx_ant_h").value,
    ];
  }

  function getRadioPropGridShort() {
    return [
      document.getElementById("prop-model-select").options[
        document.getElementById("prop-model-select").selectedIndex
      ].value,
      document.getElementById("diel_const").value,
      document.getElementById("earth_cond").value,
      document.getElementById("at_bend").value,
      document.getElementById("radio_climate").value,
      document.getElementById("ground_clutter").value,
    ];
  }
  //////////////////////////////////////////////////////////////////////////////////////////
  // end target class
  /////////////////////////////////////////////////////////////////////////////////////////

  /////////////////////////////////////////////////////////////////////////////////////
  /*  START RADIO PROP QUERY CLASS */
  ////////////////////////////////////////////////////////////////////////////////////

  function RadioPropQueryShort(
    query_id,
    diel_const,
    earth_cond,
    at_bend,
    radio_climate,
    ground_clutter,
    oitm
  ) {
    //
    this.query_id = query_id;
    this.diel_const = diel_const;
    this.earth_cond = earth_cond;
    this.at_bend = at_bend;
    this.radio_climate = radio_climate;
    this.ground_clutter = ground_clutter;
    this.oitm = oitm;
  }

  /////////////////////////////////////////////////////////////////////////////////////
  /*  START PET SENSOR CLASS */
  ////////////////////////////////////////////////////////////////////////////////////
  function PetSensor(
    object_id,
    id,
    name,
    status,
    lat,
    lon,
    threshold,
    terrainHeight
  ) {
    // object_id = PETSENSOR_PARAM_ID for sensor object
    //console.log("huhu1: ", object_id, id, name, status, lat, lon, threshold, terrainHeight)
    this.object_id = object_id;
    this.id_nr = id;
    this.name = name;
    this.status = status;
    this.lat = lat;
    this.lon = lon;
    this.threshold = threshold;
    this.height = terrainHeight;
    //console.log("huhu2: ", this.object_id, this.id, this.name, this.status, this.lat, this.lon, this.threshold, this.height)
  }

  /////////////////////////////////////////////////////////////////////////////////////
  /*  START ACITVE MONSTATIC SENSOR CLASS */
  /////////////////////////////////////////////////////////////////////////////////////

  function ActiveMonostaticSensor(object_id, id, name, lat, lon, layer) {
    // object_id = ACTIVE_MONOSTATIC_SENSOR_PARAM_ID for sensor object
    this.object_id = object_id;
    this.id_nr = id;
    this.layer = layer;
    this.lat = lat;
    this.lon = lon;
    this.power = -1;
    this.antenna_diam = -1;
    this.freq = -1;
    this.pulse_width = -1;
    this.cpi_pulses = -1;
    this.bandwidth = -1;
    this.pfa = -1;
    this.rotation_time = -1;
    this.category = -1;
    this.name = name;
    this.status = 1;

    this.min_elevation = 1;
    this.max_elevation = 1;
    this.orientation = 1;
    this.horiz_aperture = 1;
    this.min_detection_range = 1;
    this.max_detection_range = 1;
    this.min_detection_height = 1;
    this.max_detection_height = 1;
    this.min_detection_tgt_speed = 1;
    this.max_detection_tgt_speed = 1;
  }
  var coverageShown = 1;

  function getSensorFromID(id) {
    var sens = null;
    for (var i = 0, l = activeMonostaticArray.length; i < l; i++) {
      if (activeMonostaticArray[i].id_nr == id) {
        return activeMonostaticArray[i];
      }
    }

    return sens;
  }

  // just stringify the pet sensor array
  function stringifyPetSensor(sensor) {
    //console.log("stringifying pet: ", sensor)
    var retval = JSON.stringify(sensor, [
      "object_id",
      "id_nr",
      "name",
      "status",
      "lat",
      "lon",
      "threshold",
      "height",
    ]);
    //console.log("stringified pet as: ", retval)
    return retval; //
  }

  // just stringify the radio prop query
  function stringifyRadioPropQuery(query) {
    var retval = JSON.stringify(query, [
      "query_id",
      "tx_lat",
      "tx_lon",
      "tx_antenna_height",
      "rx_lat",
      "rx_lon",
      "rx_antenna_height",
      "diel_const",
      "earth_cond",
      "at_bend",
      "freq",
      "radio_climate",
      "pol",
      "ground_clutter",
      "oitm",
      "detailed_analysis",
      "erp",
    ]);
    return retval; //
  }

  // just stringify the sensor / sensor-array
  function stringifySensor(sensor) {
    var retval = JSON.stringify(sensor, [
      "object_id",
      "id_nr",
      "name",
      "lat",
      "lon",
      "power",
      "antenna_diam",
      "freq",
      "pulse_width",
      "cpi_pulses",
      "bandwidth",
      "pfa",
      "status",
      "rotation_time",
      "category",
      "status",
      "min_elevation",
      "max_elevation",
      "orientation",
      "horiz_aperture",
      "min_detection_range",
      "max_detection_range",
      "min_detection_height",
      "max_detection_height",
      "min_detection_tgt_speed",
      "max_detection_tgt_speed",
    ]);

    return retval;
  }

  // just stringify the sensor / sensor-array
  function stringifyPCLRx(sensor) {
    var retval = JSON.stringify(sensor, [
      "object_id",
      "rx_id",
      "name",
      "lat",
      "lon",
      "ahmagl",
      "bandwidth",
      "gain",
      "masl",
      "limit_distance",
      "losses",
      "signal_type",
      "temp_sys",
      "status",
      "vert_diagr_att",
      "horiz_diagr_att",
      "lostxids",
      "txcallsigns",
    ]);

    return retval;
  }

  // just stringify the sensor / sensor-array

  function stringifyPCLTx(tx) {
    var retval = JSON.stringify(tx, [
      "object_id",
      "tx_id",
      "callsign",
      "status",
      "lat",
      "lon",
      "masl",
      "ahmagl",
      "freq",
      "bandwidth",
      "erp_h",
      "erp_v",
      "type",
      "horiz_diagr_att",
      "vert_diagr_att",
      "pol",
      "signal_type",
      "losrxids",
      "sitename",
    ]);
    return retval;
  }

  // ----------------------animate sensors

  function flash(feature, tmp) {
    //console.log("inside sensor flash...", tmp)

    if (tmp == 0) {
      var style = new ol.style.Style({
        fill: new ol.style.Fill({
          color: "rgba(220, 0, 0, 0.3)",
        }),
        stroke: new ol.style.Stroke({
          width: 2,
          color: "rgba(220, 0, 0, 0.3)",
        }),
      });

      feature.setStyle(style);
    }
    if (tmp == 1) {
      var style = new ol.style.Style({
        fill: new ol.style.Fill({
          color: "rgba(220, 0, 0, 0.6)",
        }),
        stroke: new ol.style.Stroke({
          width: 2,
          color: "rgba(220, 0, 0, 0.6)",
        }),
      });

      feature.setStyle(style);
    }
    if (tmp == 2) {
      var style = new ol.style.Style({
        fill: new ol.style.Fill({
          color: "rgba(220, 0, 0, 0.9)",
        }),
        stroke: new ol.style.Stroke({
          width: 2,
          color: "rgba(220, 0, 0, 0.9)",
        }),
      });

      feature.setStyle(style);
    }
  }

  //-----------------------------------------------------------------------------
  var TARGET_GUI_ACTION = 3;

  // circle for the flight pos
  var flight_circle = new ol.geom.Circle(
    ol.proj.transform([10, 1], "EPSG:4326", "EPSG:3857"),
    200,
    "XY"
  );
  var circleFeatureFlight = new ol.Feature(flight_circle);

  //------------ for simulating the target
  function TargetCircle(id) {
    ////console.log("initializing target: ", id)
    this.id = id;

    var str_id = getStringFromUniCodeID(id, test_track_id_is_unicode);

    this.lat = 54.583;
    this.lon = 10.77;
    this.target_circle = new ol.geom.Circle(
      ol.proj.fromLonLat([this.lon, this.lat]),
      1000,
      "XY"
    );
    this.circleFeatureTarget = new ol.Feature(this.target_circle);

    this.markerLayer = new ol.layer.Vector({
      source: new ol.source.Vector({
        features: [
          new ol.Feature({
            geometry: new ol.geom.Circle(
              ol.proj.fromLonLat([this.lon, this.lat]),
              1000
            ),
          }),
        ],
      }),
      projection: "EPSG:3857",
      style: new ol.style.Style({
        fill: new ol.style.Fill({
          color: "rgba(250, 50, 50, 0.3)",
        }),
        stroke: new ol.style.Stroke({
          width: 4,
          color: "rgba(250, 10, 10, 0.8)",
        }),
        text: new ol.style.Text({
          text: str_id,
          scale: 1.0,
          fill: new ol.style.Fill({
            color: "rgba(250, 10, 10, 0.8)",
          }),
          stroke: new ol.style.Stroke({
            color: "rgba(250, 200, 200, 0.8)",
            width: 2.5,
          }),
        }),
      }),
      visible: true,
    });
    map.addLayer(this.markerLayer);
  }

  //------------ for simulating the detection
  function DetectionCircle(targ_id, sensor_id) {
    this.targ_id = targ_id;
    this.sensor_id = sensor_id;

    var str_id1 = getStringFromUniCodeID(targ_id, test_track_id_is_unicode);
    var str_id2 = getStringFromUniCodeID(sensor_id, test_track_id_is_unicode);
    var str_id = str_id1 + "-" + str_id2;

    this.lat = 54.583;
    this.lon = 10.77;
    this.detection_circle = new ol.geom.Circle(
      ol.proj.fromLonLat([this.lon, this.lat]),
      1000,
      "XY"
    );
    this.circleFeatureDetection = new ol.Feature(this.detection_circle);

    this.markerLayer = new ol.layer.Vector({
      source: new ol.source.Vector({
        features: [
          new ol.Feature({
            geometry: new ol.geom.Circle(
              ol.proj.fromLonLat([this.lon, this.lat]),
              1000
            ),
          }),
        ],
      }),
      projection: "EPSG:3857",
      style: new ol.style.Style({
        fill: new ol.style.Fill({
          color: "rgba(50, 50, 150, 0.3)",
        }),
        stroke: new ol.style.Stroke({
          width: 4,
          color: "rgba(10, 10, 150, 0.8)",
        }),
        text: new ol.style.Text({
          text: str_id,
          scale: 1.0,
          fill: new ol.style.Fill({
            color: "rgba(10, 10, 250, 0.8)",
          }),
          stroke: new ol.style.Stroke({
            color: "rgba(200, 200, 250, 0.8)",
            width: 2.5,
          }),
        }),
      }),
      visible: true,
    });
    map.addLayer(this.markerLayer);
  }

  function chunkString(str, length) {
    return str.match(new RegExp(".{1," + length + "}", "g"));
  }

  function getStringFromUniCodeID(id, is_unicode) {
    if (is_unicode == 0) {
      // if not unicode then just get the last
      //String(curr_lat).substring(0,6);
      var id_str = id.toString();
      var id_str_len = id_str.length;
      return id_str.substring(id_str_len - 3, id_str_len);
    } else {
      // if unicode represenation is used in ID get back the original   ID
      var chunks = chunkString(id.toString(), 2); // get chunks of two
      var corrected_id = "";
      for (i = 0; i < chunks.length; i++) {
        corrected_id = corrected_id + String.fromCharCode(chunks[i]);
      }
      return corrected_id;
    }
  }
  var detectionCircleArray = [];
  var targetCircleArray = [];
  //------------ for simulating the target
  function ReferenceTargetCircle(id) {
    this.id = id;
    var str_id = getStringFromUniCodeID(id, ref_track_id_is_unicode);

    this.lat = 54.583;
    this.lon = 10.77;
    this.target_circle = new ol.geom.Circle(
      ol.proj.fromLonLat([this.lon, this.lat]),
      1000,
      "XY"
    );
    this.circleFeatureTarget = new ol.Feature(this.target_circle);

    this.markerLayer = new ol.layer.Vector({
      source: new ol.source.Vector({
        features: [
          new ol.Feature({
            geometry: new ol.geom.Circle(
              ol.proj.fromLonLat([this.lon, this.lat]),
              1000
            ),
          }),
        ],
      }),
      projection: "EPSG:3857",
      style: new ol.style.Style({
        fill: new ol.style.Fill({
          color: "rgba(50, 50, 250, 0.3)",
        }),
        stroke: new ol.style.Stroke({
          width: 4,
          color: "rgba(10, 10, 250, 0.8)",
        }),
        text: new ol.style.Text({
          text: str_id,
          scale: 1.0,
          fill: new ol.style.Fill({
            color: "rgba(10, 10, 250, 0.8)",
          }),
          stroke: new ol.style.Stroke({
            color: "rgba(200, 200, 250, 0.8)",
            width: 2.5,
          }),
        }),
      }),
      visible: true,
    });
    map.addLayer(this.markerLayer);
  }
  // --------------------------------

  var hostile_line_style = new ol.style.Style({
    fill: new ol.style.Fill({
      color: "rgba(220, 10, 10, 0.7)",
    }),
    stroke: new ol.style.Stroke({
      width: 2,
      color: "rgba(220, 10, 10, 0.7)",
    }),
  });

  function POI(object_id, id, poi_name, poi_lat, poi_lon) {
    this.object_id = object_id;
    this.id = id;
    this.name = poi_name;
    this.lat = poi_lat;
    this.lon = poi_lon;
  }

  var mapLayersArray = []; // will contain the map layers for drawing trajectory

  // radar  sphere mesh
  var radar_delta_x_kms = 0;
  var radar_delta_y_kms = 0;

  function setTerrainCulisse() {
    console.log(":::::::::::::::::::::::::::::::: getting terrain culisse");

    pdf_worker.postMessage([3456178, poi.lat, poi.lon, 5.0]);
  }

  var targetHeight = 0;
  function setTargetHeight() {
    targetHeight = parseFloat(document.getElementById("flightheight").value);
    console.log("target height = ", targetHeight);
  }
  // returns a string containing all used Tx callsigns
  function getAllTxsForRxs() {
    retstr = "";
    for (var i = 0, l = passiveRxArray.length; i < l; i++) {
      retstr = retstr + " " + passiveRxArray[i].txcallsigns;
    }
    return retstr;
  }

  function insertPCLTxDataToDB() {
    //-----------------insert the Tx with status == 1 into DB
    var db_request = new request_wrapper();
    db_request.request_type = "insertPCLTx";
    db_request.nbr_args = 0;
    req = [];
    updateTxOfOpportArrayFromTable();
    alltxs = getAllTxsForRxs();
    console.log("passiveTxArray = ", passiveTxArray); //
    for (var i = 0, l = passiveTxArray.length; i < l; i++) {
      if (alltxs.includes(passiveTxArray[i].callsign)) {
        db_request.nbr_args = db_request.nbr_args + 1;
        db_request.args.push(stringifyPCLTx(passiveTxArray[i]));
      }
    }
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;

    var query = JSON.stringify(db_request);
    console.log("...................inserting PCL Tx");
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  function insertPCLRxDataToDB() {
    document.getElementById("db_item_team_info").value =
      "...........inserting PCL Rx to DB.";
    // tell the DB all the RADINT we have placed
    var db_request = new request_wrapper();
    db_request.request_type = "insertPCLRx";
    db_request.nbr_args = 0;
    req = [];
    updatePassSensorArrayFromTable();
    console.log("passiveRxArray = ", passiveRxArray);
    for (var i = 0, l = passiveRxArray.length; i < l; i++) {
      db_request.nbr_args = db_request.nbr_args + 1;
      passiveRxArray[i].status = 0;
      db_request.args.push(stringifyPCLRx(passiveRxArray[i]));
    }

    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;

    var query = JSON.stringify(db_request);
    console.log("inserting PCL Rx with query: ", query);
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  function insertRadintToDB() {
    document.getElementById("db_item_team_info").value =
      "...........inserted to DB.";
    // tell the DB all the RADINT we have placed
    var db_request = new request_wrapper();
    db_request.request_type = "insertRADINT";
    db_request.nbr_args = 0;
    req = [];
    updateSensorArrayFromTable();

    for (var i = 0, l = activeMonostaticArray.length; i < l; i++) {
      db_request.nbr_args = db_request.nbr_args + 1;
      db_request.args.push(stringifySensor(activeMonostaticArray[i]));
    }

    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    sensor_control_worker.postMessage([db_request.request_type, query]);

    initTimeAnalysis();
  }

  function stopDetections() {
    var db_request = new request_wrapper();
    db_request.request_type = "STOP_DETECTION";
    db_request.nbr_args = 0;

    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    detection_sim_worker.postMessage([db_request.request_type, query]);
    console.log("STOPPING DETECTION");
  }

  function startDetections() {
    var db_request = new request_wrapper();
    db_request.request_type = "START_DETECTION";
    db_request.nbr_args = 0;

    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    detection_sim_worker.postMessage([db_request.request_type, query]);
    console.log("STARTING DETECTION");
  }

  function ignore_rad() {
    var db_request = new request_wrapper();
    db_request.request_type = "ignore_rad";
    db_request.nbr_args = 0;

    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    sensor_control_worker.postMessage([db_request.request_type, query]);
    console.log("ignoring RADINT");
  }

  function ignoreTARGETS() {
    var db_request = new request_wrapper();
    db_request.request_type = "ignoreTARGETS";
    db_request.nbr_args = 0;

    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    sensor_control_worker.postMessage([db_request.request_type, query]);
    console.log("ignoring targets");
  }

  function fetchAir() {
    console.log("fetching air");
    document.getElementById("db_item_team_info").value =
      "...........fetching AIR from DB.";

    var db_request = new request_wrapper();
    db_request.request_type = "fetchAIR";
    db_request.nbr_args = 0;

    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    console.log("fetching AIR: ", query);
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  function clearDBtable() {
    var table = document.getElementById("db_table");
    var rowCount = table.rows.length;
    while (rowCount > 1) {
      table.deleteRow(rowCount - 1);
      rowCount = table.rows.length;
    }
  }

  function fetchPCLRx() {
    // clearDB table
    clearDBtable();

    document.getElementById("db_item_team_info").value =
      "...........fetching PCL Rx from DB.";

    var db_request = new request_wrapper();
    db_request.request_type = "fetchPCLRx";
    db_request.nbr_args = 0;

    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    console.log("fetching PCL Rx: ", query);
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  function fetchRadint() {
    // clearDB table
    clearDBtable();

    document.getElementById("db_item_team_info").value =
      "...........fetching RAD from DB.";

    var db_request = new request_wrapper();
    db_request.request_type = "fetchRADINT";
    db_request.nbr_args = 0;

    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  // get the waypoints and set this as the target trajectory
  function insertAirDataToDB() {
    document.getElementById("db_item_team_info").value =
      "...........inserted to DB.";
    document.getElementById("green-led").className = "led-green";

    // reset the target circles array
    for (var i = 0, l = targetCircleArray.length; i < l; i++) {
      map.removeLayer(targetCircleArray[i].markerLayer);
    }
    targetCircleArray = [];

    // reset the detection circles array
    for (var i = 0, l = detectionCircleArray.length; i < l; i++) {
      map.removeLayer(detectionCircleArray[i].markerLayer);
    }
    detectionCircleArray = [];

    // update target array from table
    updateTargetArrayFromTable();

    // update waypoints
    updateWaypointsArrayFromTable();
    // update POI
    updatePOIfromTable();
    // update trigger array
    updateTriggerArrayFromTable();

    updateTargetCirclesArray(); // update the target circles

    var sim_request = new request_wrapper();
    sim_request.request_type = "insert_AIR";
    sim_request.nbr_args = 0;
    //console.log("targetArray = ", targetArray);
    sim_request.args.push(JSON.stringify(targetArray));
    sim_request.nbr_args = sim_request.nbr_args + 1;
    var waypoints_json = JSON.stringify(waypoint.three_d_waypoints_array, [
      "object_id",
      "id",
      "name",
      "agl_asl",
      "targetLocationArray",
      "lat",
      "lon",
      "terrainHeight",
      "flightHeight",
    ]);
    sim_request.args.push(waypoints_json);
    sim_request.nbr_args = sim_request.nbr_args + 1;
    var poi_json = JSON.stringify(poi, [
      "object_id",
      "name",
      "lat",
      "lon",
      "id",
    ]);
    sim_request.args.push(poi_json);
    sim_request.nbr_args = sim_request.nbr_args + 1;
    var triggers_json = JSON.stringify(triggerArray, [
      "object_id",
      "name",
      "id",
      "source_target_id",
      "dest_target_id",
      "dist_to_poi",
      "poi_id_nr",
    ]);

    sim_request.args.push(triggers_json);
    sim_request.nbr_args = sim_request.nbr_args + 1;
    sim_request.args.push(JSON.stringify(team));
    sim_request.nbr_args = sim_request.nbr_args + 1;
    var query = JSON.stringify(sim_request);

    sensor_control_worker.postMessage([sim_request.request_type, query]);
  }

  function startRadTracking() {
    //just to reconnect to server if connection was interrupted
    detection_sim_worker.postMessage([]);
    sensor_control_worker.postMessage([]);

    document.getElementById("db_item_team_info").value =
      "...........RAD tracking started.";
    var sim_request = new request_wrapper();
    sim_request.request_type = "RAD_START";
    sim_request.nbr_args = 0;
    sim_request.args.push(JSON.stringify(team));
    sim_request.nbr_args = sim_request.nbr_args + 1;
    sim_request.args.push(getTargetRCSNew());
    sim_request.nbr_args = sim_request.nbr_args + 1;

    var query = JSON.stringify(sim_request);
    console.log("starting sensor_control_worker: ", query);
    sensor_control_worker.postMessage([sim_request.request_type, query]);

    document.getElementById("red-led").className = "led-red";
    document.getElementById("green-led").className = "";

    startDetections();
  }

  function startPCLSimulation() {
    document.getElementById("db_item_team_info").value =
      "...........PCL tracking started.";
    var sim_request = new request_wrapper();
    sim_request.request_type = "PCL_START";
    sim_request.nbr_args = 0;
    sim_request.args.push(JSON.stringify(team));
    sim_request.nbr_args = sim_request.nbr_args + 1;
    sim_request.args.push(getPCLTargetRCSNew());
    sim_request.nbr_args = sim_request.nbr_args + 1;
    var query = JSON.stringify(sim_request);
    console.log("starting sensor_control_worker: ", query);
    sensor_control_worker.postMessage([sim_request.request_type, query]);

    document.getElementById("red-led").className = "led-red";
    document.getElementById("green-led").className = "";
  }

  function stopRadTracking() {
    document.getElementById("db_item_team_info").value =
      "...........RAD tracking stopped.";
    var sim_request = new request_wrapper();
    sim_request.request_type = "RAD_STOP";
    sim_request.nbr_args = 0;
    sim_request.args.push(JSON.stringify(team));
    sim_request.nbr_args = sim_request.nbr_args + 1;
    var query = JSON.stringify(sim_request);
    sensor_control_worker.postMessage([sim_request.request_type, query]);

    //stopDetections()
  }

  function stopPCLTracking() {
    document.getElementById("db_item_team_info").value =
      "...........PCL tracking stopped.";
    var sim_request = new request_wrapper();
    sim_request.request_type = "PCL_STOP";
    sim_request.nbr_args = 0;
    sim_request.args.push(JSON.stringify(team));
    sim_request.nbr_args = sim_request.nbr_args + 1;
    var query = JSON.stringify(sim_request);
    sensor_control_worker.postMessage([sim_request.request_type, query]);

    //stopDetections()
  }

  // start the simulation of a Air
  function startAirSimulation() {
    document.getElementById("db_item_team_info").value =
      "...........AIR Sim started.";
    var sim_request = new request_wrapper();
    sim_request.request_type = "AIR_START";
    sim_request.nbr_args = 0;
    sim_request.args.push(JSON.stringify(team));
    sim_request.nbr_args = sim_request.nbr_args + 1;
    sim_request.args.push(
      JSON.stringify(
        document.getElementById("update_rate_field").value * 1000.0
      )
    ); // update rate
    sim_request.nbr_args = sim_request.nbr_args + 1;
    sim_request.args.push(
      JSON.stringify(
        document.getElementById("test_track_deletion_time_field").value * 1.0
      )
    ); // test track deletion time
    sim_request.nbr_args = sim_request.nbr_args + 1;
    sim_request.args.push(
      JSON.stringify(
        document.getElementById("ref_track_deletion_time_field").value * 1.0
      )
    ); // ref track deletion time
    sim_request.nbr_args = sim_request.nbr_args + 1;
    var query = JSON.stringify(sim_request);
    //console.log("starting sensor_control_worker: ", query)
    sensor_control_worker.postMessage([sim_request.request_type, query]);

    document.getElementById("red-led").className = "led-red";
    document.getElementById("green-led").className = "";

    sim.simulationRunning = true;
  }
  // stop the simulation of Air targets
  function stopAirSimulation() {
    document.getElementById("red-led").className = "";

    sim.simulationRunning = false;
  }

  function updateWayPoints(
    wayp_id,
    wayp_name,
    poi_name,
    agl_asl,
    targLocArray
  ) {
    for (var i = 0, l = waypoint.three_d_waypoints_array.length; i < l; i++) {
      if (parseInt(waypoint.three_d_waypoints_array[i].id) == wayp_id) {
        waypoint.three_d_waypoints_array[i].targetLocationArray = targLocArray;
        waypoint.three_d_waypoints_array[i].name = wayp_name;
        waypoint.three_d_waypoints_array[i].poi_name = poi_name;
        waypoint.three_d_waypoints_array[i].agl_asl = agl_asl;

        // first remove all elements in the mapLayersArray
        for (
          var u = 0,
            ll = waypoint.three_d_waypoints_array[i].mapLayersArray.length;
          u < ll;
          u++
        ) {
          map.removeLayer(
            waypoint.three_d_waypoints_array[i].mapLayersArray[u]
          );
        }

        // then remove the mapLayersArray element itself
        waypoint.three_d_waypoints_array[i].mapLayersArray = [];

        // now draw the new waypoints on the map
        drawWayPoints(wayp_id);

        // toggle view twice to also show the terrain heig chartshow the waypoints if they were shown before, and otherwise not
        if (waypoint.three_d_waypoints_array[i].shown) {
          toggleWaypointsView(wayp_id); // will make the currently shown invisible
          toggleWaypointsView(wayp_id); // this will load the layers from the targetLocationArray as the layers were set to null when data downloaded from server
        } else {
          toggleWaypointsView(wayp_id);
        }
      }
    }
  }

  function updateWaypointsArrayFromTable() {
    for (
      var i = 2, l = document.getElementById("3d_waypoints_table").rows.length;
      i < l;
      i++
    ) {
      var data = document.getElementById("3d_waypoints_table").rows[i].cells;
      var curr_id = parseInt(data[0].innerHTML);
      for (
        var j = 0, ll = waypoint.three_d_waypoints_array.length;
        j < ll;
        j++
      ) {
        if (parseInt(waypoint.three_d_waypoints_array[j].id) == curr_id) {
          waypoint.three_d_waypoints_array[j].name = String(data[1].innerHTML);
          waypoint.three_d_waypoints_array[j].agl_asl = parseInt(
            data[2].innerHTML
          );
          waypoint.three_d_waypoints_array[j].poi_name = String(
            data[3].innerHTML
          );
        }
      }
    }
    // set next waypId to be greater than the current last one
    var data =
      document.getElementById("3d_waypoints_table").rows[
        document.getElementById("3d_waypoints_table").rows.length - 1
      ].cells;
    runningWaypId = parseInt(data[0].innerHTML) + 1;
  }

  function clearDetections() {
    // removes all detections from DB
    var db_request = new request_wrapper();
    db_request.request_type = "clearDETECTION";
    db_request.nbr_args = 0;
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  function clearRadint() {
    // removes all RADINT rows from DB
    var db_request = new request_wrapper();
    db_request.request_type = "clearRADINT";
    db_request.nbr_args = 0;
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  function clearAirTargets() {
    // removes all AIR Targets from DB
    var db_request = new request_wrapper();
    db_request.request_type = "clearAIR_TARGET";
    db_request.nbr_args = 0;
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  function clearAirWaypoints() {
    // removes all AIR Waypoints from DB
    var db_request = new request_wrapper();
    db_request.request_type = "clearAIR_WAYPOINT";
    db_request.nbr_args = 0;
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  function clearAirPois() {
    // removes all AIR Pois from DB
    var db_request = new request_wrapper();
    db_request.request_type = "clearAIR_POI";
    db_request.nbr_args = 0;
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  function clearAirTargetTriggers() {
    // removes all AIR Triggers from DB
    var db_request = new request_wrapper();
    db_request.request_type = "clearAIR_TRIGGER";
    db_request.nbr_args = 0;
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  function clearAir() {
    clearAirTargets();
    clearAirWaypoints();
    clearAirPois();
    clearAirTargetTriggers();
  }

  function setTargetVelocity() {
    var SELECTED_TARGET_ID = parseInt(
      document.getElementById("targetidinput").value
    );
    var set_vel = parseInt(document.getElementById("targetspeedinput").value);

    if (!isNaN(SELECTED_TARGET_ID)) {
      for (var i = 0, l = targetArray.length; i < l; i++) {
        if (
          targetArray[i].id.toString().endsWith(SELECTED_TARGET_ID.toString())
        ) {
          var db_request = new request_wrapper();
          db_request.request_type = "set_TARGET_VELOCITY";
          db_request.nbr_args = 0;
          db_request.args.push(JSON.stringify(set_vel));
          db_request.nbr_args = db_request.nbr_args + 1;
          db_request.args.push(JSON.stringify(targetArray[i].id));
          db_request.nbr_args = db_request.nbr_args + 1;
          db_request.args.push(JSON.stringify(team));
          db_request.nbr_args = db_request.nbr_args + 1;
          var query = JSON.stringify(db_request);
          sensor_control_worker.postMessage([db_request.request_type, query]);
        }
      }
    }
  }

  function bindEvents() {
    console.log("binding");

    $("#db_table").on("dblclick", "tr", function (e) {
      var row = $(e.currentTarget).index();
      if (row > 0) {
        var rad_id = $("#db_table").children().children()[row]
          .children[0].innerHTML;
        console.log("ID  = ", rad_id);
        setActiveSensorActiveInDB(rad_id);
        clearDBtable();
        fetchRadint();
      }
    });

    $("#set_target_speed").on("click", function () {
      setTargetVelocity();
    });
    $("#reset_target_ticker").on("click", function () {
      resetSimTargetTicker();
    });

    $("#fetch_db_item").on("click", function () {
      clearDBtable();
      var db_item = document.getElementById("db-item-selector").value;
      //console.log("db item = ", db_item)
      switch (db_item) {
        case "RADINT":
          fetchRadint();
          break;
        case "AIR":
          fetchAir();
          break;
        case "PCL_RX":
          fetchPCLRx();
          break;
        //
      }
    });
    $("#insert_db_item").on("click", function () {
      var db_item = document.getElementById("db-item-selector").value;
      switch (db_item) {
        case "RADINT":
          insertRadintToDB();
          break;
        case "AIR":
          insertAirDataToDB();
          break;
        //

        case "PCL_RX":
          insertPCLRxDataToDB();

          insertPCLTxDataToDB();
          break;
        //
      }
    });

    $("#clear_db_item").on("click", function () {
      var db_item = document.getElementById("db-item-selector").value;
      switch (db_item) {
        case "RADINT":
          clearRadint();
          clearDetections();
          break;
        case "AIR":
          clearAir();
          clearDetections();
          break;
        //
      }
    });
    $("#start_db_item_sim").on("click", function () {
      var db_item = document.getElementById("db-item-selector").value;
      switch (db_item) {
        case "RADINT":
          startRadTracking();
          break;
        case "AIR":
          startAirSimulation();
          break;
        case "PCL_RX":
          startPCLSimulation();
          break;
        //
      }
    });
    $("#stop_db_item_sim").on("click", function () {
      var db_item = document.getElementById("db-item-selector").value;
      switch (db_item) {
        case "RADINT":
          stopRadTracking();
          break;
        case "AIR":
          stopAirSimulation();
          break;
        case "PCL_RX":
          stopPCLTracking();
          break;
        //
      }
    });

    $("#setheight").on("click", function () {
      setTargetHeight();
    });
    $("#setTerrainCulisse").on("click", function () {
      setTerrainCulisse();
    });

    $("#save_scenario").on("click", function () {
      saveScenarioLocally();
    });
    $("#read_scenario").on("click", function () {
      readScenarioLocally();
    });
    $("#test").on("click", function () {
      testDynamic();
    });
    $("#goto").on("click", function () {
      gotoLatLon();
    });

    $("#css3-tabstrip-1-3").on("click", function () {
      replayTabSelected();
    });
    $("#css3-tabstrip-0-0").on("click", function () {
      homeTabSelected();
    });

    $("#css3-tabstrip-0-9").on("click", function () {
      if ($("#configure_txs").is(":checked") == true) {
        updatePCLRxTxCallsigns();
      }
    });
    $("#css3-tabstrip-0-60").on("click", function () {
      if ($("#configure_txs").is(":checked") == true) {
        updatePCLRxTxCallsigns();
      }
    });

    $("#find_tx_for_passive_rx").on("click", function () {
      findTxForRx(passive_worker);
    });
    $("#show_rad_patterns").on("click", function () {
      plotTxRadPatternOnMap(map);
    });
    $("#show_LOS_Tx_Rx_lines").on("click", function () {
      drawLinesBetwAllActiveRxAndTx(map);
    });
    $("#deact_all_Tx").on("click", function () {
      setStatusAllTx(0);
    });

    $("#calcPassCoverage").on("click", function () {
      // radio propagation
      var radio_prop_enabled = 0;
      var params = "";
      var radio_prop_params = "";
      if ($("#prop_enabled").is(":checked") == true) {
        radio_prop_enabled = 1;
        console.log("radio prop enabled.........................");
        params = getRadioPropGridShort();
        var query_id = getRandomInt(0, 99999999);
        var oitm = 1;
        if (params[0] == "itwom") {
          oitm = 0;
        }
        var query = new RadioPropQueryShort(
          query_id,
          params[1],
          params[2],
          params[3],
          params[4],
          params[5],
          oitm
        );
        var radio_prop_params = stringifyRadioPropQuery(query);
      }

      calcMinDetRCS(
        nofRunningCoverages,
        passive_worker,
        radio_prop_enabled,
        radio_prop_params
      );
    });
    $("#plotRCScontours").on("click", function () {
      plotRCScontours(geoplot_worker);
    });

    $("#p2pPropDetailedButton").on("click", function () {
      console.log("detailed prop button clicked");
      document.getElementById("prop_txt").value = "";
      document.getElementById("ItemPreview").src =
        "data:image/png;base64," + "";
      document.getElementById("prop_txt").value = "";

      computeDetailedRadioPropagation();
    });
    document.getElementById("prop_txt").value = "";

    $("#load_test_tracks").on("click", function () {
      loadTestTracks();
    });
    $("#load_ref_tracks").on("click", function () {
      loadRefTracks();
    });
    $("#start_replay").on("click", function () {
      startAirSimulation();
      RUN_REPLAY = true;

      ref_file_name = document.getElementById("ref_file_field").value;
      test_file_name = document.getElementById("test_file_field").value;
      sampling_time = document.getElementById("sampling_time_field").value;
      update_rate = document.getElementById("update_rate_field").value;
      ref_track_deletion_time = document.getElementById(
        "ref_track_deletion_time_field"
      ).value;
      test_track_deletion_time = document.getElementById(
        "test_track_deletion_time_field"
      ).value;

      sensor_control_worker.postMessage([
        730678,
        [ref_track_deletion_time, test_track_deletion_time],
      ]); // set the replay target deletion times

      if (document.getElementById("ref_unicode_check").checked) {
        ref_track_id_is_unicode = 1;
      } else {
        ref_track_id_is_unicode = 0;
      }
      if (document.getElementById("test_unicode_check").checked) {
        test_track_id_is_unicode = 1;
      } else {
        test_track_id_is_unicode = 0;
      }

      if (
        ref_file_name.length == 0 ||
        test_file_name.length == 0 ||
        sampling_time.length == 0 ||
        update_rate.length == 0 ||
        ref_track_deletion_time.length == 0 ||
        test_track_deletion_time.length == 0 ||
        isNaN(parseInt(sampling_time)) ||
        isNaN(parseFloat(update_rate)) ||
        isNaN(parseInt(ref_track_deletion_time)) ||
        isNaN(parseInt(test_track_deletion_time))
      ) {
        alert("Please complete all inputs.");
      } else {
        REF_TARGET_INITIAL_STATUS =
          Math.ceil(
            parseFloat(ref_track_deletion_time) / parseFloat(sampling_time)
          ) + 1;
        TEST_TARGET_INITIAL_STATUS =
          Math.ceil(
            parseFloat(test_track_deletion_time) / parseFloat(sampling_time)
          ) + 1;
        var test_track_del_time =
          document.getElementById("test_track_deletion_time_field").value * 1.0; // test track deletion time
        var ref_track_deletion_time =
          document.getElementById("ref_track_deletion_time_field").value * 1.0; // ref track deletion time
        var tgt_rcs = document.getElementById("coverage_rcs").value; // tgt rcs [m2]
        console.log("tgt_tcs = ", tgt_rcs);

        startReplay(
          ref_file_name,
          test_file_name,
          sampling_time,
          update_rate,
          test_track_del_time,
          ref_track_deletion_time,
          replay_worker,
          tgt_rcs
        );
      }
    });

    $("#stop_replay").on("click", function () {
      forceKillAllTargets();
      removeDeadTargets();
      stopReplay(replay_worker);
      stopAirSimulation();
      removeAllReplaytargets();
    });
    $("#ref_file_button").on("click", function () {
      downloadReplayRefFile();
    });
    $("#test_file_button").on("click", function () {
      downloadReplayTestFile();
    });

    $("#download_kml_file_button").on("click", function () {
      downloadKMLFile();
    });
    $("#clear_kml_table").on("click", function () {
      var table = document.getElementById("kml_table");
      var rowCount = table.rows.length;
      while (rowCount > 1) {
        table.deleteRow(rowCount - 1);
        rowCount = table.rows.length;
      }

      deleteKMLTracks();
    });
  }

  function replayTabSelected() {}

  function updateTargetCirclesArray() {
    for (var j = 0, ll = targetArray.length; j < ll; j++) {
      var curid = parseInt(targetArray[j].id);
      for (var jj = 0, lll = targetArray[j].noftargets; jj < lll; jj++) {
        var targ = new TargetCircle(curid);
        targetCircleArray.push(targ);
        curid++;
      }
    }
  }

  function homeTabSelected() {
    map.updateSize();
  }

  function updatePOIfromTable() {
    var data = document.getElementById("poi_table").rows[2].cells;
    poi.name = String(data[1].innerHTML);
    poi.lat = parseFloat(data[2].innerHTML);
    poi.lon = parseFloat(data[3].innerHTML);
    poi.id = parseInt(data[0].innerHTML);
  }

  function resetSimTargetTicker() {}

  function initReplayAnalysis() {}

  function setReplayAnalysis(mdts, sp, load, noftargs, reptime, realtime) {
    console.log(
      "total objects in sky = " +
        noftargs.toString() +
        ", replay data time[s]: " +
        reptime.toString() +
        ", real replay time[s]: " +
        realtime.toString()
    );
  }

  function initTimeAnalysis() {}

  function resetTargetArray() {
    targetArray = [];
  }

  function resetSpaceAnalysis() {}

  function removeWayPointsFromMap() {
    for (var i = 0, l = tmpLayersArray.length; i < l; i++) {
      map.removeLayer(tmpLayersArray[i]);
    }
    tmpLayersArray = [];
  }

  function gotoLatLon() {
    var lat = parseFloat(document.getElementById("lat2d").value);
    var lon = parseFloat(document.getElementById("lon2d").value);

    var curr_ort = ol.proj.fromLonLat([lon, lat]);
    view.setCenter(curr_ort);
    gotoLatLonMap(lat, lon);
  }

  function toDecimal(deg, min, sec) {
    return deg + min / 60 + sec / 3600;
  }

  /////////////////////////////////// functions to debug WORKER-----------------------------------

  // computes slippy map x,y given zoom,lat,lon

  function long2tile(lon, zoom) {
    return Math.floor(((lon + 180) / 360) * Math.pow(2, zoom));
  }

  function lat2tile(lat, zoom) {
    return Math.floor(
      ((1 -
        Math.log(
          Math.tan((lat * Math.PI) / 180) + 1 / Math.cos((lat * Math.PI) / 180)
        ) /
          Math.PI) /
        2) *
        Math.pow(2, zoom)
    );
  }

  //http://oms.wff.ch/calc.htm
  //http://wiki.openstreetmap.org/wiki/Zoom_levels
  function setMidSlippyXY(lat_deg, lon_deg, zoom) {
    mid_tile_x = long2tile(lon_deg, zoom);
    mid_tile_y = lat2tile(lat_deg, zoom);
  }

  function getSlippyXY(index) {
    var retval = [mid_tile_x, mid_tile_y];
    // mid_tile_x, mid_tile_y

    var tmp1 = index % anz_x;
    var tmp2 = anz_x / 2 - tmp1;
    retval[0] = mid_tile_x - tmp2;

    var tmp3 = Math.floor(index / anz_y);
    var tmp4 = Math.round(anz_y / 2) - tmp3;
    retval[1] = mid_tile_y + tmp4;

    return retval;
  }

  function addFlightAndTerrainHeightsToChart(
    dNr,
    terrain_height,
    flight_height
  ) {}

  function addHeightSeries(dataNr, terrain_height, flight_height) {}

  function addWayPointRow() {
    // in the beginning simply add a row to the 3D waypoints table
    var $TABLE = $("#3d_waypoints_table_div");
    var $clone = $TABLE
      .find("tr.hide")
      .clone(true)
      .removeClass("hide table-line");
    $TABLE.find("table").append($clone);
    var x = document.getElementById("3d_waypoints_table").rows.length;
    var data = document.getElementById("3d_waypoints_table").rows[x - 1].cells;
    data[0].innerHTML = runningWaypId;
  }

  function addPositionToTrack() {
    // -------------------add this track poition to the track array
    var track = new TrackPosition();
    track.lat = curr_lat;
    track.lon = curr_lon;
    track.z = targetHeight;

    // ... more attributes to add
    track.terrainHeight = terrain_mid_point_height;
    track.delta_x_kms = radar_delta_x_kms * -1; // we place the track relative to the radar! (so if radar moved this will be invalid)
    track.delta_y_kms = radar_delta_y_kms * -1; // we place the track relative to the radar!(so if radar moved this will be invalid)
    track.z = targetHeight; //flight_mesh.position.z;

    // draw a line to the previous track position
    if (targetLocationArray.length > 1) {
      var currPos = targetLocationArray[targetLocationArray.length - 1];
      var prevPos = targetLocationArray[targetLocationArray.length - 2];

      var pos1 = ol.proj.transform(
        [
          targetLocationArray[targetLocationArray.length - 2].lon,
          targetLocationArray[targetLocationArray.length - 2].lat,
        ],
        "EPSG:4326",
        "EPSG:3857"
      );
      var pos2 = ol.proj.transform(
        [
          targetLocationArray[targetLocationArray.length - 1].lon,
          targetLocationArray[targetLocationArray.length - 1].lat,
        ],
        "EPSG:4326",
        "EPSG:3857"
      );
      var coordinates = [pos1, pos2];

      var coord_new = ol.proj.transform(coordinates, "EPSG:4326", "EPSG:3857");
      var layerLines = new ol.layer.Vector({
        source: new ol.source.Vector({
          features: [
            new ol.Feature({
              geometry: new ol.geom.LineString(coordinates),
              name: "track",
            }),
          ],
        }),
      });

      layerLines.setStyle(hostile_line_style);
      map.addLayer(layerLines);

      tmpLayersArray.push(layerLines);

      addLayerLinesToTargetLocationArray(layerLines);
    }
  }

  function addLayerLinesToTargetLocationArray(layerlines) {
    mapLayersArray.push(layerlines);
  }

  function onDocumentKeyRelease(event) {
    var keyCode = event.which;

    // F1: create new target
    if (keyCode == 112) {
      if (sim.simulationRunning) {
        alert("Please stop running simulation.");
      } else {
        if (TARGET_GUI_ACTION != 3) {
          alert(
            "Please add atleast two waypoints for the current target, or finish waypoint collection for current traget (F3)"
          );
        } else {
          if (targetLocationArray.length > 0) {
            alert("Please press F3 to save the waypoints of current target...");
          } else {
            document.getElementById("yellow-led").className = "led-yellow";

            // reset the space charts
            resetSpaceAnalysis();

            // add a waypoint row, as each target needs a waypoint array
            addWayPointRow();
            runningWaypId++;
            addTargetRow();

            // update the target array
            console.log("running Target ID = ", runningTargetID);
            var target = new Target(
              sim.TARGET_PARAM_ID,
              runningTargetID,
              -1,
              "noname",
              1,
              -1,
              -1,
              1,
              "G",
              "",
              1
            );

            targetArray.push(target);
            updateTargetArrayFromTable();

            currentActiveTargetID = runningTargetID;
            runningTargetID = runningTargetID + 11; // allow some space of IDs because each target can be set to consist of many (we assume it will be less than 10)

            TARGET_GUI_ACTION = 1;
          }
        }
      }
    }

    // F2: capture waypoint for current target
    else if (keyCode == 113) {
      if (currentActiveTargetID < 0) {
        alert("Please add a target first by pressing F1...");
      } else {
        if (TARGET_GUI_ACTION < 0 || TARGET_GUI_ACTION == 3) {
          alert("Please add a new target first...");
        } else {
          TARGET_GUI_ACTION = 2;

          var tgtLoc = new TargetLocation(
            sim.TRACK_LOCATION_PARAM_ID,
            dataNr,
            curr_lat,
            curr_lon,
            terrain_mid_point_height,
            targetHeight
          );
          addHeightSeries(dataNr, terrain_mid_point_height, targetHeight);
          targetLocationArray.push(tgtLoc);

          dataNr++;
          totalPds = 0;
          addPositionToTrack(); // this will draw an extra marker at this flight location
        }
      }
    }
    // F3: finish waypoints for current target
    else if (keyCode == 114) {
      if (currentActiveTargetID < 0) {
        alert("Please add a target first by pressing F1...");
      } else {
        if (targetLocationArray.length < 2) {
          alert("Please add atleast 2 waypoints by pressing F2 ...");
        } else {
          document.getElementById("yellow-led").className = "";

          var wayp_id, wayp_name, poi_name, agl_asl;

          var y = document.getElementById("3d_waypoints_table").rows.length;
          var datay =
            document.getElementById("3d_waypoints_table").rows[y - 1].cells;

          wayp_id = parseInt(datay[0].innerHTML);
          wayp_name = String(datay[1].innerHTML);
          agl_asl = parseInt(datay[2].innerHTML);
          poi_name = String(datay[3].innerHTML);

          var threeD_wayp = new ThreeD_Waypoints(
            sim.THREE_D_WAYPOINTS_PARAM_ID,
            wayp_id,
            wayp_name,
            poi_name,
            agl_asl
          );
          threeD_wayp.targetLocationArray = targetLocationArray;
          threeD_wayp.mapLayersArray = mapLayersArray;
          waypoint.three_d_waypoints_array.push(threeD_wayp);

          // reset the SPACE charts 1 and 2 (because now a new target was created)
          resetSpaceAnalysis();

          // also reset the targetLocationArray
          resetTargetLocationArray();

          TARGET_GUI_ACTION = 3;
        }
      }
    }

    // c: compute radar coverage
    else if (keyCode == 67) {
      // used to be 120 for F9, now its just c
      var selected_sensor = document.getElementById("sensor-selector").value;
      switch (selected_sensor) {
        case "RADINT":
          if (nofRunningCoverages < 1) {
            // i.e. if all running coverage computations are finished
            // update the sensor array from the html
            updateSensorArrayFromTable();

            // update the target array from the html
            updateTargetArrayFromTable();
            var rcs = getTargetRCSNew();
            var str =
              "coverage at height: " +
              String(targetHeight) +
              "[masl], for tgt. rcs: " +
              String(rcs);
            $("#infobox").text(str);

            // now compute coverage for each radar
            for (var i = 0, l = activeMonostaticArray.length; i < l; i++) {
              var rcs = getTargetRCSNew();

              if (activeMonostaticArray[i].status == 1) {
                nofRunningCoverages++;
                var radio_prop_en = 0;
                if ($("#prop_enabled").is(":checked") == true) {
                  radio_prop_en = 1;
                }
                var agl_enabled = 0;
                if ($("#magl_enabled").is(":checked") == true) {
                  agl_enabled = 1;
                }
                pdf_worker.postMessage([
                  559765,
                  parseInt(activeMonostaticArray[i].id_nr),
                  parseFloat(activeMonostaticArray[i].lat),
                  parseFloat(activeMonostaticArray[i].lon),
                  targetHeight,
                  activeMonostaticArray[i].power,
                  activeMonostaticArray[i].antenna_diam,
                  activeMonostaticArray[i].freq,
                  activeMonostaticArray[i].pulse_width,
                  activeMonostaticArray[i].cpi_pulses,
                  activeMonostaticArray[i].bandwidth,
                  activeMonostaticArray[i].pfa,
                  rcs,
                  activeMonostaticArray[i].min_elevation,
                  activeMonostaticArray[i].max_elevation,
                  radio_prop_en,
                  agl_enabled,
                ]);
              }
            }
            document.getElementById("blue-led").className = "led-blue";
            alert("Computing RADINT coverage");
          } else {
            alert(
              "Please wait for running radar coverage computation to finish..."
            );
          }
          break;
        case "PET":
          console.log("in PET coverage");
          updatePETSensorArrayFromTable();
          var pet_request = new request_wrapper();
          pet_request.request_type = "computeCoverage";
          pet_request.nbr_args = 0;
          nofRunningCoverages++;
          for (var i = 0, l = petArray.length; i < l; i++) {
            if (petArray[i].status == 1) {
              // the coverage of the first active sensor only
              //rad_id, rad_lat, rad_lon, flight_height, erp_dbm, threshold_dbm, freq, radioprop_enabled, lat_min, lat_max, lon_min, lon_max

              freq = document.getElementById("pet_coverage_freq").value; // GHz //

              pet_request.args.push(JSON.stringify(petArray[i].id_nr));
              pet_request.nbr_args = pet_request.nbr_args + 1;
              pet_request.args.push(JSON.stringify(petArray[i].lat));
              pet_request.nbr_args = pet_request.nbr_args + 1;
              pet_request.args.push(JSON.stringify(petArray[i].lon));
              pet_request.nbr_args = pet_request.nbr_args + 1;
              var flightHeight = getTargetHeight();
              pet_request.args.push(JSON.stringify(flightHeight));
              pet_request.nbr_args = pet_request.nbr_args + 1;
              var erp_dbm = getTargetERP();
              pet_request.args.push(JSON.stringify(erp_dbm));
              pet_request.nbr_args = pet_request.nbr_args + 1;
              pet_request.args.push(JSON.stringify(petArray[i].threshold));
              pet_request.nbr_args = pet_request.nbr_args + 1;
              pet_request.args.push(JSON.stringify(freq));
              pet_request.nbr_args = pet_request.nbr_args + 1;
              var radio_prop_enabled = 0;
              if ($("#prop_enabled").is(":checked") == true) {
                radio_prop_enabled = 1;
              }
              pet_request.args.push(JSON.stringify(radio_prop_enabled));
              pet_request.nbr_args = pet_request.nbr_args + 1;
              var [lat_min, lat_max, lon_min, lon_max] = getPetGrid();
              pet_request.args.push(JSON.stringify(lat_min));
              pet_request.nbr_args = pet_request.nbr_args + 1;
              pet_request.args.push(JSON.stringify(lat_max));
              pet_request.nbr_args = pet_request.nbr_args + 1;
              pet_request.args.push(JSON.stringify(lon_min));
              pet_request.nbr_args = pet_request.nbr_args + 1;
              pet_request.args.push(JSON.stringify(lon_max));
              pet_request.nbr_args = pet_request.nbr_args + 1;

              pet_request.args.push(
                JSON.stringify(petArray[i].use_antenna_diag)
              );
              pet_request.nbr_args = pet_request.nbr_args + 1;
              pet_request.args.push(
                JSON.stringify(petArray[i].main_beam_azimuth)
              );
              pet_request.nbr_args = pet_request.nbr_args + 1;
              pet_request.args.push(
                JSON.stringify(petArray[i].main_beam_elevation)
              );
              pet_request.nbr_args = pet_request.nbr_args + 1;

              var magl_enabled = 0;
              if ($("#magl_enabled").is(":checked") == true) {
                magl_enabled = 1;
              }
              pet_request.args.push(JSON.stringify(magl_enabled));
              pet_request.nbr_args = pet_request.nbr_args + 1;

              var query = JSON.stringify(pet_request); //////
              pet_worker.postMessage([pet_request.request_type, query]);

              break;
            }
          }

          break;
      }
    }
  }

  //------------------------------------------------3D Mesh FUNCTIONS --------------------------------

  function testDynamic() {
    removeAllTempObjects();
    // debugging
    cur_pdf = Math.random();
    cur_snr = Math.random();
  }

  function updatePOIPosition(data) {
    var theText = data;
    var res = theText.split(",");
    var delta_x_dem_pixels = parseInt(res[1]);
    var delta_y_dem_pixels = parseInt(res[2]);
    var height = parseInt(res[3]);
    var id = parseInt(res[4]);

    var delta_x_plane =
      (-1 * (elem_width * delta_x_dem_pixels * 25.0)) / plane_width_meters;
    var delta_y_plane =
      (elem_width * delta_y_dem_pixels * 25.0) / plane_width_meters;
  }

  function getRoadBlockCircle(curr_ort, id) {
    var road_circle = new ol.geom.Circle(
      ol.proj.transform([1.5, 5.5], "EPSG:4326", "EPSG:3857"),
      200
    );
    var circleFeatureRoad = new ol.Feature(road_circle);
    var roadFeatureOverlay = new ol.FeatureOverlay({
      map: map,
      features: [circleFeatureRoad],
      style: new ol.style.Style({
        fill: new ol.style.Fill({
          color: "rgba(120, 120, 50, 0.3)",
        }),
        stroke: new ol.style.Stroke({
          width: 4,
          color: "rgba(120, 120, 50, 0.8)",
        }),
        text: new ol.style.Text({
          text: id.toString(),
          scale: 1.3,
          fill: new ol.style.Fill({
            color: "#000000",
          }),
          stroke: new ol.style.Stroke({
            color: "#987000",
            width: 3.5,
          }),
        }),
      }),
    });
    road_circle.setCenter(curr_ort);
    return road_circle;
  }

  function getRadarCircle(curr_ort, id) {
    var radar_circle = new ol.geom.Circle(
      ol.proj.transform([1.5, 5.5], "EPSG:4326", "EPSG:3857"),
      200
    );
    var circleFeatureRadar = new ol.Feature(radar_circle);
    var radarFeatureOverlay = new ol.FeatureOverlay({
      map: map,
      features: [circleFeatureRadar],
      style: new ol.style.Style({
        fill: new ol.style.Fill({
          color: "rgba(220, 50, 50, 0.3)",
        }),
        stroke: new ol.style.Stroke({
          width: 4,
          color: "rgba(220, 10, 10, 0.8)",
        }),
        text: new ol.style.Text({
          text: id.toString(),
          scale: 1.3,
          fill: new ol.style.Fill({
            color: "#000000",
          }),
          stroke: new ol.style.Stroke({
            color: "#FFFF99",
            width: 3.5,
          }),
        }),
      }),
    });
    radar_circle.setCenter(curr_ort);
    return radar_circle;
  }

  // -------------------------------------------------2D Map and general Functions--------------------------------

  function removeWayPointsLayerFromMap(waypointsID) {
    for (var j = 0, ll = waypoint.three_d_waypoints_array.length; j < ll; j++) {
      if (parseInt(waypoint.three_d_waypoints_array[j].id) == waypointsID) {
        for (
          var i = 0,
            l = waypoint.three_d_waypoints_array[j].mapLayersArray.length;
          i < l;
          i++
        ) {
          map.removeLayer(
            waypoint.three_d_waypoints_array[j].mapLayersArray[i]
          );
        }
      }
    }
  }

  // move the flight circle on the 2D map
  function changeFlightLocationOnMap(c_lat, c_lon) {
    var curr_ort = ol.proj.fromLonLat([c_lon, c_lat]);

    flight_circle.setCenter(curr_ort);
  }

  function onLeftDoubleClick(event) {
    if (event.which == 1) {
      // left mouse button

      var $div = $(event.target);
      var offset = $div.offset();
      var cur_x = event.clientX - offset.left;
      var cur_y = event.clientY - offset.top;
    }
  }

  // debugging to add a new points to heatmap
  function addPointsToHeatMap(points) {
    // this should get the new set of points as input

    // first remove the currently layer
    map.removeLayer(heatMapLayer);

    // now make the new data
    var data = new ol.source.Vector();

    // created for owl range of data
    var tmp1 = Math.random() - 0.5;
    var lat1 = 47.0 + tmp1;
    var tmp11 = Math.random() - 0.5;
    var lon1 = 7.0 + tmp11;

    var tmp2 = Math.random() - 0.5;
    var lat2 = 47.0 + tmp2;
    var tmp22 = Math.random() - 0.5;
    var lon2 = 7.0 + tmp22;

    var tmp3 = Math.random() - 0.5;
    var lat3 = 47.0 + tmp3;
    var tmp33 = Math.random() - 0.5;
    var lon3 = 7.0 + tmp33;

    var coord1 = ol.proj.transform([lon1, lat1], "EPSG:4326", "EPSG:3857");
    var lonLat1 = new ol.geom.Point(coord1);
    var coord2 = ol.proj.transform([lon2, lat2], "EPSG:4326", "EPSG:3857");
    var lonLat2 = new ol.geom.Point(coord2);
    var coord3 = ol.proj.transform([lon3, lat3], "EPSG:4326", "EPSG:3857");
    var lonLat3 = new ol.geom.Point(coord3);

    var pointFeature1 = new ol.Feature({
      geometry: lonLat1,
      weight: 0.5, // min:0 max:1
    });
    var pointFeature2 = new ol.Feature({
      geometry: lonLat2,
      weight: 0.7, // min:0 max:1
    });
    var pointFeature3 = new ol.Feature({
      geometry: lonLat3,
      weight: 0.9, // min:0 max:1
    });

    data.addFeature(pointFeature1);
    data.addFeature(pointFeature2);
    data.addFeature(pointFeature3);

    // set the new source
    heatMapLayer.setSource(data);

    // add to the map
    map.addLayer(heatMapLayer);
  }

  function addRadRowWithID(id) {
    var $TABLE = $("#active_sensor_table_div");
    var $clone = $TABLE
      .find("tr.hide")
      .clone(true)
      .removeClass("hide table-line");
    $TABLE.find("table").append($clone);

    var x = document.getElementById("active_sensor_table").rows.length;
    var data = document.getElementById("active_sensor_table").rows[x - 1].cells;
    data[0].innerHTML = id;
  }

  function addTargetRowWithID(id) {
    var $TABLE = $("#target_table_div");
    var $clone = $TABLE
      .find("tr.hide")
      .clone(true)
      .removeClass("hide table-line");
    $TABLE.find("table").append($clone);

    var x = document.getElementById("target_table").rows.length;
    var data = document.getElementById("target_table").rows[x - 1].cells;
    data[0].innerHTML = id;
  }

  function addTargetRow() {
    var $TABLE = $("#target_table_div");

    var $clone = $TABLE
      .find("tr.hide")
      .clone(true)
      .removeClass("hide table-line");
    $TABLE.find("table").append($clone);

    var x = document.getElementById("target_table").rows.length;
    var data = document.getElementById("target_table").rows[x - 1].cells;
    data[0].innerHTML = runningTargetID;
    data[8].innerHTML = runningWaypId - 1;
    data[7].innerHTML = 1; // running
    data[9].innerHTML = 1; // status
  }

  function addPETSensorRowLatLon(lat, lon) {
    var $TABLE = $("#pet_sensor_table_div");

    var $clone = $TABLE
      .find("tr.hide")
      .clone(true)
      .removeClass("hide table-line");
    $TABLE.find("table").append($clone);

    var x = document.getElementById("pet_sensor_table").rows.length;
    var data = document.getElementById("pet_sensor_table").rows[x - 1].cells;

    data[0].innerHTML = runningSensorID;
    data[1].innerHTML = "?";
    data[2].innerHTML = "1";
    data[3].innerHTML = lat;
    data[4].innerHTML = lon;
    data[5].innerHTML = "-75";
  }
  function addRoadBlockLatLon(lat, lon) {
    var $TABLE = $("#road_block_table_div");

    var $clone = $TABLE
      .find("tr.hide")
      .clone(true)
      .removeClass("hide table-line");
    $TABLE.find("table").append($clone);

    var x = document.getElementById("road_block_table").rows.length;
    var data = document.getElementById("road_block_table").rows[x - 1].cells;
    console.log("nof rows = ", x, ", cell data before = ", data[0].innerHTML);
    data[0].innerHTML = runningRoadBlockID;
    data[3].innerHTML = lat;
    data[4].innerHTML = lon;
  }

  function addSensorRowLatLon(
    lat,
    lon,
    pow = null,
    status = null,
    antenna_diam = null,
    freq = null,
    cpi_pulses = null,
    bandwidth = null,
    pfa = null,
    rot_time = null,
    category = null,
    pulse_width = null,
    name = null
  ) {
    var $TABLE = $("#active_sensor_table_div");

    var $clone = $TABLE
      .find("tr.hide")
      .clone(true)
      .removeClass("hide table-line");
    $TABLE.find("table").append($clone);

    var x = document.getElementById("active_sensor_table").rows.length;
    var data = document.getElementById("active_sensor_table").rows[x - 1].cells;
    data[0].innerHTML = runningSensorID;

    data[3].innerHTML = lat;
    data[4].innerHTML = lon;

    if (pow != null) {
      data[5].innerHTML = pow;
    }
    if (status != null) {
      data[2].innerHTML = status;
    }
    if (antenna_diam != null) {
      data[6].innerHTML = antenna_diam;
    }
    if (freq != null) {
      data[7].innerHTML = freq;
    }
    if (pulse_width != null) {
      data[8].innerHTML = pulse_width;
    }
    if (cpi_pulses != null) {
      data[9].innerHTML = cpi_pulses;
    }
    if (bandwidth != null) {
      data[10].innerHTML = bandwidth;
    }
    if (pfa != null) {
      data[11].innerHTML = pfa;
    }
    if (rot_time != null) {
      data[12].innerHTML = rot_time;
    }
    if (category != null) {
      data[13].innerHTML = category;
    }
    if (name != null) {
      data[1].innerHTML = name;
    }
  }

  // adds a new PET Rx
  function addNewPETRx(lat, lon) {
    var curr_ort = ol.proj.fromLonLat([lon, lat]);

    // add circle to 2D map
    var radar_circle = new ol.geom.Circle(
      ol.proj.transform([1.5, 5.5], "EPSG:4326", "EPSG:3857"),
      200
    );
    var circleFeatureRadar = new ol.Feature(radar_circle);
    var radarFeatureOverlay = new ol.FeatureOverlay({
      map: map,
      features: [circleFeatureRadar],
      style: new ol.style.Style({
        fill: new ol.style.Fill({
          color: "rgba(10, 100, 200, 0.3)",
        }),
        stroke: new ol.style.Stroke({
          width: 4,
          color: "rgba(10, 100, 200, 0.8)",
        }),
        text: new ol.style.Text({
          text: runningSensorID.toString(),
          scale: 1.3,
          fill: new ol.style.Fill({
            color: "rgba(220, 220, 220, 0.8)",
          }),
          stroke: new ol.style.Stroke({
            color: "#0000FF",
            width: 3.5,
          }),
        }),
      }),
    });
    radar_circle.setCenter(curr_ort);

    // add row to sensor table
    addPETSensorRowLatLon(lat, lon);

    // update the pet radar array
    var pet_sensor = new PetSensor(
      sim.PET_SENSOR_PARAM_ID,
      runningSensorID,
      "?",
      1,
      lat,
      lon,
      -75,
      terrain_mid_point_height
    ); //
    petArray.push(pet_sensor);
    runningSensorID++;
  }

  // add a new active monostatic sensor
  function addNewActiveMonostaticSensor(
    c_lat,
    c_lon,
    pow = null,
    status = null,
    antenna_diam = null,
    freq = null,
    cpi_pulses = null,
    bandwidth = null,
    pfa = null,
    rot_time = null,
    category = null,
    pulse_width,
    name = null
  ) {
    var curr_ort = ol.proj.fromLonLat([c_lon, c_lat]);

    // add circle to 2D map
    var radar_circle = getRadarCircle(curr_ort, runningSensorID);

    // add row to sensor table
    addSensorRowLatLon(
      c_lat,
      c_lon,
      pow,
      status,
      antenna_diam,
      freq,
      cpi_pulses,
      bandwidth,
      pfa,
      rot_time,
      category,
      pulse_width,
      name
    );

    // update the radar array
    var sensor = new ActiveMonostaticSensor(
      sim.ACTIVE_MONOSTATIC_SENSOR_PARAM_ID,
      runningSensorID,
      "",
      c_lat,
      c_lon,
      radar_circle
    );
    activeMonostaticArray.push(sensor);

    var sens_arr = [];
    for (var i = 0, l = activeMonostaticArray.length; i < l; i++) {
      sens_arr.push(activeMonostaticArray[i].id_nr.toString());
    }

    // increment the sensor ID
    runningSensorID++;
  }

  function updatePETSensorArrayFromTable() {
    for (
      var i = 2, l = document.getElementById("pet_sensor_table").rows.length;
      i < l;
      i++
    ) {
      var data = document.getElementById("pet_sensor_table").rows[i].cells;
      var curr_id = parseInt(data[0].innerHTML);
      for (var j = 0, ll = petArray.length; j < ll; j++) {
        if (parseInt(petArray[j].id_nr) == curr_id) {
          petArray[j].name = data[1].innerHTML;
          petArray[j].status = parseInt(data[2].innerHTML);
          petArray[j].lat = parseFloat(data[3].innerHTML);
          petArray[j].lon = parseFloat(data[4].innerHTML);
          petArray[j].threshold = parseFloat(data[5].innerHTML);
          petArray[j].use_antenna_diag = parseFloat(data[6].innerHTML);
          petArray[j].main_beam_azimuth = parseFloat(data[7].innerHTML);
          petArray[j].main_beam_elevation = parseFloat(data[8].innerHTML);
        }
      }
    }
  }

  function updateSensorArrayFromTable() {
    for (
      var i = 2, l = document.getElementById("active_sensor_table").rows.length;
      i < l;
      i++
    ) {
      var data = document.getElementById("active_sensor_table").rows[i].cells;
      var curr_id = parseInt(data[0].innerHTML);
      for (var j = 0, ll = activeMonostaticArray.length; j < ll; j++) {
        if (parseInt(activeMonostaticArray[j].id_nr) == curr_id) {
          activeMonostaticArray[j].power = parseInt(data[5].innerHTML);
          activeMonostaticArray[j].antenna_diam = parseFloat(data[6].innerHTML);
          activeMonostaticArray[j].freq = parseFloat(data[7].innerHTML);
          activeMonostaticArray[j].pulse_width = parseFloat(data[8].innerHTML);
          activeMonostaticArray[j].cpi_pulses = parseInt(data[9].innerHTML);
          activeMonostaticArray[j].bandwidth = parseFloat(data[10].innerHTML);
          activeMonostaticArray[j].pfa = parseFloat(data[11].innerHTML);
          activeMonostaticArray[j].status = parseInt(data[2].innerHTML);
          activeMonostaticArray[j].rotation_time = parseInt(data[12].innerHTML);
          activeMonostaticArray[j].category = parseInt(data[13].innerHTML);
          activeMonostaticArray[j].name = String(data[1].innerHTML);
          activeMonostaticArray[j].status = parseInt(data[2].innerHTML);
          activeMonostaticArray[j].lat = parseFloat(data[3].innerHTML); // this is necessary as this changes when a dispo is uploaded
          activeMonostaticArray[j].lon = parseFloat(data[4].innerHTML); // this is necessary as this changes when a dispo is uploaded

          activeMonostaticArray[j].min_elevation = parseFloat(
            data[14].innerHTML
          );
          activeMonostaticArray[j].max_elevation = parseFloat(
            data[15].innerHTML
          );
          activeMonostaticArray[j].orientation = parseFloat(data[16].innerHTML);
          activeMonostaticArray[j].horiz_aperture = parseFloat(
            data[17].innerHTML
          );
          activeMonostaticArray[j].min_detection_range = parseFloat(
            data[18].innerHTML
          );
          activeMonostaticArray[j].max_detection_range = parseFloat(
            data[19].innerHTML
          );
          activeMonostaticArray[j].min_detection_height = parseFloat(
            data[20].innerHTML
          );
          activeMonostaticArray[j].max_detection_height = parseFloat(
            data[21].innerHTML
          );
          activeMonostaticArray[j].min_detection_tgt_speed = parseFloat(
            data[22].innerHTML
          );
          activeMonostaticArray[j].max_detection_tgt_speed = parseFloat(
            data[23].innerHTML
          );
        }
      }
    }
  }

  function updateTableDataFromSensor(data, sensor) {
    data[5].innerHTML = sensor.pow;
    data[6].innerHTML = sensor.antenna_diam;
    data[7].innerHTML = sensor.freq;
    data[8].innerHTML = sensor.pulse_width;
    data[9].innerHTML = sensor.cpi_pulses;
    data[10].innerHTML = sensor.bandwidth;
    data[11].innerHTML = sensor.pfa;
    data[2].innerHTML = sensor.status;
    data[12].innerHTML = sensor.rotation_time;
    data[13].innerHTML = sensor.category;
    data[1].innerHTML = sensor.name;
    data[2].innerHTML = sensor.status;

    data[14].innerHTML = sensor.min_elevation;
    data[15].innerHTML = sensor.max_elevation;
    data[16].innerHTML = sensor.orientation;
    data[17].innerHTML = sensor.horiz_aperture;
    data[18].innerHTML = sensor.min_detection_range;
    data[19].innerHTML = sensor.max_detection_range;
    data[20].innerHTML = sensor.min_detection_height;
    data[21].innerHTML = sensor.max_detection_height;
    data[22].innerHTML = sensor.min_detection_tgt_speed;
    data[23].innerHTML = sensor.max_detection_tgt_speed;
  }

  function toggleWaypointsView(id) {
    var ind = -1;
    for (var i = 0, l = three_d_waypoints_array.length; i < l; i++) {
      if (parseInt(three_d_waypoints_array[i].id) == id) {
        ind = i;
        break;
      }
    }

    if (ind > -1) {
      // reset the space charts
      resetSpaceAnalysis();
      var dNr = 0;
      // if the waypoint was imported from the server it does not have any maplayers
      if (
        three_d_waypoints_array[ind].mapLayersArray == null ||
        three_d_waypoints_array[ind].mapLayersArray.length == 0
      ) {
        drawWayPoints(three_d_waypoints_array[ind].id);
      } else {
        // i.e. if map layer exists
        for (
          var i = 0, l = three_d_waypoints_array[ind].mapLayersArray.length;
          i < l;
          i++
        ) {
          if (three_d_waypoints_array[ind].mapLayersArray[i].getVisible()) {
            //
            three_d_waypoints_array[ind].mapLayersArray[i].setVisible(false);
            three_d_waypoints_array[ind].shown = false;
          } else {
            three_d_waypoints_array[ind].mapLayersArray[i].setVisible(true);
            three_d_waypoints_array[ind].shown = true;
            // draw flight and terrain chart
            var terrain_height =
              three_d_waypoints_array[ind].targetLocationArray[i].terrainHeight;
            var flight_height =
              three_d_waypoints_array[ind].targetLocationArray[i].flightHeight;
            addFlightAndTerrainHeightsToChart(
              dNr,
              terrain_height,
              flight_height
            );

            dNr++;
            if (i == three_d_waypoints_array[ind].mapLayersArray.length - 1) {
              // draw the last point (there is one point more than there are lines)
              var terrain_height =
                three_d_waypoints_array[ind].targetLocationArray[i + 1]
                  .terrainHeight;
              var flight_height =
                three_d_waypoints_array[ind].targetLocationArray[i + 1]
                  .flightHeight;
              addFlightAndTerrainHeightsToChart(
                dNr,
                terrain_height,
                flight_height
              );
            }
          }
        }
      }
    }
  }

  function removeWaypoint($row) {
    var id = $row.text().split("\n")[1].trim();
    removeWayPointsLayerFromMap(id);

    // now go through the array and remove the featurefind the index
    var ind = -1;
    for (var i = 0, l = waypoint.three_d_waypoints_array.length; i < l; i++) {
      if (parseInt(waypoint.three_d_waypoints_array[i].id) == id) {
        ind = i;
        break;
      }
    }

    if (ind > -1) {
      waypoint.three_d_waypoints_array.splice(ind, 1);
    }

    // remove waypoint from DB
    removeWaypointFromDB(id);
  }

  function removeTrigger($row) {
    var id = $row.text().split("\n")[1].trim();

    // now go through the array and remove the featurefind the index
    var ind = -1;
    for (var i = 0, l = triggerArray.length; i < l; i++) {
      if (parseInt(triggerArray[i].id) == id) {
        ind = i;
        break;
      }
    }

    if (ind > -1) {
      triggerArray.splice(ind, 1);
    }
    removeTriggerFromDB(id);
  }

  function removeDetection(targ_id, sensor_id) {
    // now go through the array and remove the index
    var ind = -1;
    for (var i = 0, l = detectionArray.length; i < l; i++) {
      if (
        parseInt(detectionArray[i].targ_id) == targ_id &&
        parseInt(detectionArray[i].sensor_id) == sensor_id
      ) {
        ind = i;
        break;
      }
    }

    if (ind > -1) {
      detectionArray.splice(ind, 1);
    }

    // remove the circle on map
    var tmpindex = -1;
    for (var i = 0, ll = detectionCircleArray.length; i < ll; i++) {
      if (
        detectionCircleArray[i].targ_id == targ_id &&
        detectionCircleArray[i].sensor_id == sensor_id
      ) {
        tmpindex = i;
        break;
      }
    }
    if (tmpindex > -1) {
      map.removeLayer(detectionCircleArray[tmpindex].markerLayer);
      delete detectionCircleArray[tmpindex].markerLayer;
      detectionCircleArray.splice(tmpindex, 1);
    }
  }

  function removeTargetWithID(targ_id) {
    // removes from html table and targetArray
    var tbl = document.getElementById("target_table");
    var found = false;
    var ind = -1;
    for (var i = 2, l = tbl.rows.length; i < l; i++) {
      var row = tbl.rows[i];
      var data = row.cells;
      var id = parseInt(data[0].innerHTML);
      if (targ_id == id) {
        found = true;
        ind = i;
        break;
      }
    }
    if (found) {
      tbl.deleteRow(ind);
    }

    // now go through the array and remove the index
    var ind = -1;
    for (var i = 0, l = targetArray.length; i < l; i++) {
      if (parseInt(targetArray[i].id) == targ_id) {
        ind = i;
        break;
      }
    }

    if (ind > -1) {
      targetArray.splice(ind, 1);
    }
  }

  function removeTarget($row) {
    // removes from html table and targetArray
    var id = $row.text().split("\n")[1].trim();
    // now go through the array and remove the featurefind the index
    var ind = -1;
    for (var i = 0, l = targetArray.length; i < l; i++) {
      if (parseInt(targetArray[i].id) == id) {
        ind = i;
        break;
      }
    }

    if (ind > -1) {
      targetArray.splice(ind, 1);
    }

    var indd = targetArray.length - 1;
    if (indd > 0) {
      currentActiveTargetID = parseInt(targetArray[indd].id);
    } else {
      currentActiveTargetID = -1;
    }
    if (targetArray.length == 0) {
      currentActiveTargetID = -1;
    }
  }

  function setActiveSensorInactiveInDB(id) {
    console.log("setting rad inactive: ", id);
    var db_request = new request_wrapper();
    db_request.request_type = "inactivateRADINT";
    db_request.nbr_args = 0;
    db_request.args.push(JSON.stringify(id));
    db_request.nbr_args = db_request.nbr_args + 1;
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  function setActiveSensorActiveInDB(id) {
    console.log("setting rad active: ", id);
    var db_request = new request_wrapper();
    db_request.request_type = "activateRADINT";
    db_request.nbr_args = 0;
    db_request.args.push(JSON.stringify(id));
    db_request.nbr_args = db_request.nbr_args + 1;
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  function removeWaypointFromDB(id) {
    var db_request = new request_wrapper();
    db_request.request_type = "removeAIR_WAYPOINT";
    db_request.nbr_args = 0;
    db_request.args.push(JSON.stringify(id));
    db_request.nbr_args = db_request.nbr_args + 1;
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  function removeTriggerFromDB(id) {
    var db_request = new request_wrapper();
    db_request.request_type = "removeAIR_TRIGGER";
    db_request.nbr_args = 0;
    db_request.args.push(JSON.stringify(id));
    db_request.nbr_args = db_request.nbr_args + 1;
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    sensor_control_worker.postMessage([db_request.request_type, query]);
  }

  function removeActiveMonostaticSensor($row) {
    var id = $row.text().split("\n")[1].trim();
    // now go through the array and remove the feature
    var ind = -1;
    for (var i = 0, l = activeMonostaticArray.length; i < l; i++) {
      if (parseInt(activeMonostaticArray[i].id_nr) == id) {
        var layer = activeMonostaticArray[i].layer;

        var dump_ort = ol.proj.fromLonLat([-7, -40]);
        layer.setCenter(dump_ort); // TBD: this has to be corrected to really remove the circle and not dump it
        ind = i;
        break;
      }
    }
    if (ind > -1) {
      activeMonostaticArray.splice(ind, 1);
    }

    // set status of this RAD to 0 in DB
    setActiveSensorInactiveInDB(id);
  }

  function updateTableFromRadArray(ind) {
    //console.log("ind = ", ind)
    var rad_id = parseInt(activeMonostaticArray[ind].id_nr); //

    for (
      var i = 2, l = document.getElementById("active_sensor_table").rows.length;
      i < l;
      i++
    ) {
      var data = document.getElementById("active_sensor_table").rows[i].cells;
      var curr_id = parseInt(data[0].innerHTML);

      if (rad_id == curr_id) {
        data[1].innerHTML = activeMonostaticArray[ind].name;
        data[2].innerHTML = activeMonostaticArray[ind].status;
        data[3].innerHTML = activeMonostaticArray[ind].lat;
        data[4].innerHTML = activeMonostaticArray[ind].lon;
        data[5].innerHTML = activeMonostaticArray[ind].power;
        data[6].innerHTML = activeMonostaticArray[ind].antenna_diam;
        data[7].innerHTML = activeMonostaticArray[ind].freq;
        data[8].innerHTML = activeMonostaticArray[ind].pulse_width;
        data[9].innerHTML = activeMonostaticArray[ind].cpi_pulses;
        data[10].innerHTML = activeMonostaticArray[ind].bandwidth;
        data[11].innerHTML = activeMonostaticArray[ind].pfa;
        data[12].innerHTML = activeMonostaticArray[ind].rotation_time;
        data[13].innerHTML = activeMonostaticArray[ind].category;
        data[14].innerHTML = activeMonostaticArray[ind].min_elevation;
        data[15].innerHTML = activeMonostaticArray[ind].max_elevation;
        data[16].innerHTML = activeMonostaticArray[ind].orientation;
        data[17].innerHTML = activeMonostaticArray[ind].horiz_aperture;
        data[18].innerHTML = activeMonostaticArray[ind].min_detection_range;
        data[19].innerHTML = activeMonostaticArray[ind].max_detection_range;
        data[20].innerHTML = activeMonostaticArray[ind].min_detection_height;
        data[21].innerHTML = activeMonostaticArray[ind].max_detection_height;
        data[22].innerHTML = activeMonostaticArray[ind].min_detection_tgt_speed;
        data[23].innerHTML = activeMonostaticArray[ind].max_detection_tgt_speed;
      }
    }
  }

  function updateTargetArrayFromTable() {
    for (
      var i = 2, l = document.getElementById("target_table").rows.length;
      i < l;
      i++
    ) {
      var data = document.getElementById("target_table").rows[i].cells;
      var curr_id = parseInt(data[0].innerHTML);
      if (i == 2) {
        currentActiveTargetID = curr_id;
      }

      for (var j = 0, ll = targetArray.length; j < ll; j++) {
        if (parseInt(targetArray[j].id) == curr_id) {
          targetArray[j].name = String(data[1].innerHTML);
          targetArray[j].rcs = parseFloat(data[2].innerHTML);
          targetArray[j].velocity = parseFloat(data[3].innerHTML);
          targetArray[j].corridor_breadth = parseFloat(data[4].innerHTML);
          targetArray[j].noftargets = parseInt(data[5].innerHTML);
          targetArray[j].type = data[6].innerHTML;
          targetArray[j].running = parseInt(data[7].innerHTML);
          targetArray[j].threeD_waypoints_id = parseInt(data[8].innerHTML);
          targetArray[j].status = parseInt(data[9].innerHTML);
          targetArray[j].maneuvring = parseInt(data[10].innerHTML);
        }
      }
    }
  }
  function updateTriggerArrayFromTable() {
    triggerArray = [];
    for (
      var i = 2,
        l = document.getElementById("target_triggers_table").rows.length;
      i < l;
      i++
    ) {
      var data = document.getElementById("target_triggers_table").rows[i].cells;
      var curr_id = parseInt(data[0].innerHTML);
      var trigger = new TargetTrigger(
        sim.TARGET_TRIGGER_PARAM_ID,
        curTriggerID,
        "?",
        -1,
        -1,
        -1,
        "?"
      );
      trigger.id = curr_id;
      trigger.name = String(data[1].innerHTML);
      trigger.source_target_id = parseInt(data[2].innerHTML);
      trigger.dest_target_id = parseInt(data[3].innerHTML);
      trigger.dist_to_poi = parseFloat(data[4].innerHTML);
      trigger.poi_id_nr = parseInt(data[5].innerHTML);
      triggerArray.push(trigger);
    }
  }

  function removeDeadTargetFromDisplay(targid) {
    var tmpindex = -1;
    for (var i = 0, ll = targetCircleArray.length; i < ll; i++) {
      if (targetCircleArray[i].id == targid) {
        tmpindex = i;
        break;
      }
    }
    if (tmpindex > -1) {
      map.removeLayer(targetCircleArray[tmpindex].markerLayer);
      delete targetCircleArray[tmpindex].markerLayer;
      targetCircleArray.splice(tmpindex, 1);
    }
  }

  function removeAllReplaytargets() {
    console.log("deleting ref and test replay vectors...");
    map.removeLayer(test_replay_vector);
    map.removeLayer(ref_replay_vector);

    ref_replay_vectorSource.clear();
    test_replay_vectorSource.clear();

    sensor_control_worker.postMessage([8993455]); // empty replay arrays

    RUN_REPLAY = false;
  }

  function removeDeadTargets() {
    var tmparray = [];
    for (var j = 0, ll = targetArray.length; j < ll; j++) {
      if (targetArray[j].status <= 0) {
        tmparray.push(j);
        removeDeadTargetFromDisplay(targetArray[j].id);
      }
    }

    while (tmparray.length) {
      targetArray.splice(tmparray.pop(), 1);
    }
  }

  function forceKillAllTargets() {
    for (var j = 0, ll = targetArray.length; j < ll; j++) {
      targetArray[j].status = 0;
    }
  }

  function gotoLatLonMap(lat, lon) {
    curr_lat = lat;
    curr_lon = lon;
    document.getElementById("lat2d").value = lat;
    document.getElementById("lon2d").value = lon;
    changeFlightLocationOnMap(curr_lat, curr_lon);

    setMidSlippyXY(curr_lat, curr_lon, slippy_zoom);
    pdf_worker.postMessage([6200901, curr_lat, curr_lon, poi.lat, poi.lon]); // ask for the terrain height

    // set lat lon for radio prop Rx
    document.getElementById("p2p_prop_rx_lat").value = curr_lat;
    document.getElementById("p2p_prop_rx_lon").value = -1 * curr_lon;

    // set lat lon for PCL coverage computation rectangle top-right (NE)
    document.getElementById("lat_stop_inp").value = curr_lat;
    document.getElementById("lon_stop_inp").value = curr_lon;
  }

  function addSensorRow() {
    var $TABLE = $("#active_sensor_table_div");

    var $clone = $TABLE
      .find("tr.hide")
      .clone(true)
      .removeClass("hide table-line");
    $TABLE.find("table").append($clone);

    var x = document.getElementById("active_sensor_table").rows.length;
    var data = document.getElementById("active_sensor_table").rows[x - 1].cells;
    runningSensorID++;
    data[0].innerHTML = runningSensorID;
  }

  function removeAllTargetTriggers() {
    var tbl = document.getElementById("target_triggers_table");
    while (tbl.rows.length > 2) {
      var row = $("tr:eq(2)", tbl);
      removeTrigger(row);
      row.detach();
    }
  }

  function removeAllWayPoints() {
    var tbl = document.getElementById("3d_waypoints_table");
    while (tbl.rows.length > 2) {
      var row = $("tr:eq(2)", tbl);
      removeWaypoint(row);
      row.detach();
    }
  }

  function removeAllTargets() {
    var tbl = document.getElementById("target_table");
    while (tbl.rows.length > 2) {
      var row = $("tr:eq(2)", tbl);
      var id = row.text().split("\n")[1].trim();
      removeTarget(row);
      row.detach();
    }
    runningTargetID = 0;
  }

  function nameUnique(name, json_array) {
    // returns true if name not iin the json_array, else false
    if (json_array == null) {
      return true;
    }
    for (var i = 0; i < json_array.length; i++) {
      var cur_dispo_name = json_array[i].name;
      var curname = json_array[i].dispo_name;
      if (curname == name || cur_dispo_name == name) {
        return false;
      }
    }
    return true;
  }

  function drawWayPoints(wayp_id) {
    var ind = -1;
    for (var i = 0, l = three_d_waypoints_array.length; i < l; i++) {
      if (parseInt(three_d_waypoints_array[i].id) == wayp_id) {
        ind = i;
        if (three_d_waypoints_array[ind].targetLocationArray.length > 1) {
          for (
            var i = 1,
              l = three_d_waypoints_array[ind].targetLocationArray.length;
            i < l;
            i++
          ) {
            var currPos = three_d_waypoints_array[ind].targetLocationArray[i];
            var prevPos =
              three_d_waypoints_array[ind].targetLocationArray[i - 1];

            var pos1 = ol.proj.transform(
              [currPos.lon, currPos.lat],
              "EPSG:4326",
              "EPSG:3857"
            );
            var pos2 = ol.proj.transform(
              [prevPos.lon, prevPos.lat],
              "EPSG:4326",
              "EPSG:3857"
            );
            var coordinates = [pos1, pos2];

            var coord_new = ol.proj.transform(
              coordinates,
              "EPSG:4326",
              "EPSG:3857"
            );
            var layerLines = new ol.layer.Vector({
              source: new ol.source.Vector({
                features: [
                  new ol.Feature({
                    geometry: new ol.geom.LineString(coordinates),
                    name: "track",
                  }),
                ],
              }),
            });

            layerLines.setStyle(hostile_line_style);
            map.addLayer(layerLines);

            three_d_waypoints_array[ind].mapLayersArray.push(layerLines);
          }
        }
      }
    }
  }

  function deleteKMLTracks() {
    for (var i = 0; i < geoplot_track_layers.length; i++) {
      for (var j = 0; j < geoplot_track_layers[i].length; j++) {
        map.removeLayer(geoplot_track_layers[i][j]);
        delete geoplot_track_layers[i][j];
      }
    }
    geoplot_track_layers = [];
  }

  function init() {
    document.getElementById("flightheight").value = 5999; // set inital flight height
    setTargetHeight();

    document.addEventListener("keydown", onDocumentKeyRelease, false);

    console.log(
      ".........got burst proxy server info: ",
      proxy_server,
      ". ...initing workers"
    );
    initWorkersWithServers();

    poi = new POI(sim.POI_PARAM_ID, running_poi_id, "", 46.25, 7.12);
    // code to load xml file for loading scenario
    $("#odfxml").change(function () {
      var file = document.getElementById("odfxml").files[0];
      //You could insert a check here to ensure proper file type
      var reader = new FileReader();
      reader.readAsText(file);
      reader.onloadend = function (e) {
        var xmlData = $(reader.result);

        var parser = new DOMParser();
        var xmlDoc = parser.parseFromString(e.target.result, "text/xml");
        var x = xmlDoc.documentElement.childNodes;
        for (var i = 0, l = x.length; i < l; i++) {
          var lat = -1;
          var lon = -1;
          var pow = -1;
          var status = 1;
          var antenna_diam = -1;
          var freq = -1;
          var pulse_width = -1;
          var bandwidth = -1;
          var cpi_pulses = -1;
          var pfa = -1;
          var rot_time = -1;
          var category = -1;
          var name = "-";
          if (x[i].nodeName == "SENSOR") {
            var y = x[i].childNodes;
            for (var ii = 0, ll = y.length; ii < ll; ii++) {
              if (y[ii].nodeName == "LAT") {
                lat = parseFloat(y[ii].textContent);
              }
              if (y[ii].nodeName == "LON") {
                lon = parseFloat(y[ii].textContent);
              }
              if (y[ii].nodeName == "STATUS") {
                status = parseFloat(y[ii].textContent);
              }
              if (y[ii].nodeName == "POWER") {
                pow = parseFloat(y[ii].textContent);
              }
              if (y[ii].nodeName == "antenna_diam") {
                antenna_diam = parseFloat(y[ii].textContent);
              }
              if (y[ii].nodeName == "FREQ") {
                freq = parseFloat(y[ii].textContent);
              }
              if (y[ii].nodeName == "pulse_width") {
                pulse_width = parseFloat(y[ii].textContent);
              }
              if (y[ii].nodeName == "CPI_PULSES") {
                cpi_pulses = parseFloat(y[ii].textContent);
              }
              if (y[ii].nodeName == "BANDWIDTH") {
                bandwidth = parseFloat(y[ii].textContent);
              }
              if (y[ii].nodeName == "PFA") {
                pfa = parseFloat(y[ii].textContent);
              }
              if (y[ii].nodeName == "ROTATION_TIME") {
                rot_time = parseFloat(y[ii].textContent);
              }
              if (y[ii].nodeName == "CATEGORY") {
                category = parseFloat(y[ii].textContent);
              }
              if (y[ii].nodeName == "NAME") {
                name = y[ii].textContent;
              }
            }
          }

          if (lat > -1 && lon > -1) {
            //
            addNewActiveMonostaticSensor(
              lat,
              lon,
              pow,
              status,
              antenna_diam,
              freq,
              cpi_pulses,
              bandwidth,
              pfa,
              rot_time,
              category,
              pulse_width,
              name
            );
          }
        }
      };
    });

    //--------------------- target tigger table functions
    $(".target-triggers-table-add").click(function () {
      var $TABLE = $("#target_triggers_table_div");
      var $clone = $TABLE
        .find("tr.hide")
        .clone(true)
        .removeClass("hide table-line");
      $TABLE.find("table").append($clone);
      var x = document.getElementById("target_triggers_table").rows.length;
      var data = document.getElementById("target_triggers_table").rows[x - 1]
        .cells;
      data[0].innerHTML = curTriggerID;

      data[1].innerHTML = "?";
      data[2].innerHTML = "?";
      data[3].innerHTML = "?";
      data[4].innerHTML = -1;
      data[5].innerHTML = "?";

      // now add to array
      var trigger = new TargetTrigger(
        sim.TARGET_TRIGGER_PARAM_ID,
        curTriggerID,
        "?",
        -1,
        -1,
        -1,
        "?"
      );
      triggerArray.push(trigger);
      curTriggerID++;
    });

    $(".target-triggers-table-remove").click(function () {
      removeTrigger($(this).parents("tr"));
      $(this).parents("tr").detach();
    });

    $(".target-triggers-table-up").click(function () {
      // ask for current target-triggers
      var msg_json1 = JSON.stringify([
        { object_id: TARGET_TRIGGER_DOWNLOAD_ID },
      ]);
      var total_msg_json = [msg_json1];
      // now call the worker to get all the triggers saved on the server
      sensor_control_worker.postMessage(total_msg_json);
      //-------------------------------------------------------

      // upload trigger to server
      var id = $(this).parents("tr").text().split("\n")[1].trim();
      var name = $(this).parents("tr").text().split("\n")[2].trim();

      var title = "Upload trigger to server with name = : " + name;
      // update the trigger array from the html
      updateTriggerArrayFromTable();
      upload_trigger_id = id;

      $("#target_trigger_upload_diag_input").dialog("option", "title", title);
      $("#target_trigger_upload_diag_input").dialog("open");
    });

    $(".target-triggers-table-down").click(function () {
      var id = $(this).parents("tr").text().split("\n")[1].trim();
      download_trigger_id = id;

      // download trigger from server
      var msg_json1 = JSON.stringify([
        { object_id: TARGET_TRIGGER_DOWNLOAD_ID },
      ]);
      var total_msg_json = [msg_json1];
      // now call the worker to get all the triggers saved on the server
      sensor_control_worker.postMessage(total_msg_json);

      var title = "Download trigger from server with name";
      $("#target_trigger_download_diag_input").dialog("option", "title", title);
      $("#target_trigger_download_diag_input").dialog("open");
    });

    // -------set up functions for the target table
    $(".target-table-update").click(function () {});

    $(".target-table-remove").click(function () {
      var id = $(this).parents("tr").text().split("\n")[1].trim();
      removeTarget($(this).parents("tr"));
      $(this).parents("tr").detach();
    });
    $(".target-table-down").click(function () {
      var id = $(this).parents("tr").text().split("\n")[1].trim();
      download_target_id = id;

      // download target from server
      var msg_json1 = JSON.stringify([{ object_id: TARGET_DOWNLOAD_ID }]);
      var total_msg_json = [msg_json1];
      // now call the worker to get all the targets saved on the server
      sensor_control_worker.postMessage(total_msg_json);

      var title = "Download target from server with name";
      $("#target_download_diag_input").dialog("option", "title", title);
      $("#target_download_diag_input").dialog("open");
    });

    $(".target-table-up").click(function () {
      // ask for the currently saved targets: so that the variabe download_targets_json is updated..
      var msg_json1 = JSON.stringify([{ object_id: TARGET_DOWNLOAD_ID }]);
      var total_msg_json = [msg_json1];
      // now call the worker to get all the targets saved on the server
      sensor_control_worker.postMessage(total_msg_json);
      // upload target to server
      var id = $(this).parents("tr").text().split("\n")[1].trim();
      var name = $(this).parents("tr").text().split("\n")[2].trim();

      var title = "Upload target to server with name = : " + name;
      // update the target array from the html
      updateTargetArrayFromTable();
      upload_target_id = id;

      $("#target_upload_diag_input").dialog("option", "title", title);
      $("#target_upload_diag_input").dialog("open"); //
    });

    // threat table
    $(".threat-scenario-table-down").click(function () {
      var id = $(this).parents("tr").text().split("\n")[1].trim();

      // download threat scenarios from server
      var msg_json1 = JSON.stringify([
        { object_id: THREAT_SCENARIO_DOWNLOAD_ID },
      ]);
      var total_msg_json = [msg_json1];
      // now call the worker to get all the threat scenarios saved on the server
      sensor_control_worker.postMessage(total_msg_json);

      var title = "Download Threat Scenarios from server with name";
      $("#threat_scenario_download_diag_input").dialog(
        "option",
        "title",
        title
      );
      $("#threat_scenario_download_diag_input").dialog("open");
    });

    $(".threat-scenario-table-up").click(function () {
      // ask for the currently saved threat scenarios : so that the variabe
      // download_threat_scenarios_json is updated.
      var msg_json1 = JSON.stringify([
        { object_id: THREAT_SCENARIO_DOWNLOAD_ID },
      ]);
      var total_msg_json = [msg_json1];
      // now call the worker to get all the threat scenarios saved on the server
      sensor_control_worker.postMessage(total_msg_json);

      // upload threat scenarios to server
      var name = $(this).parents("tr").text().split("\n")[1].trim();

      var title = "Upload threat scenarios to server with name = " + name;

      $("#threat_scenario_upload_diag_input").dialog("option", "title", title);
      $("#threat_scenario_upload_diag_input").dialog("open"); //
    });

    /// POI table
    $(".poi-table-down").click(function () {
      var id = $(this).parents("tr").text().split("\n")[1].trim();
      // download poi from server
      var msg_json1 = JSON.stringify([{ object_id: POI_DOWNLOAD_ID }]);
      var total_msg_json = [msg_json1];
      // now call the worker to get all the pois saved on the server
      sensor_control_worker.postMessage(total_msg_json);

      var title = "Download POI from server with name";
      $("#poi_download_diag_input").dialog("option", "title", title);
      $("#poi_download_diag_input").dialog("open");
    });

    $(".poi-table-up").click(function () {
      // update POI from table
      updatePOIfromTable();

      // ask for the currently saved POIs: so that the variabe download_pois_json is updated.
      var msg_json1 = JSON.stringify([{ object_id: POI_DOWNLOAD_ID }]);
      var total_msg_json = [msg_json1];
      // now call the worker to get all the POIs saved on the server
      sensor_control_worker.postMessage(total_msg_json);
      // upload POI to server
      var id = $(this).parents("tr").text().split("\n")[1].trim();
      var name = $(this).parents("tr").text().split("\n")[2].trim();

      var title = "Upload POI to server with name = : " + name;

      $("#poi_upload_diag_input").dialog("option", "title", title);
      $("#poi_upload_diag_input").dialog("open"); //
    });

    // -------set up functions for the active sensor table

    $(".sensor-table-update").click(function () {
      //addSensorRow();
    });

    $(".sensor-table-remove").click(function () {
      if (nofRunningCoverages == 0) {
        removeActiveMonostaticSensor($(this).parents("tr"));
        $(this).parents("tr").detach();
      } else {
        alert("Please wait for radar coverage computation to finish...");
      }
    });

    $(".sensor-table-wrench").click(function () {
      var id = $(this).parents("tr").text().split("\n")[1].trim();
      var title = "Set Antenna Pattern for Sensor ID: " + id;
      $("#sensor_antenna_diag_input").dialog("option", "title", title);
      $("#sensor_antenna_diag_input").dialog("open");
    });

    $(".sensor-table-down").click(function () {
      var id = $(this).parents("tr").text().split("\n")[1].trim();
      download_sensor_id = id;

      // download sensor from server
      var msg_json1 = JSON.stringify([{ object_id: SENSOR_DOWNLOAD_ID }]);
      var total_msg_json = [msg_json1];
      // now call the worker to get all the sensors saved on the server
      sensor_control_worker.postMessage(total_msg_json);

      var title = "Download sensor from server with name";
      $("#sensor_download_diag_input").dialog("option", "title", title);
      $("#sensor_download_diag_input").dialog("open");
    });

    $(".sensor-table-up").click(function () {
      // ask for the currently saved sensors: so that the variabe download_sensors_json is updated..
      var msg_json1 = JSON.stringify([{ object_id: SENSOR_DOWNLOAD_ID }]);
      var total_msg_json = [msg_json1];
      // now call the worker to get all the sensors saved on the server
      sensor_control_worker.postMessage(total_msg_json);
      // upload sensor to server
      var id = $(this).parents("tr").text().split("\n")[1].trim();
      var name = $(this).parents("tr").text().split("\n")[2].trim();

      var title = "Upload sensor to server with name = : " + name;
      // update the sensor array from the html
      updateSensorArrayFromTable();
      upload_sensor_id = id;

      $("#sensor_upload_diag_input").dialog("option", "title", title);
      $("#sensor_upload_diag_input").dialog("open");
    });

    // This defines what happens when clicking 'x' glyph. of passive sensors
    $(".passsensor-table-remove").click(function () {
      // alert("Removing passive sensor");
      removePassSensor($(this).parents("tr"));
      $(this).parents("tr").detach();

      findTxForRx(); // find Tx for the remaining Rx

      removeAllLinesBetwAllRxAndTx(map); // removing all lines
      removeAllTxRadPatternsOnMap(map); // removing all radiation patterns
    });

    // in the beginning simply add a row to the POI table
    var $TABLE = $("#poi_table_div");
    var $clone = $TABLE
      .find("tr.hide")
      .clone(true)
      .removeClass("hide table-line");
    $TABLE.find("table").append($clone);
    var x = document.getElementById("poi_table").rows.length;
    var data = document.getElementById("poi_table").rows[x - 1].cells;
    data[0].innerHTML = running_poi_id.toString();
    //data[1].innerHTML = "?"
    data[2].innerHTML = poi.lat;
    data[3].innerHTML = poi.lon;

    // in the beginning simply add a row to the Threat Sceanrio table
    var $TABLE = $("#threat_scenario_table_div");
    var $clone = $TABLE
      .find("tr.hide")
      .clone(true)
      .removeClass("hide table-line");
    $TABLE.find("table").append($clone);
    var x = document.getElementById("threat_scenario_table").rows.length;
    var data = document.getElementById("threat_scenario_table").rows[x - 1]
      .cells;
    data[0].innerHTML = "?";

    $("#target_rcs_input").keypress(function (e) {
      //if the letter is not a digit then display error and don't type anything
      if (e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57)) {
        //display error message
        //$("#errmsg").html("Digits Only").show().fadeOut("slow");
        return false;
      }
    });

    //----------------waypoints table function
    $(".3d-waypoints-table-remove").click(function () {
      removeWaypoint($(this).parents("tr"));
      $(this).parents("tr").detach();
    });
    $(".3d-waypoints-table-toggle-view").click(function () {
      //console.log("toggel clicked")
      $(this)
        .toggleClass("glyphicon-eye-open")
        .toggleClass("glyphicon-eye-close");
      $row = $(this).parents("tr");
      var id = $row.text().split("\n")[1].trim();
      toggleWaypointsView(id);
    });

    $(".3d-waypoints-table-up").click(function () {
      // ask for current waypoint
      var msg_json1 = JSON.stringify([{ object_id: WAYPOINTS_DOWNLOAD_ID }]);
      var total_msg_json = [msg_json1];
      // now call the worker to get all the sensors saved on the server
      sensor_control_worker.postMessage(total_msg_json);
      //-------------------------------------------------------

      // upload waypoint to server
      var id = $(this).parents("tr").text().split("\n")[1].trim();
      var name = $(this).parents("tr").text().split("\n")[2].trim();

      var title = "Upload waypoint to server with name = : " + name;
      // update the waypoint array from the html
      updateWaypointsArrayFromTable();
      upload_waypoint_id = id;

      $("#waypoints_upload_diag_input").dialog("option", "title", title);
      $("#waypoints_upload_diag_input").dialog("open");
    });

    $(".3d-waypoints-table-down").click(function () {
      var id = $(this).parents("tr").text().split("\n")[1].trim();
      download_waypoint_id = id;

      // download waypoint from server
      var msg_json1 = JSON.stringify([{ object_id: WAYPOINTS_DOWNLOAD_ID }]);
      var total_msg_json = [msg_json1];
      // now call the worker to get all the waypoints saved on the server
      sensor_control_worker.postMessage(total_msg_json);

      var title = "Download waypoint from server with name";
      $("#waypoints_download_diag_input").dialog("option", "title", title);
      $("#waypoints_download_diag_input").dialog("open");
    });

    // --------------------------------kml_table checkbox click function
    $("#kml_table").on("click", "input[type=checkbox]", function () {
      var row = this.parentNode.parentNode.rowIndex;
      var maxind = geoplot_track_layers.length;
      if (row > 0) {
        if (this.checked == 1) {
          // show the tracks
          for (
            var i = 0, l = geoplot_track_layers[row - 1].length;
            i < l;
            i++
          ) {
            geoplot_track_layers[row - 1][i].setVisible(true);
          }
        } else {
          // hide the tracks
          for (
            var i = 0, l = geoplot_track_layers[row - 1].length;
            i < l;
            i++
          ) {
            geoplot_track_layers[row - 1][i].setVisible(false);
          }
        }
      }
    });

    // ---------------------------initialize 2D openlayers map with openstreetmap source -----------------

    view = new ol.View({
      // the view's initial state
      center: bern,
      zoom: 8,
    });

    map = new ol.Map({
      // Improve user experience by loading tiles while animating. Will make
      // animations stutter on mobile or slow devices.
      loadTilesWhileAnimating: true,
      controls: ol.control
        .defaults({
          attributionOptions: /** @type {olx.control.AttributionOptions} */ ({
            collapsible: false,
          }),
        })
        .extend([
          new ol.control.ScaleLine({
            className: "ol-scale-line",
            target: document.getElementById("map"),
          }),
        ]),
      layers: [
        new ol.layer.Tile({
          //preload: 4,
          source: new ol.source.OSM(), // REMOTE: i.e. needs internet conenction and use the openstreetmaps background
          // using local tile server from: http://openlayers.org/en/v3.5.0/examples/localized-openstreetmap.html

          //source: new ol.source.OSM({
          //    url: 'http://10.42.0.101/osm_tiles/{z}/{x}/{y}.png' // LOCAL: i.e needs no internet, but needs a local tile server running
          //})
        }),
      ],
      overlays: [popup_overlay],
      target: "map",
      view: view,
    });
    $("#infobox").appendTo($(".ol-overlaycontainer"));

    // ---POI
    var poi_circle = new ol.geom.Circle(
      ol.proj.transform([2.5, 5.5], "EPSG:4326", "EPSG:3857"),
      200
    );
    var circleFeaturePOI = new ol.Feature(poi_circle);
    var poiFeatureOverlay = new ol.FeatureOverlay({
      map: map,
      features: [circleFeaturePOI],
      style: new ol.style.Style({
        fill: new ol.style.Fill({
          color: "rgba(220, 200, 100, 0.3)",
        }),
        stroke: new ol.style.Stroke({
          width: 4,

          color: "#20B2AA",
        }),
        text: new ol.style.Text({
          text: "POI",
          scale: 1.3,
          fill: new ol.style.Fill({
            color: "#fff",
          }),
          stroke: new ol.style.Stroke({
            color: "#20B2AA",
            width: 3.5,
          }),
        }),
      }),
    });

    // create animation source and vector
    sensorAnimationSource = new ol.source.Vector({
      wrapX: false,
    });
    var sensorAnimationVector = new ol.layer.Vector({
      source: sensorAnimationSource,
    });
    map.addLayer(sensorAnimationVector);

    // --------------try the heatmap------------
    var data = new ol.source.Vector();

    // created for owl range of data
    var coord1 = ol.proj.transform([7.82, 47.1], "EPSG:4326", "EPSG:3857");
    var lonLat1 = new ol.geom.Point(coord1);
    var coord2 = ol.proj.transform([7.82, 47.11], "EPSG:4326", "EPSG:3857");
    var lonLat2 = new ol.geom.Point(coord2);
    var coord3 = ol.proj.transform([7.82, 47.105], "EPSG:4326", "EPSG:3857");
    var lonLat3 = new ol.geom.Point(coord3);

    var pointFeature1 = new ol.Feature({
      geometry: lonLat1,
      weight: 0.5, // min:0 max:1
    });
    var pointFeature2 = new ol.Feature({
      geometry: lonLat2,
      weight: 0.7, // min:0 max:1
    });
    var pointFeature3 = new ol.Feature({
      geometry: lonLat3,
      weight: 0.9, // min:0 max:1
    });

    data.addFeature(pointFeature1);
    data.addFeature(pointFeature2);
    data.addFeature(pointFeature3);

    // create the layer
    heatMapLayer = new ol.layer.Heatmap({
      source: data,
      radius: 20,
    });

    map.on("pointermove", function (evt) {
      if (popup_closer != null) {
        popup_overlay.setPosition(undefined);
        popup_closer.blur();
      }
    });

    map.on("click", function (evt) {
      var lonlat = ol.proj.transform(evt.coordinate, "EPSG:3857", "EPSG:4326");
      var lon = lonlat[0];
      var lat = lonlat[1];
      gotoLatLonMap(lat, lon);

      if (ol.events.condition.shiftKeyOnly(evt)) {
        var selected_sensor = document.getElementById("sensor-selector").value;
        switch (selected_sensor) {
          case "RADINT":
            if (nofRunningCoverages < 1) {
              addNewActiveMonostaticSensor(lat, lon);
            } else {
              alert("Please wait for radar coverage computation to finish...");
            }

            break;

          case "PCL":
            if (nofRunningCoverages < 1) {
              console.log("----------placing PCL sensor at this point ###!");
              // query what height the receiver has, and will eventually update
              // the table and the array
              updateHeightOfRx(lat, lon, pdf_worker);
            } else {
              alert("Please wait for radar coverage computation to finish...");
            }
            break;

          case "PET":
            pdf_worker.postMessage([
              6200902,
              curr_lat,
              curr_lon,
              poi.lat,
              poi.lon,
            ]); // ask for the terrain height
            break;

          case "TARGET":
            console.log("maneuvering target");
            var db_request = new request_wrapper();
            var SELECTED_TARGET_ID = parseInt(
              document.getElementById("targetidinput").value
            );
            var targ_id = -1;
            for (var i = 0, l = targetArray.length; i < l; i++) {
              console.log(
                "found id: ",
                targetArray[i].id,
                ", searching for: ",
                targ_id
              );
              if (
                targetArray[i].id
                  .toString()
                  .endsWith(SELECTED_TARGET_ID.toString())
              ) {
                targ_id = targetArray[i].id;
              }
            }
            if (targ_id != -1) {
              var targetHeight = parseFloat(
                document.getElementById("flightheight").value
              );
              db_request.request_type = "maneuver_TARGET";
              db_request.nbr_args = 0;
              db_request.args.push(JSON.stringify(targ_id));
              db_request.nbr_args = db_request.nbr_args + 1;
              db_request.args.push(JSON.stringify(team));
              db_request.nbr_args = db_request.nbr_args + 1;
              db_request.args.push(JSON.stringify(curr_lat));
              db_request.nbr_args = db_request.nbr_args + 1;
              db_request.args.push(JSON.stringify(curr_lon));
              db_request.nbr_args = db_request.nbr_args + 1;
              db_request.args.push(JSON.stringify(targetHeight));
              db_request.nbr_args = db_request.nbr_args + 1;
              var query = JSON.stringify(db_request);
              sensor_control_worker.postMessage([
                db_request.request_type,
                query,
              ]);
            }
            break;
        }
      }
    });

    // set POI if double clicked
    map.on("dblclick", function (evt) {
      var lonlat = ol.proj.transform(evt.coordinate, "EPSG:3857", "EPSG:4326");
      poi.lon = lonlat[0];
      poi.lat = lonlat[1];
      // set lat lon for radio prop Tx
      document.getElementById("p2p_prop_tx_lat").value = poi.lat;
      document.getElementById("p2p_prop_tx_lon").value = -1 * poi.lon;

      // set lat lon for PCL coverage computation rectangle bottom_left (SW)
      document.getElementById("lat_start_inp").value = poi.lat;
      document.getElementById("lon_start_inp").value = poi.lon;

      //
      var curr_ort = ol.proj.fromLonLat([poi.lon, poi.lat]);
      poi_circle.setCenter(curr_ort);

      var x = document.getElementById("poi_table").rows.length;
      var data = document.getElementById("poi_table").rows[x - 1].cells;
      data[2].innerHTML = poi.lat;
      data[3].innerHTML = poi.lon;

      pdf_worker.postMessage([5340906, poi.lat, poi.lon, 0]);
    });

    //-------------------target trigger upload input dialog-----------------------
    $(function () {
      $("#target_trigger_upload_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            // get the trigger
            var trigger = getTriggerFromID(upload_trigger_id);

            if (!nameUnique(trigger.name, download_triggers_json)) {
              alert("Error: Trigger name already in DB");
              return;
            }

            var trigger_str = JSON.stringify(trigger, [
              "object_id",
              "id",
              "name",
              "source_target_id",
              "dest_target_id",
              "dist_to_poi",
              "poi_name",
            ]);
            trigger_str = "[" + trigger_str + "]";

            var msg_json1 = JSON.stringify([
              { object_id: TARGET_TRIGGER_UPLOAD_ID },
            ]); //

            var total_msg_json = [msg_json1, trigger_str];
            // now call the worker
            sensor_control_worker.postMessage(total_msg_json);

            var alert_txt =
              "Trigger uploaded to server with name: " + trigger.name;
            alert(alert_txt);
            $(this).dialog("close");
            //}
          },
          Close: function () {
            alert("Trigger not uploaded");
            $(this).dialog("close");
          },
        },
      });
    });
    //-------------------trigger download input dialog-----------------------
    $(function () {
      $("#target_trigger_download_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            var trigger_name = $(
              "#target_trigger_download_selectbox option:selected"
            ).text();
            var trigger = null;
            for (var i = 0; i < download_triggers_json.length; i++) {
              var curname = download_triggers_json[i].name;
              if (curname == trigger_name) {
                trigger = download_triggers_json[i];
                break;
              }
            }

            // update the trigger parameters in the table
            if (trigger != null) {
              // traverse the table
              for (
                var i = 2,
                  l = document.getElementById("target_triggers_table").rows
                    .length;
                i < l;
                i++
              ) {
                var data = document.getElementById("target_triggers_table")
                  .rows[i].cells;
                var curr_id = parseInt(data[0].innerHTML);

                if (curr_id == download_trigger_id) {
                  data[1].innerHTML = trigger.name;
                  data[2].innerHTML = trigger.source_target_id;
                  data[3].innerHTML = trigger.dest_target_id;
                  data[4].innerHTML = trigger.dist_to_poi;
                  data[5].innerHTML = trigger.poi_name;
                }
              }

              // also insert this trigger into the array
              updateTriggerArrayFromTable();
            }

            var alert_txt = "Trigger downloaded from server ";
            alert(alert_txt);
            $(this).dialog("close");
            //}
          },
          Close: function () {
            alert("Trigger not downloaded");
            $(this).dialog("close");
          },
        },
      });
    });
    //-------------------Threat Scenario upload input dialog-----------------------
    $(function () {
      $("#threat_scenario_upload_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            // update trigger array
            updateTriggerArrayFromTable();
            // update waypoints array
            updateWaypointsArrayFromTable();
            // update targets array
            updateTargetArrayFromTable();
            // update POI from table
            updatePOIfromTable();

            //console.log("uploading Threat Scenario...")
            // get the threat_name
            var data = document.getElementById("threat_scenario_table").rows[2]
              .cells;
            var threat_name = String(data[0].innerHTML);
            if (!nameUnique(threat_name, download_threat_scenarios_json)) {
              alert("Error: Threat Scenario name already in DB");
              return;
            }
            var threat_scenario = new ThreatScenario(
              THREAT_SCENARIO_PARAM_ID,
              threat_name,
              triggerArray,
              targetArray,
              three_d_waypoints_array,
              poi
            );

            var threat_scenario_str = stringifyThreatScenario(threat_scenario);

            threat_scenario_str = "[" + threat_scenario_str + "]";

            var msg_json1 = JSON.stringify([
              { object_id: THREAT_SCENARIO_UPLOAD_ID },
            ]);

            var total_msg_json = [msg_json1, threat_scenario_str];

            // now call the worker
            sensor_control_worker.postMessage(total_msg_json);

            var alert_txt =
              "Threat scenario uploaded to server with name: " + threat_name;
            alert(alert_txt);
            $(this).dialog("close");
          },
          Close: function () {
            alert("POI not uploaded");
            $(this).dialog("close");
          },
        },
      });
    });

    //-------------------threat scenario download input dialog-----------------------
    $(function () {
      $("#threat_scenario_download_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            var threat_scenario_name = $(
              "#threat_scenario_download_selectbox option:selected"
            ).text();
            var threat_scenario = null;
            for (var i = 0; i < download_threat_scenarios_json.length; i++) {
              var curname = download_threat_scenarios_json[i].name;
              if (curname == threat_scenario_name) {
                threat_scenario = download_threat_scenarios_json[i];
                break;
              }
            }

            // update the threat scenario parameters in the table
            if (threat_scenario != null) {
              // traverse the table
              var data = document.getElementById("threat_scenario_table")
                .rows[2].cells;
              data[0].innerHTML = threat_scenario.name;

              // now update all the variables and array
              // remove all Targets
              removeAllTargets();

              // remove all waypoints
              removeAllWayPoints();

              // remove all target triggers
              removeAllTargetTriggers();

              // remove all downloaded json data
              download_triggers_json = [];
              download_threat_scenarios_json = [];
              download_targets_json = [];

              // update trigger array
              updateTriggerArrayFromTable();
              // update waypoints array
              updateWaypointsArrayFromTable();
              // update targets array
              updateTargetArrayFromTable();
              // update POI from table
              updatePOIfromTable();

              // now read the downloaded threat_scenario and create targets
              if (threat_scenario.targetArray != null) {
                for (
                  var j = 0, l = threat_scenario.targetArray.length;
                  j < l;
                  j++
                ) {
                  addTargetRow();

                  var target = threat_scenario.targetArray[j];
                  var ind =
                    document.getElementById("target_table").rows.length - 1;
                  var data =
                    document.getElementById("target_table").rows[ind].cells;

                  data[1].innerHTML = target.name; //
                  data[2].innerHTML = target.rcs;
                  data[3].innerHTML = target.velocity;
                  data[4].innerHTML = target.corridor_breadth;
                  data[5].innerHTML = target.noftargets;
                  data[6].innerHTML = target.type;
                  data[7].innerHTML = target.running;
                  data[8].innerHTML = target.threeD_waypoints_id;

                  // object_id, id, rcs, name, running, velocity, corridor_breadth, noftargets, type, threeD_waypoints_id, status
                  var target = new Target(
                    sim.TARGET_PARAM_ID,
                    runningTargetID,
                    target.rcs,
                    target.name,
                    target.running,
                    target.velocity,
                    target.corridor_breadth,
                    target.noftargets,
                    target.type,
                    target.threeD_waypoints_id,
                    target.status
                  );
                  targetArray.push(target);
                  runningTargetID = runningTargetID + 111;
                }
                // update targets array
                updateTargetArrayFromTable();
              }

              // now read the downloaded threat_scenario and create 3d waypoints
              if (threat_scenario.three_d_waypoints_array != null) {
                //console.log(" threat_scenario...updating waypoints table")
                for (
                  var j = 0, l = threat_scenario.three_d_waypoints_array.length;
                  j < l;
                  j++
                ) {
                  addWayPointRow();

                  var wayp = threat_scenario.three_d_waypoints_array[j];
                  var ind =
                    document.getElementById("3d_waypoints_table").rows.length -
                    1;
                  var data =
                    document.getElementById("3d_waypoints_table").rows[ind]
                      .cells;
                  data[0].innerHTML = wayp.id; //runningWaypId;
                  data[1].innerHTML = wayp.name;
                  data[2].innerHTML = wayp.agl_asl;
                  data[3].innerHTML = wayp.poi_name;

                  // also insert this waypoints into the array //
                  var threeD_wayp = new ThreeD_Waypoints(
                    THREE_D_WAYPOINTS_PARAM_ID,
                    wayp.id,
                    wayp.name,
                    wayp.poi_name,
                    wayp.agl_asl
                  );
                  threeD_wayp.targetLocationArray = wayp.targetLocationArray;
                  threeD_wayp.mapLayersArray = [];
                  three_d_waypoints_array.push(threeD_wayp);
                  updateWayPoints(
                    wayp.id,
                    wayp.name,
                    wayp.poi_name,
                    wayp.agl_asl,
                    wayp.targetLocationArray
                  );
                }
                // update waypoints array
                updateWaypointsArrayFromTable();
              }
              // update POI
              if (threat_scenario.poi != null) {
                poi = threat_scenario.poi;
                var ind = document.getElementById("poi_table").rows.length - 1;
                var data = document.getElementById("poi_table").rows[ind].cells;
                data[1].innerHTML = poi.name;
                data[2].innerHTML = poi.lat;
                data[3].innerHTML = poi.lon;
                var curr_ort = ol.proj.fromLonLat([poi.lon, poi.lat]);
                poi_circle.setCenter(curr_ort);
                if (poi_mesh == null) {
                  addNewPOIMesh(poi.lat, poi.lon);
                }
                pdf_worker.postMessage([5340906, poi.lat, poi.lon, 0]); // to update poi mesh on the 3d map also
                // update POI from table
                updatePOIfromTable();
              }
              // update target triggers
              // now read the downloaded threat_scenario and create target triggers
              if (threat_scenario.triggerArray != null) {
                for (
                  var j = 0, l = threat_scenario.triggerArray.length;
                  j < l;
                  j++
                ) {
                  // add a new trigger
                  var $TABLE = $("#target_triggers_table_div");
                  var $clone = $TABLE
                    .find("tr.hide")
                    .clone(true)
                    .removeClass("hide table-line");
                  $TABLE.find("table").append($clone);

                  var trigger = threat_scenario.triggerArray[j];
                  var ind =
                    document.getElementById("target_triggers_table").rows
                      .length - 1;
                  var data = document.getElementById("target_triggers_table")
                    .rows[ind].cells;
                  data[0].innerHTML = curTriggerID;
                  data[1].innerHTML = trigger.name;
                  data[2].innerHTML = trigger.source_target_id;
                  data[3].innerHTML = trigger.dest_target_id;
                  data[4].innerHTML = trigger.dist_to_poi;
                  data[5].innerHTML = trigger.poi_name;

                  // now add to array
                  // object_id, id, name, source_target_id, dest_target_id, dist_to_poi, poi_name
                  var trigger = new TargetTrigger(
                    TARGET_TRIGGER_PARAM_ID,
                    curTriggerID,
                    trigger.name,
                    trigger.source_target_id,
                    trigger.dest_target_id,
                    trigger.dist_to_poi,
                    trigger.poi_name
                  );
                  triggerArray.push(trigger);

                  curTriggerID++;
                }
              }
              // update trigger array

              updateTriggerArrayFromTable();
            }

            // enable capture button
            document.getElementById("insert_air").disabled = false;

            var alert_txt = "Threat Scenario downloaded from server ";
            alert(alert_txt);
            $(this).dialog("close");
            //}
          },
          Close: function () {
            alert("Threat Scenario not downloaded");
            $(this).dialog("close");
          },
        },
      });
    });
    //-------------------POI upload input dialog-----------------------
    $(function () {
      $("#poi_upload_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            // get the POI
            if (!nameUnique(poi.name, download_pois_json)) {
              alert("Error: POI name already in DB");
              return;
            }

            var poi_str = JSON.stringify(poi, [
              "object_id",
              "id",
              "name",
              "lat",
              "lon",
            ]);
            poi_str = "[" + poi_str + "]";

            var msg_json1 = JSON.stringify([{ object_id: POI_UPLOAD_ID }]);

            var total_msg_json = [msg_json1, poi_str];

            // now call the worker
            sensor_control_worker.postMessage(total_msg_json);

            var alert_txt = "POI uploaded to server with name: " + poi.name;
            alert(alert_txt);
            $(this).dialog("close");
            //}
          },
          Close: function () {
            alert("POI not uploaded");
            $(this).dialog("close");
          },
        },
      });
    });

    //-------------------poi download input dialog-----------------------
    $(function () {
      $("#poi_download_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            var poi_name = $("#pois_download_selectbox option:selected").text();
            var d_poi = null;
            for (var i = 0; i < download_pois_json.length; i++) {
              var curname = download_pois_json[i].name;
              if (curname == poi_name) {
                d_poi = download_pois_json[i];
                break;
              }
            }

            // update the POI parameters in the table
            if (d_poi != null) {
              // traverse the table
              var data = document.getElementById("poi_table").rows[2].cells;
              data[1].innerHTML = d_poi.name;
              data[2].innerHTML = d_poi.lat;
              data[3].innerHTML = d_poi.lon;

              // update poi variabel
              poi.name = d_poi.name;
              poi.lat = d_poi.lat;
              poi.lon = d_poi.lon;

              // also place the marker on the map correctly
              var curr_ort = ol.proj.fromLonLat([poi.lon, poi.lat]);
              poi_circle.setCenter(curr_ort);

              // remove poi mesh
              pdf_worker.postMessage([5340906, poi.lat, poi.lon, 0]);
            }

            var alert_txt = "POI downloaded from server ";
            alert(alert_txt);
            $(this).dialog("close");
            //}
          },
          Close: function () {
            alert("POI not downloaded");
            $(this).dialog("close");
          },
        },
      });
    });
    //-------------------target upload input dialog-----------------------
    $(function () {
      $("#target_upload_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            updateTargetArrayFromTable();

            // get the target
            var target = getTargetFromID(upload_target_id);
            if (!nameUnique(target.name, download_targets_json)) {
              alert("Error: Target name already in DB");
              return;
            }

            var target_str = stringifyTarget(target);
            target_str = "[" + target_str + "]";

            var msg_json1 = JSON.stringify([{ object_id: TARGET_UPLOAD_ID }]);

            var total_msg_json = [msg_json1, target_str];
            // now call the worker
            sensor_control_worker.postMessage(total_msg_json);

            var alert_txt =
              "Target uploaded to server with name: " + target.name;
            alert(alert_txt);
            $(this).dialog("close");
            //}
          },
          Close: function () {
            alert("Target not uploaded");
            $(this).dialog("close");
          },
        },
      });
    });

    //-------------------target download input dialog-----------------------
    $(function () {
      $("#target_download_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            var target_name = $(
              "#targets_download_selectbox option:selected"
            ).text();
            var target = null;
            for (var i = 0; i < download_targets_json.length; i++) {
              var curname = download_targets_json[i].name;
              if (curname == target_name) {
                target = download_targets_json[i];
                break;
              }
            }

            // update the target parameters in the table
            if (target != null) {
              // traverse the table
              for (
                var i = 2,
                  l = document.getElementById("target_table").rows.length;
                i < l;
                i++
              ) {
                var data =
                  document.getElementById("target_table").rows[i].cells;
                var curr_id = parseInt(data[0].innerHTML);
                if (curr_id == download_target_id) {
                  data[1].innerHTML = target.name;
                  data[2].innerHTML = target.rcs;
                  data[3].innerHTML = target.velocity;
                  data[4].innerHTML = target.corridor_breadth;
                  data[5].innerHTML = target.noftargets;
                  data[6].innerHTML = target.type;
                  data[7].innerHTML = target.running;
                  data[8].innerHTML = target.threeD_waypoints_id;
                  data[9].innerHTML = target.status;
                  data[10].innerHTML = target.maneuvring;
                }
              }
            }

            var alert_txt = "Target downloaded from server ";
            alert(alert_txt);
            $(this).dialog("close");
            //}
          },
          Close: function () {
            alert("Target not downloaded");
            $(this).dialog("close");
          },
        },
      });
    });

    //-------------------3d waypoint upload input dialog-----------------------
    $(function () {
      $("#waypoints_upload_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            // get the waypoint
            var waypoint = getWaypointFromID(upload_waypoint_id);

            if (!nameUnique(waypoint.name, download_waypoints_json)) {
              alert("Error: Waypoint name already in DB");
              return;
            }

            var waypoint_str = JSON.stringify(waypoint, [
              "object_id",
              "id",
              "name",
              "agl_asl",
              "poi_name",
              "targetLocationArray",
              "lat",
              "lon",
              "terrainHeight",
              "flightHeight",
            ]);
            waypoint_str = "[" + waypoint_str + "]";

            var msg_json1 = JSON.stringify([
              { object_id: WAYPOINTS_UPLOAD_ID },
            ]);

            var total_msg_json = [msg_json1, waypoint_str];
            // now call the worker
            sensor_control_worker.postMessage(total_msg_json);

            var alert_txt =
              "Waypoint uploaded to server with name: " + waypoint.name;
            alert(alert_txt);
            $(this).dialog("close");
            //}
          },
          Close: function () {
            alert("Waypoint not uploaded");
            $(this).dialog("close");
          },
        },
      });
    });
    //-------------------waypoints download input dialog-----------------------
    $(function () {
      $("#waypoints_download_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            var waypoint_name = $(
              "#waypoints_download_selectbox option:selected"
            ).text();
            var waypoint = null;
            for (var i = 0; i < download_waypoints_json.length; i++) {
              var curname = download_waypoints_json[i].name;
              if (curname == waypoint_name) {
                waypoint = download_waypoints_json[i];
                break;
              }
            }

            // update the waypoint parameters in the table
            if (waypoint != null) {
              // traverse the table
              var wayp_id, wayp_name, poi_name, agl_asl;
              for (
                var i = 2,
                  l = document.getElementById("3d_waypoints_table").rows.length;
                i < l;
                i++
              ) {
                var data =
                  document.getElementById("3d_waypoints_table").rows[i].cells;
                var curr_id = parseInt(data[0].innerHTML);
                wayp_id = curr_id;
                if (curr_id == download_waypoint_id) {
                  data[0].innerHTML = waypoint.id;
                  data[1].innerHTML = waypoint.name;
                  wayp_name = String(waypoint.name);
                  data[2].innerHTML = waypoint.agl_asl;
                  agl_asl = parseInt(waypoint.agl_asl);
                  data[3].innerHTML = waypoint.poi_name;
                  poi_name = String(waypoint.poi_name);
                  break;
                }
              }

              // also insert this waypoints into the array
              updateWayPoints(
                wayp_id,
                wayp_name,
                poi_name,
                agl_asl,
                waypoint.targetLocationArray
              );
            }

            var alert_txt = "Waypoint downloaded from server ";
            alert(alert_txt);
            $(this).dialog("close");
            //}
          },
          Close: function () {
            alert("Waypoint not downloaded");
            $(this).dialog("close");
          },
        },
      });
    });
    //-------------------sensor download input dialog-----------------------
    $(function () {
      $("#sensor_download_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            var sensor_name = $(
              "#sensor_download_selectbox option:selected"
            ).text();
            var sensor = null;
            for (var i = 0; i < download_sensors_json.length; i++) {
              var curname = download_sensors_json[i].name;
              if (curname == sensor_name) {
                sensor = download_sensors_json[i];
                break;
              }
            }

            // update the sensor parameters in the table
            if (sensor != null) {
              // traverse the table
              for (
                var i = 2,
                  l = document.getElementById("active_sensor_table").rows
                    .length;
                i < l;
                i++
              ) {
                var data = document.getElementById("active_sensor_table").rows[
                  i
                ].cells;
                var curr_id = parseInt(data[0].innerHTML);
                if (curr_id == download_sensor_id) {
                  updateTableDataFromSensor(data, sensor);
                }
              }
            }

            var alert_txt = "Sensor downloaded from server ";
            alert(alert_txt);
            $(this).dialog("close");
            //}
          },
          Close: function () {
            alert("Sensor not downloaded");
            $(this).dialog("close");
          },
        },
      });
    });
    //-------------------sensor upload input dialog-----------------------
    $(function () {
      $("#sensor_upload_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            // get the sensor
            var sensor = getSensorFromID(upload_sensor_id);

            if (!nameUnique(sensor.name, download_sensors_json)) {
              alert("Error: Sensor name already in DB");
              return;
            }

            var sensor_str = stringifySensor(sensor);
            sensor_str = "[" + sensor_str + "]";

            var msg_json1 = JSON.stringify([{ object_id: SENSOR_UPLOAD_ID }]);

            var total_msg_json = [msg_json1, sensor_str];
            // now call the worker
            sensor_control_worker.postMessage(total_msg_json);

            var alert_txt =
              "Sensor uploaded to server with name: " + sensor.name;
            alert(alert_txt);
            $(this).dialog("close");
            //}
          },
          Close: function () {
            alert("Sensor not uploaded");
            $(this).dialog("close");
          },
        },
      });
    });

    //-------------------sensor antenna pattern input dialog-----------------------
    $(function () {
      $("#sensor_antenna_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {},
        },
      });
    });

    //-----------------------------------Replay GUI functions----------------------
    //-----------------------replay ref file -----------------------------------
    $(function () {
      $("#replay_ref_file_download_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            var ref_file_name = $(
              "#replay_ref_file_download_selectbox option:selected"
            ).text();
            var text_ff = document.getElementById("ref_file_field");
            text_ff.value = ref_file_name;
            text_ff.disabled = true;
            $(this).dialog("close");
          },
          Close: function () {
            alert("No ref file downloaded");
            $(this).dialog("close");
          },
        },
      });
    });
    //-----------------------------Replay test file -------------------------------------
    $(function () {
      $("#replay_test_file_download_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            var ref_file_name = $(
              "#replay_test_file_download_selectbox option:selected"
            ).text();
            var text_ff = document.getElementById("test_file_field");
            text_ff.value = ref_file_name;
            text_ff.disabled = true;
            $(this).dialog("close");
          },
          Close: function () {
            alert("No test file downloaded");
            $(this).dialog("close");
          },
        },
      });
    });

    // ---------------------------KML Tab GUI functions-----------------------------
    $("#download_kml_file_button").click(function () {
      $("#kml_file_download_diag_input").dialog({
        autoOpen: false,
        modal: true,
        draggable: false,
        resizable: false,
        responsive: true,
        width: 500,
        buttons: {
          OK: function () {
            var kml_file_name = $(
              "#kml_file_download_selectbox option:selected"
            ).text();
            $("#kml_table tbody").append(
              $("#kml_table tbody tr:first").clone()
            );
            $("#kml_table tbody tr:last td:first").html(kml_file_name);
            $("#kml_table tr:last td:last input").attr("disabled", "disabled");
            $("#kml_table tr:last")
              .find('input[type="checkbox"]')
              .prop("checked", true);
            $(this).dialog("close");

            // send request to get this kml file
            var getkmlfile_request = new request_wrapper();
            getkmlfile_request.request_type = "getKMLFile";
            getkmlfile_request.nbr_args = 1;
            getkmlfile_request.args = [JSON.stringify(kml_file_name)];
            var query = JSON.stringify(getkmlfile_request);
            geoplot_worker.postMessage([
              getkmlfile_request.request_type,
              query,
            ]);
          },
          Close: function () {
            alert("No kml file downloaded");
            $(this).dialog("close");
          },
        },
      });
    });

    //--------------------------- add flight circle to map--------------------

    var flightFeatureOverlay = new ol.FeatureOverlay({
      map: map,
      features: [circleFeatureFlight],

      style: new ol.style.Style({
        fill: new ol.style.Fill({
          color: "rgba(50, 50, 220, 0.3)",
        }),
        stroke: new ol.style.Stroke({
          width: 4,
          color: "rgba(10, 10, 220, 0.8)",
        }),
      }),
    });
  }

  function downloadReplayRefFile() {
    getReplayRefFiles(replay_worker);

    var title = "Download replay reference file from server:";
    $("#replay_ref_file_download_diag_input").dialog("option", "title", title);
    $("#replay_ref_file_download_diag_input").dialog("open");
  }

  function downloadReplayTestFile() {
    getReplayTestFiles(replay_worker);
    var title = "Download replay test file from server:";
    $("#replay_test_file_download_diag_input").dialog("option", "title", title);
    $("#replay_test_file_download_diag_input").dialog("open");
  }

  function computeDetailedRadioPropagation() {
    var params = getRadioPropGrid();

    var query_id = getRandomInt(0, 99999999);
    var oitm = 1;
    if (params[0] == "itwom") {
      oitm = 0;
    }

    pdf_worker.postMessage([
      29824733,
      params[6],
      params[7],
      params[8],
      params[12],
      params[13],
      params[14],
      params[1],
      params[2],
      params[3],
      params[11],
      params[4],
      params[9],
      params[5],
      oitm,
      1,
      params[10],
    ]);
    //
    delete query;
  }

  // download kml files
  function downloadKMLFile() {
    // send request to get kml filenames
    var getkmlfilenames_request = new request_wrapper();
    getkmlfilenames_request.request_type = "getKMLFileList";
    getkmlfilenames_request.nbr_args = 0;
    getkmlfilenames_request.args = [];
    var query = JSON.stringify(getkmlfilenames_request);
    geoplot_worker.postMessage([getkmlfilenames_request.request_type, query]);

    var title = "Download kml file from server:";
    $("#kml_file_download_diag_input").dialog("option", "title", title);
    $("#kml_file_download_diag_input").dialog("open");
  }

  function dem_tab_clicked(source) {}

  // this function will be called whenever dispo tab is clicked
  function dispo_tab_clicked(source) {
    var x = document.getElementById("system_table").rows.length;
    var data_system = document.getElementById("system_table").rows[x - 1].cells;
    var y = document.getElementById("dispo_table").rows.length;
    var data_dispo = document.getElementById("dispo_table").rows[y - 1].cells;
    data_dispo[1].innerHTML = data_system[0].innerHTML;
  }

  init();
  bindEvents();
})(); // closure
