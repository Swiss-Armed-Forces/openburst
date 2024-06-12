// This request_wrapper is intended to handle data to the python server
function request_wrapper() {
  this.request_type = "NONE";
  this.nbr_args = 0;
  this.args = [];
}

(function () {
  // use closure to avoid global variables (otherwise memory leak in browser)

  var ws = null;
  var timer;
  var detectionsArray = []; // will contain all the detections
  var det_deletion_time = 12;

  function Detection(targ_id, sensor_id, lat, lon, update_time, height, track) {
    this.targ_id = targ_id;
    this.sensor_id = sensor_id;
    this.lat = lat;
    this.lon = lon;
    this.update_time = update_time;
    this.height = height;
    this.track = track;
  }

  function checkUpdate(data) {
    // will check and update the array
    var res = JSON.parse(data);
    changes = res.args[0];

    //{"targ_id": 6565495455, "sensor_id": 551, "team": "blue", "pd": 0.8, "plot": 1, "track": 3, "det_time": 1565783126675, "lat": 48.0895, "lon": 12.042, "height": 12400, "vx": 0, "vy": 0, "vz": 0, "cpx": 0, "cpy": 0, "cpz": 0, "cvx": 0, "cvy": 0, "cvz": 0}}]}

    var targ_id = parseInt(changes.data.targ_id);
    var sensor_id = parseInt(changes.data.sensor_id);
    var track = parseInt(changes.data.track);
    var lat = parseFloat(changes.data.lat);
    var lon = parseFloat(changes.data.lon);
    var height = parseFloat(changes.data.height);
    var update_time = changes.data.det_time;

    var det_date = new Date();
    var curr_time = det_date.getTime();

    index = -1;
    for (var i = 0; i < detectionsArray.length; i++) {
      if (
        detectionsArray[i].targ_id == targ_id &&
        detectionsArray[i].sensor_id == sensor_id
      ) {
        index = i;
        break;
      }
    }

    if (index == -1) {
      var detection = new Detection(
        targ_id,
        sensor_id,
        lat,
        lon,
        update_time,
        height,
        track
      );
      detectionsArray.push(detection);
    } else {
      detectionsArray[index].lat = lat;
      detectionsArray[index].lon = lon;
      detectionsArray[index].update_time = update_time;
      detectionsArray[index].height = height;
      detectionsArray[index].track = track;
    }
    ///////  PERIODICALLY SEND ALL DATA TO THE MAIN THREAD //////////

    var det_json = {};
    det_json["request_type"] = "db_update";
    det_json["data"] = detectionsArray;
    det_json["table"] = "blue_live_detection";
    det_json["node"] = "gbad";
    det_json["action"] = "UPDATE";

    self.postMessage(JSON.stringify(det_json));
    last_det_time = curr_time;

    // ------------------------------also remove dead replay targets
    for (var i = 0; i < detectionsArray.length; i++) {
      if (
        update_time - detectionsArray[i].update_time >
        det_deletion_time * 1000
      ) {
        detectionsArray.splice(i, 1);
      }
    }

    //}
  }

  function startWsServer() {
    ws = new WebSocket(ws_addr);
    ws.onmessage = function (
      evt // receive messages from the python server
    ) {
      var ret_msg = JSON.parse(evt.data);
      if (ret_msg[0] < 0) {
        // this means the sim is over
        clearInterval(timer);
        self.postMessage([-999]);
      } else {
        checkUpdate(evt.data);
      }
    };

    ws.onopen = function (event) {
      console.log("-------DETECTION SIM WebSocket opened");
      runSim = true;
    };
    ws.onclose = function (evt) {
      console.log("-------DETECTION SIM WebSocket closed");
    };
  }

  //-------------------------------------------------------------------------------------------------------------------------------

  self.addEventListener(
    "message",
    function (e) {
      // receive messages from the main thread
      anz_x = e.data[0];

      // this is to update ws server address and port
      if (anz_x == 8993493) {
        ws_addr = e.data[1];
        startWsServer();
      }
      var timeout_if_ws_closed_ms = 0;
      if (ws.readyState == ws.CLOSED) {
        console.log(
          "----- websocket to DETECTION SIM server is closed, attempting to reopen..."
        );
        startWsServer();
        timeout_if_ws_closed_ms = 1000;
      }

      var request_type = e.data[0];

      setTimeout(function () {
        // will wait for time specified by 'timeout_if_ws_closed_ms', until executing code below
        // if websocket was closed, the 'timeout_if_ws_closed_ms' is set
        // to a higher value, in order to give the websocket time to be reopened
        if (ws.readyState != ws.OPEN) {
          console.log(
            "----- did not manage to open websocket to detection_simserver within the timeout"
          );
        } else {
          // websocket is open
          var query = e.data[1];
          if (query != null) {
            ws.send(query); // send the message to the Python server
          }
        }
      }, timeout_if_ws_closed_ms);
    },
    false
  );
})(); // closure
