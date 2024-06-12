// This request_wrapper is intended to handle data to the python server
function request_wrapper() {
  this.request_type = "NONE";
  this.nbr_args = 0;
  this.args = [];
}

(function () {
  // use closure to avoid global variables (otherwise memory leak in browser)

  var ws = null;

  //------------ OBJECT IDS for communication with the sim server
  var test_track_deletion_time = 3; // 3s default
  var ref_track_deletion_time = 3; // 3s default

  var refTargsArray = []; // will contain all the reference targets during replay
  var testTargsArray = []; // will contain all the test targets during replay

  var blueLiveTargsArray = []; // will contain all the blue live targets (not replay but user defined)
  var redLiveTargsArray = []; // will contain all the red live targets (not replay but user defined)

  function Target(
    id,
    team,
    lat,
    lon,
    update_time,
    threed_waypoints_id,
    height,
    terrainHeight,
    name
  ) {
    this.id = id;
    this.name = name;
    this.lat = lat;
    this.lon = lon;
    this.team = team;
    this.update_time = update_time;
    this.threed_waypoints_id = threed_waypoints_id;
    this.height = height;
    this.terrainHeight = terrainHeight;
  }

  function checkUpdate(data) {
    // will check and update the array
    var res = JSON.parse(data);
    changes = res.args[0];
    var id = parseInt(changes.data.id_nr);
    var lat = parseFloat(changes.data.lat);
    var lon = parseFloat(changes.data.lon);
    var height = parseFloat(changes.data.height);
    var team = changes.data.team;
    var wayp_id = changes.data.threed_waypoints_id;
    var update_time = changes.data.update_time;
    var replay_date = new Date();
    var curr_time = replay_date.getTime();
    var name = changes.data.name;
    var terrainHeight = parseFloat(changes.data.terrainheight);
    ///////////////////////////   FOR LIVE TARGETS //////////////////
    if (name != "ref" && name != "test") {
      // this is not a replay target, but a live target
      var index = -1;
      if (team.includes("blue")) {
        for (var i = 0; i < blueLiveTargsArray.length; i++) {
          if (blueLiveTargsArray[i].id == id) {
            index = i;
            break;
          }
        }

        if (index == -1) {
          var targ = new Target(
            id,
            team,
            lat,
            lon,
            update_time,
            wayp_id,
            height,
            terrainHeight,
            name
          );
          blueLiveTargsArray.push(targ);
        } else {
          blueLiveTargsArray[index].lat = lat;
          blueLiveTargsArray[index].lon = lon;
          blueLiveTargsArray[index].update_time = update_time;
          blueLiveTargsArray[index].height = height;
          blueLiveTargsArray[index].terrainHeight = terrainHeight;
        }
      }
      if (team.includes("red")) {
        for (var i = 0; i < redLiveTargsArray.length; i++) {
          if (redLiveTargsArray[i].id == id) {
            index = i;
            break;
          }
        }

        if (index == -1) {
          var targ = new Target(id, team, lat, lon, update_time);
          redLiveTargsArray.push(targ);
        } else {
          redLiveTargsArray[index].lat = lat;
          redLiveTargsArray[index].lon = lon;
          redLiveTargsArray[index].update_time = update_time;
        }
      }
    }

    ///////////////////////////   PERIODICALLY SEND ALL DAT TO THE MAIN THREAD //////////////////////////////////////////////
    var tgt_json = {};
    tgt_json["request_type"] = "REF_TGT_UPDATE";
    tgt_json["data"] = refTargsArray;
    self.postMessage(JSON.stringify(tgt_json));

    tgt_json = {};
    tgt_json["request_type"] = "TEST_TGT_UPDATE";
    tgt_json["data"] = testTargsArray;
    self.postMessage(JSON.stringify(tgt_json));

    tgt_json = {};
    tgt_json["request_type"] = "LIVE_BLUE_TGT_UPDATE";
    tgt_json["data"] = blueLiveTargsArray;
    self.postMessage(JSON.stringify(tgt_json));

    tgt_json = {};
    tgt_json["request_type"] = "LIVE_RED_TGT_UPDATE";
    tgt_json["data"] = redLiveTargsArray;
    self.postMessage(JSON.stringify(tgt_json));

    last_replay_time = curr_time;

    // ------------------------------also remove dead replay targets
    for (var i = 0; i < refTargsArray.length; i++) {
      if (
        update_time - refTargsArray[i].update_time >
        ref_track_deletion_time * 1000
      ) {
        refTargsArray.splice(i, 1);
      }
    }

    // also remove dead replay targets
    for (var i = 0; i < testTargsArray.length; i++) {
      if (
        update_time - testTargsArray[i].update_time >
        test_track_deletion_time * 1000
      ) {
        testTargsArray.splice(i, 1);
      }
    }
    // ------------------------------also remove dead live targets
    for (var i = 0; i < redLiveTargsArray.length; i++) {
      if (update_time - redLiveTargsArray[i].update_time > 15000) {
        // more than 15s
        redLiveTargsArray.splice(i, 1);
      }
    }

    // also remove dead replay targets
    for (var i = 0; i < blueLiveTargsArray.length; i++) {
      if (update_time - blueLiveTargsArray[i].update_time > 15000) {
        // more than 15s
        blueLiveTargsArray.splice(i, 1);
      }
    }
  }

  function stopWsServer() {
    ws.close();
  }

  function startWsServer() {
    ws = new WebSocket(ws_addr);
    ws.onmessage = function (
      evt // receive messages from Python server
    ) {
      var data = evt.data;
      var res = JSON.parse(data);
      var changes = res.args[0];
      var action = changes.action;
      var table = changes.table;

      if (action == "UPDATE" && table == "blue_live_target") {
        // just handle the change in targets (for replay)
        checkUpdate(evt.data);
      } else if (action == "UPDATE" && table == "red_live_target") {
        // just handle the change in targets (for replay)
        setTimeout(function () {
          checkUpdate(evt.data);
        }, 10);
      } else {
        // all other DB changes will be handled by the main thread
        self.postMessage(evt.data);
      }
    };

    ws.onopen = function (event) {
      console.log(
        "-------sensorControlWorker: SENSOR CONTROL WebSocket opened"
      );
      self.postMessage(JSON.stringify("OPEN"));
    };
    ws.onclose = function (evt) {
      console.log(
        "-------sensorControlWorker: SENSOR CONTROL WebSocket closed"
      );
    };
    ws.onerror = function (evt) {
      console.log("-------SIM WebSocket error!!!!!!!!!!!!");
      self.postMessage(JSON.stringify("ERROR"));
    };
  }

  self.addEventListener(
    "message",
    function (e) {
      // receive messages from the main thread

      anz_x = e.data[0];
      console.log("sensorControlWorker received from master Client: ", e.data);
      // this is to update ws server address and port
      if (anz_x == 8993493) {
        ws_addr = e.data[1];
        startWsServer();
      }

      if (anz_x == 8993455) {
        // stop
        console.log(
          "-------------------------------------->emptying blueLiveTargsArray and redLiveTargsArray"
        );
        refTargsArray = [];
        testTargsArray = [];
        stopWsServer();
      }

      // this is to set the replay target deletion times
      if (anz_x == 730678) {
        console.log(
          "sensorControlWorker setting client target deletion times: ",
          e.data[1][0],
          e.data[1][1]
        );
        ref_track_deletion_time = parseFloat(e.data[1][0]);
        test_track_deletion_time = parseFloat(e.data[1][1]);
        return;
      }

      var timeout_if_ws_closed_ms = 0;
      if (ws.readyState == ws.CLOSED) {
        console.log(
          "----- websocket to SIM server is closed, attempting to reopen..."
        );
        startWsServer();
        timeout_if_ws_closed_ms = 100;
      }
      var request_type = e.data[0];

      if (request_type == "insert_AIR") {
        var query = e.data[1];
        console.log(
          "----Sending following insert AIR message request to sensorControl server: " +
            query
        );
        ws.send(query);
      }

      setTimeout(function () {
        // will wait for time specified by 'timeout_if_ws_closed_ms', until executing code below
        // if websocket was closed, the 'timeout_if_ws_closed_ms' is set to a higher value,
        // in order to give the websocket time to be reopened
        if (ws.readyState != ws.OPEN) {
          console.log(
            "----- sensorControlWorker.js: did not manage to open websocket to SENSOR CONTROL server within the timeout"
          );
        } else {
          // websocket is open
          var query = e.data[1];
          if (query != null) {
            var res = JSON.parse(query);
            if (res.request_type == "AIR_START") {
              update_rate = res.args[1];
              test_track_deletion_time = res.args[2];
              ref_track_deletion_time = res.args[3];
            }

            ws.send(query);
          }
        }
      }, timeout_if_ws_closed_ms);
    },
    false
  );
})(); // closure
