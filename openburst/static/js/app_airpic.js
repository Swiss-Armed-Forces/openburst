function getRandomInt(min, max) {
  min = Math.ceil(min);
  max = Math.floor(max);
  return Math.floor(Math.random() * (max - min)) + min;
}

(function () {
  // use closure to avoid global variables (otherwise memory leak in browser)

  var activeMonostaticArray = []; // wil contain all the active sensors placed by the user

  var curr_lat;
  var curr_lon;
  var test_track_id_is_unicode = 0;
  var ref_track_id_is_unicode = 1;
  var terrain_mid_point_height;
  var nofRunningCoverages = 0;
  var pdf_worker, geoplot_worker, target_sim_worker, detection_sim_worker;
  var geoplot_layers = [];
  var geoplot_track_layers = []; // this will be a 2D array

  var runningSensorID = getRandomInt(500, 600);
  var runningTargetID = getRandomInt(0, 500);
  var runningWaypId = getRandomInt(0, 9999999);
  var running_poi_id = getRandomInt(700, 800);

  var bern = ol.proj.fromLonLat([8.3, 47.0]);

  var view;
  var map;
  var sim = new Sim();
  var sensorAnimationSource;

  var dataNr = 0; // for space charts
  //-----------------------------------------------------------------------------
  var TARGET_GUI_ACTION = 3;

  // circle for the flight pos
  var flight_circle = new ol.geom.Circle(
    ol.proj.transform([10, 1], "EPSG:4326", "EPSG:3857"),
    200,
    "XY"
  );
  var circleFeatureFlight = new ol.Feature(flight_circle);
  // html5 local data storage: to store scenarios
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

  // this function should return the same as functions.py: getTime()
  // see https://currentmillis.com/
  function getTime() {
    // get the time in milliseconds since the UNIX epoch (January 1, 1970 00:00:00 UTC)
    return new Date().getTime();
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

  function checkAddRad(data) {
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
      activeMonostaticArray[ind].min_detection_range = data.min_detection_range;
      activeMonostaticArray[ind].max_detection_range = data.max_detection_range;
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

  function target_sim_worker_listener(data) {
    var res = JSON.parse(data);
    if (res == "ERROR") {
      alert("Connection to SIM server lost. Please restart SIM if running");
    }

    if (res.request_type == "db_fetch") {
      // data was requested from the DB
      data = res.args[0];
      var data_type = data.data_type;
      var table = data.table;
      if (data_type == "RADINT" && table == "blue_live_rad") {
        // first remove all the current rad in the client
      }
    } else if (res.request_type == "db_update") {
      // the data bank changed
      changes = res.args[0];
      var action = changes.action;
      var table = changes.table;
      //console.log("action = ", action, ", table = ", table)
      // -------------------------DB UPDATED RAD----------------------------------------
      if (action == "UPDATE" && table == "blue_live_rad") {
        console.log("updating rad....");
        checkAddRad(changes.data);
      }
      if (action == "INSERT" && table == "blue_live_rad") {
        console.log("inserting rad....");
        checkAddRad(changes.data);
      }

      // -------------------------DB UPDATED TARGET ----------------------------------------
      if (action == "UPDATE" && table == "blue_live_target") {
        //console.log("updating target....")
        updateTargetCirclePosition(
          parseInt(changes.data.id_nr),
          parseFloat(changes.data.lat),
          parseFloat(changes.data.lon)
        ); //
        var targ_id = parseInt(changes.data.id_nr);
        var terrainHeight = parseInt(changes.data.terrainheight);
        var targetHeight = parseInt(changes.data.height);
        //console.log("parsed: ", targ_id, terrainHeight, targetHeight)
        checkAddTarget(targ_id, terrainHeight, targetHeight);
        updateLiveTicker(targ_id, terrainHeight, targetHeight);
      }
      if (action == "INSERT" && table == "blue_live_target") {
        console.log("inserting target....");
        var targ_id = parseInt(changes.data.id_nr);
        checkAddTarget(targ_id);
      }
    }
  }

  function detection_sim_worker_listener(data) {
    var res = JSON.parse(data);

    if (res.request_type == "db_update") {
      //changes = res.args[0];
      var action = res.action;
      var table = res.table;
      var node = res.node;
      //console.log("action, table, node = ",action, table, node)
      fdata = res.data;

      // -------------------------DB UPDATED DETECTION: DRAW CIRCLE on MAP ----------------------------------------
      if (action == "UPDATE" && table == "blue_live_detection") {
        //console.log(".....updating detection")
        for (i = 0; i < fdata.length; i++) {
          checkAddDetection(fdata[i]);
        }
      }

      // -------------------------DB UPDATED DETECTION: UPDATE THE Live Graphs ----------------------------------------

      if (action == "UPDATE" && table == "blue_live_detection") {
        done = false;
        for (i = 0; i < fdata.length; i++) {
          data = fdata[i];
          //console.log(".....updating detection time series")
          var targ_id = parseInt(data[0]);
          var rad_id = parseInt(data[1]);
          var pd = parseFloat(data[3]);
          var plot = parseFloat(data[4]);
          var track = parseFloat(data[5]);

          var SELECTED_TARGET_ID = parseInt(
            document.getElementById("targetidinput").value
          );

          if (!isNaN(SELECTED_TARGET_ID)) {
            if (targ_id.toString().endsWith(SELECTED_TARGET_ID.toString())) {
              if (isNaN(rad_id) || isNaN(pd) || isNaN(plot) || isNaN(track)) {
              } else {
                updateSpecificTimeSeries(rad_id, pd, plot, track);
                done = true;
              }
            }
          }
        }
        if (done == false) {
          initTimeAnalysis();
          resetSimTargetTicker();
        }
      }
    }
  }

  //
  function checkAddDetection(data) {
    targ_id = data.targ_id; //data[0]
    sensor_id = data.sensor_id; //data[1]

    var ind = existsDetection(targ_id, sensor_id);
    if (ind != null) {
      // this detection is in the array
      if (data.track > 0) {
        detectionArray[ind].lat = data.lat; //parseFloat(data[7]);
        detectionArray[ind].lon = data.lon; //parseFloat(data[8]);
        detectionArray[ind].height = data.height; //parseFloat(data[9]);
        detectionArray[ind].detection_time = data.update_time; //parseFloat(data[6]);
        updateDetectionCirclePosition(targ_id, sensor_id, data.lat, data.lon);
      } else {
        console.log(
          "detection exists..but track=0 for targ: ",
          targ_id,
          ", sensor_id: ",
          sensor_id
        );
        removeDetection(targ_id, sensor_id);
      }
    } else {
      // this detection is not in the array
      if (data.track > 0) {
        console.log("creating detection: ", data);
        var now = null;
        var detection = new Detection(
          sim.DETECTION_PARAM_ID,
          targ_id,
          data.lat,
          data.lon,
          data.height,
          sensor_id,
          data.update_time
        );
        detection.object_id = sim.DETECTION_PARAM_ID;
        console.log(
          "detected unknown target..adding detection: ",
          targ_id,
          sensor_id
        ); //
        detectionArray.push(detection);
        var det = new DetectionCircle(targ_id, sensor_id);
        detectionCircleArray.push(det);
      }
    }
  }

  function POI(object_id, id, poi_name, poi_lat, poi_lon) {
    this.object_id = object_id;
    this.id = id;
    this.name = poi_name;
    this.lat = poi_lat;
    this.lon = poi_lon;
  }

  function geoplot_worker_listener(data) {
    var res = JSON.parse(data);
    if (res.request_type == "activeCoveragePoints_response") {
      // active coverage
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

      var colorpicker = document.getElementById("color_picker1");
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

        //if (kml_name == "0"){
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
          $("#kml_table tbody").append($("#kml_table tbody tr:first").clone());
          $("#kml_table tbody tr:last td:first").html(kml_file_name);
          $("#kml_table tr:last td:last input").attr("disabled", "disabled");
          $("#kml_table tr:last")
            .find('input[type="checkbox"]')
            .prop("checked", true);
        }
        //}
      }
    } else if (res.request_type == "getKMLFileList_response") {
      // this are kml file names
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
      // these are kml files
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

      var colorpicker = document.getElementById("color_picker1");
      var custom_color = document.getElementById(
        "color_picker_checker"
      ).checked;

      var hexColor = colorpicker.value;
      var color = ol.color.asArray(hexColor);
      color = color.slice();
      color[3] = 0.4;
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
          //console.log("color is customized....")
          kml_features[i].setStyle(style);
        } else {
        }
        ssource.addFeature(kml_features[i]);
        geoplot_track_layers[currind].push(vector);
        map.addLayer(vector);
      }
    } else {
      // these are coverage kml files
      // first remove all existing geoplot layers from map
      removeGeoPlotLayers();

      var kmlstring = res;
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
        for (var i = 0; i < kml_features.length; i++) {
          var ssource = new ol.source.Vector();
          var vector = new ol.layer.Vector({
            source: ssource,
            format: kml,
            opacity: 0.5,
          });
          ssource.addFeature(kml_features[i]);
          geoplot_layers.push(vector);
          map.addLayer(vector);
        }
      } else {
      }
    }
  }

  function pdf_worker_listener(data) {
    var res = JSON.parse(data);
    var los = parseFloat(res[0]);
    if (los === 0) {
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
    }
  }

  // queries the proxy server and inits the workers with the correct ws addresses
  // assumes that the global variable proxy_server is set
  function initWorkersWithServers() {
    var proxy_ws = new WebSocket(proxy_server);

    proxy_ws.onmessage = function (evt) {
      var msg = JSON.parse(evt.data);

      switch (msg[0]) {
        case "dem":
          pdf_worker = new Worker("/static/js/pdfWorker.js");
          var s_prim = msg[1];
          pdf_worker.postMessage([8993493, s_prim]); // set the correct dem server address and port
          pdf_worker.addEventListener("message", function (e) {
            pdf_worker_listener(e.data);
          });
          break;
        case "geoplot":
          geoplot_worker = new Worker("/static/js/geoPlotWorker.js");
          var s_prim = msg[1];
          geoplot_worker.postMessage([8993493, s_prim]); // set the correct dem server address and port
          geoplot_worker.addEventListener("message", function (e) {
            geoplot_worker_listener(e.data);
          });
          break;
        case "target_sim":
          target_sim_worker = new Worker("/static/js/targetSimWorker.js");
          var s_prim = msg[1];
          target_sim_worker.postMessage([8993493, s_prim]); // set the correct dem server address and port
          target_sim_worker.addEventListener("message", function (e) {
            target_sim_worker_listener(e.data);
          });

          break;
        case "detection_sim":
          detection_sim_worker = new Worker("/static/js/detectionSimWorker.js");
          var s_prim = msg[1];
          detection_sim_worker.postMessage([8993493, s_prim]); // set the correct dem server address and port
          detection_sim_worker.addEventListener("message", function (e) {
            detection_sim_worker_listener(e.data);
          });

          break;

        default:
          break;
      }
    };
    proxy_ws.onopen = function (event) {};
    proxy_ws.onclose = function (evt) {};
    // query for DEM WS Server address
    proxy_ws.onopen = function () {
      proxy_ws.send("dem");
      proxy_ws.send("geoplot");
      proxy_ws.send("detection_sim");
    };
  }

  function Detection(object_id, targ_id, lat, lon, height, sensor_id, now) {
    this.object_id = object_id;
    this.targ_id = targ_id;
    this.sensor_id = sensor_id;
    this.lat = lat;
    this.lon = lon;
    this.height = height;
    this.detection_time = now;
  }
  var detectionArray = []; // this will contain all the detection

  //------------ for simulating the detection
  function DetectionCircle(targ_id, sensor_id) {
    this.targ_id = targ_id;
    this.sensor_id = sensor_id;

    var str_id1 = getStringFromUniCodeID(targ_id, test_track_id_is_unicode); //targ_id.toString()//
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
      // if unicode representation is used in ID get back the original ID
      var chunks = chunkString(id.toString(), 2); // get chunks of two
      var corrected_id = "";
      for (i = 0; i < chunks.length; i++) {
        corrected_id = corrected_id + String.fromCharCode(chunks[i]);
      }
      return corrected_id;
    }
  }
  var detectionCircleArray = [];

  function fetchAir() {
    startDetections();
  }

  function fetchRadint() {
    return;
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
      }
    }
  }

  function clearDetections() {
    // removes all detections from DB
    var db_request = new request_wrapper();
    db_request.request_type = "clearDETECTION";
    db_request.nbr_args = 0;
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    target_sim_worker.postMessage([db_request.request_type, query]);
  }

  function clearRadint() {
    // removes all RADINT rows from DB
    var db_request = new request_wrapper();
    db_request.request_type = "clearRADINT";
    db_request.nbr_args = 0;
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    target_sim_worker.postMessage([db_request.request_type, query]);
  }

  function bindEvents() {
    $("#reset_target_ticker").on("click", function () {
      resetSimTargetTicker();
    });
    $("#fetch_radint").on("click", function () {
      fetchRadint();
    });
    $("#fetch_air").on("click", function () {
      fetchAir();
    });
    $("#clear_radint").on("click", function () {
      clearRadint();
      clearDetections();
    });

    $("#goto").on("click", function () {
      gotoLatLon();
    });
    $("#css3-tabstrip-0-0").on("click", function () {
      homeTabSelected();
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

  function initTimeAnalysis() {}

  function resetSpaceAnalysis() {}

  function gotoLatLon() {
    var lat = parseFloat(document.getElementById("lat2d").value);
    var lon = parseFloat(document.getElementById("lon2d").value);

    var curr_ort = ol.proj.fromLonLat([lon, lat]);
    view.setCenter(curr_ort);
    gotoLatLonMap(lat, lon);
  }

  /////////////////////////////////// functions to debug WORKER-----------------------------------

  function updateSpecificTimeSeries(rad_id, pd, plot, track) {
    console.log("gotten: ", rad_id, pd, plot, track);
  }

  //------------------------------------------------3D Mesh FUNCTIONS --------------------------------

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
    ////console.log("nof rows = ", x, ", cell data before = ", data[0].innerHTML);

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

    var sensor = new ActiveMonostaticSensor(
      sim.ACTIVE_MONOSTATIC_SENSOR_PARAM_ID,
      runningSensorID,
      "",
      c_lat,
      c_lon,
      radar_circle
    );
    activeMonostaticArray.push(sensor);

    // add also series to the TIME chart 1
    var sens_arr = [];
    for (var i = 0, l = activeMonostaticArray.length; i < l; i++) {
      sens_arr.push(activeMonostaticArray[i].id_nr.toString());
    }

    // increase the sensor ID
    runningSensorID++;
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

  function removeWaypoint($row) {
    var id = $row.text().split("\n")[1].trim();
    //console.log("removing waypoint with ID: ", id);
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

  function removeActiveSensorFromDB(id) {
    var db_request = new request_wrapper();
    db_request.request_type = "removeRADINT";
    db_request.nbr_args = 0;
    db_request.args.push(JSON.stringify(id));
    db_request.nbr_args = db_request.nbr_args + 1;
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    target_sim_worker.postMessage([db_request.request_type, query]);
  }

  function removeTargetFromDB(id) {
    var db_request = new request_wrapper();
    db_request.request_type = "removeAIR_TARGET";
    db_request.nbr_args = 0;
    db_request.args.push(JSON.stringify(id));
    db_request.nbr_args = db_request.nbr_args + 1;
    db_request.args.push(JSON.stringify(team));
    db_request.nbr_args = db_request.nbr_args + 1;
    var query = JSON.stringify(db_request);
    target_sim_worker.postMessage([db_request.request_type, query]);
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
    target_sim_worker.postMessage([db_request.request_type, query]);
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
    target_sim_worker.postMessage([db_request.request_type, query]);
  }

  function removeActiveMonostaticSensor($row) {
    var id = $row.text().split("\n")[1].trim();
    // now go through the array and remove the feature
    var ind = -1;
    for (var i = 0, l = activeMonostaticArray.length; i < l; i++) {
      if (parseInt(activeMonostaticArray[i].id_nr) == id) {
        var layer = activeMonostaticArray[i].layer;
        var dump_ort = ol.proj.fromLonLat([-7, -40]); // debug: this has to be corrected to really remove the circle and not dump it
        layer.setCenter(dump_ort); // TBD: this has to be corrected to really remove the circle and not dump it
        ind = i;

        break;
      }
    }
    if (ind > -1) {
      activeMonostaticArray.splice(ind, 1);
    }

    // also remove this from the DB
    removeActiveSensorFromDB(id);
  }

  function updateTargetCirclePosition(id, lat, lon) {
    // move the target circle to this point
    for (var i = 0, ll = targetCircleArray.length; i < ll; i++) {
      if (targetCircleArray[i].id == id) {
        var curr_targ_ort = ol.proj.fromLonLat([lon, lat]);
        var src = targetCircleArray[i].markerLayer.getSource();
        var features = src.getFeatures();
        var target_circle = features[0];
        target_circle.getGeometry().setCenter(curr_targ_ort);
      }
    }
  }

  function updateDetectionCirclePosition(targ_id, sensor_id, lat, lon) {
    for (var i = 0, ll = detectionCircleArray.length; i < ll; i++) {
      if (
        detectionCircleArray[i].targ_id == targ_id &&
        detectionCircleArray[i].sensor_id == sensor_id
      ) {
        var curr_det_ort = ol.proj.fromLonLat([lon, lat]);
        var src = detectionCircleArray[i].markerLayer.getSource();
        var features = src.getFeatures();
        var det_circle = features[0];
        det_circle.getGeometry().setCenter(curr_det_ort);
      }
    }
  }

  function updateTableFromRadArray(ind) {
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
      ////console.log("rows = ", document.getElementById("active_sensor_table").rows.length, ", i = ", i, ", current ID = ", parseInt(data[0].innerHTML), ", ", data[1].innerHTML);
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

  function gotoLatLonMap(lat, lon) {
    curr_lat = lat;
    curr_lon = lon;
    document.getElementById("lat2d").value = lat;
    document.getElementById("lon2d").value = lon;
    changeFlightLocationOnMap(curr_lat, curr_lon);

    pdf_worker.postMessage([6200901, curr_lat, curr_lon, poi.lat, poi.lon]); // ask for the terrain height
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

  function removeGeoPlotLayers() {
    while (geoplot_layers.length > 0) {
      map.removeLayer(geoplot_layers.splice(i, 1)[0]);
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

  function onDocumentKeyRelease(event) {
    var keyCode = event.which;
  }

  function init() {
    document.addEventListener("keydown", onDocumentKeyRelease, false);
    initWorkersWithServers();
    poi = new POI(sim.POI_PARAM_ID, running_poi_id, "", 46.25, 7.12);

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
      target_sim_worker.postMessage(total_msg_json);
      //-------------------------------------------------------
    });

    // -------set up functions for the target table
    $(".target-table-update").click(function () {});

    $(".target-table-remove").click(function () {
      //if (nofRunningCoverages == 0){
      var id = $(this).parents("tr").text().split("\n")[1].trim();
      removeTargetFromDB(id);
      removeTarget($(this).parents("tr"));
      $(this).parents("tr").detach();
    });
    $(".target-table-down").click(function () {
      //console.log("target table down")
      var id = $(this).parents("tr").text().split("\n")[1].trim();
      download_target_id = id;

      // download target from server
      var msg_json1 = JSON.stringify([{ object_id: TARGET_DOWNLOAD_ID }]);
      var total_msg_json = [msg_json1];
      // now call the worker to get all the targets saved on the server
      target_sim_worker.postMessage(total_msg_json);

      var title = "Download target from server with name";
      $("#target_download_diag_input").dialog("option", "title", title);
      $("#target_download_diag_input").dialog("open");
    });

    $(".target-table-up").click(function () {
      // ask for the currently saved targets: so that the variabe download_targets_json is updated..
      var msg_json1 = JSON.stringify([{ object_id: TARGET_DOWNLOAD_ID }]);
      var total_msg_json = [msg_json1];
      // now call the worker to get all the targets saved on the server
      target_sim_worker.postMessage(total_msg_json);
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
    });

    // set POI if double clicked
    map.on("dblclick", function (evt) {
      var lonlat = ol.proj.transform(evt.coordinate, "EPSG:3857", "EPSG:4326");
      poi.lon = lonlat[0];
      poi.lat = lonlat[1];

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

            //console.log("going to upload trigger with json: ", total_msg_json)
            // now call the worker
            target_sim_worker.postMessage(total_msg_json);

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
            //console.log("selected kml file name = ", kml_file_name)
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

  init();
  bindEvents();
})(); // closure
