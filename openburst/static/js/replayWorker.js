(function () {
  // use closure to avoid global variables to avoid memory leak in browser

  var ws = null;

  var refTargsArray = []; // will contain all the reference targets during replay
  var testTargsArray = []; // will contain all the test targets during replay

  var last_replay_time = 0;
  var CLIENT_REPLAY_UPDATE_RATE = 1000.0; // we will only send the data to the main thread every CLIENT_REPLAY_UPDATE_RATE seconds
  var ref_track_deletion_time = 30; // [s] will be set through query
  var test_track_deletion_time = 30; // [s] will be set through query

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
    var update_time = changes.data.update_time; //replay_date.getTime();
    var curr_time = Date.now(); //replay_date.getTime();
    var name = changes.data.name;
    var terrainHeight = parseFloat(changes.data.terrainheight);

    // replay targets
    if (team.includes("blue")) {
      var index = -1;
      for (var i = 0; i < refTargsArray.length; i++) {
        if (refTargsArray[i].id == id) {
          index = i;
          break;
        }
      }

      if (index == -1) {
        var targ = new Target(id, team, lat, lon, update_time);
        refTargsArray.push(targ);
      } else {
        refTargsArray[index].lat = lat;
        refTargsArray[index].lon = lon;
        refTargsArray[index].update_time = update_time;
      }
    } else if (team.includes("red")) {
      var index = -1;
      for (var i = 0; i < testTargsArray.length; i++) {
        if (testTargsArray[i].id == id) {
          index = i;
          break;
        }
      }

      if (index == -1) {
        var targ = new Target(id, team, lat, lon, update_time);
        testTargsArray.push(targ);
      } else {
        testTargsArray[index].lat = lat;
        testTargsArray[index].lon = lon;
        testTargsArray[index].update_time = update_time;
      }
    } else {
    }

    ///////////////////////////   SEND ALL DAT TO THE MAIN THREAD ///////////////////////

    if (curr_time - last_replay_time > CLIENT_REPLAY_UPDATE_RATE) {
      // just send after 1 second
      var tgt_json = {};
      tgt_json["request_type"] = "REF_TGT_UPDATE";
      tgt_json["data"] = refTargsArray;
      self.postMessage(JSON.stringify(tgt_json));

      tgt_json = {};
      tgt_json["request_type"] = "TEST_TGT_UPDATE";
      tgt_json["data"] = testTargsArray;
      self.postMessage(JSON.stringify(tgt_json));
      last_replay_time = curr_time;
    }

    // ------------------------------also remove dead replay targets
    for (var i = 0; i < refTargsArray.length; i++) {
      if (
        update_time - refTargsArray[i].update_time >
        ref_track_deletion_time * 1000
      ) {
        refTargsArray.splice(i, 1);
      }
    }
  }

  function startWsServer() {
    ws = new WebSocket(ws_addr);
    ws.onmessage = function (evt) {
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
        checkUpdate(evt.data);
      } else {
        // all other DB changes (INSERT, DELETE etc. ) will be handled by the main thread
        self.postMessage(evt.data);
      }
    };
    ws.onopen = function (event) {
      console.log("-------Replay WebSocket opened");
    };
    ws.onclose = function (evt) {
      console.log("-------Replay WebSocket closed");
    };
  }

  // receive input from main javascript thread
  self.addEventListener(
    "message",
    function (e) {
      if (e.data.source == "react-devtools-content-script") {
        return;
      }
      console.log("----replayWorker.js got message from MAIN thread: ", e.data);
      // data coming in:
      var anz_x = e.data[0];

      // this is to update ws server address and port
      if (anz_x == 8993493) {
        console.log("----replayWorker.js : got 8993493 from MAIN thread");
        ws_addr = e.data[1];
        startWsServer();
      }
      var timeout_if_ws_closed_ms = 0;
      if (ws.readyState == ws.CLOSED) {
        console.log(
          "----- replayWorker: websocket to replayWorker is closed, attempting to reopen..."
        );
        startWsServer();
        timeout_if_ws_closed_ms = 3000;
      }

      var request_type = e.data[0];
      console.log(
        "----replayWorker: from MAIN thread request_type = ",
        request_type
      );

      setTimeout(function () {
        // will wait for time specified by 'timeout_if_ws_closed_ms', until executing code below
        // if websocket was closed, the 'timeout_if_ws_closed_ms' is set to a higher value,
        // in order to give the websocket time to be reopened
        if (ws.readyState != ws.OPEN) {
          console.log(
            "----- replayWorker: did not manage to OPEN websocket to replayserver within the timeout"
          );
        } else {
          // websocket is open

          console.log("----- replayWorker: websocket to server is open");

          if (request_type == "REPLAY_START_SEND_TEST_DATA_FLOW") {
            var query = e.data[1];

            var res = JSON.parse(query);
            test_track_deletion_time = parseFloat(res.args[4]);
            ref_track_deletion_time = parseFloat(res.args[5]);
            console.log(
              "----replayWorker: Sending following request to replayServer: " +
                query
            );
            ws.send(query);
          }
          if (request_type == "REPLAY_STOP_SEND_TEST_DATA_FLOW") {
            var query = e.data[1];
            console.log(
              "----replayWorker: Sending following request to python replayServer: " +
                query
            );
            ws.send(query);
            refTargsArray = [];
            testTargsArray = [];
          }
          if (request_type == "GET_REPLAY_REF_DATA") {
            var query = e.data[1];
            console.log(
              "----replayWorker: Sending following request to python replayServer: " +
                query
            );
            ws.send(query);
          }
          if (request_type == "GET_REPLAY_TEST_DATA") {
            var query = e.data[1];
            console.log(
              "----replayWorker: Sending following request to python replayServer: " +
                query
            );
            ws.send(query);
          }
        }
      }, timeout_if_ws_closed_ms);
    },
    false
  );
})(); // closure
