(function () {
  // use closure to avoid global variables (otherwise memory leak in browser)

  var ws = null;
  var ws_addr = null;

  var anz_x = 40; // this has to be copied into pdf_Worker.js (as workers do not see this)

  var SENSOR_UPLOAD_ID = 9245;

  function startWsServer() {
    ws = new WebSocket(ws_addr);
    ws.onmessage = function (evt) {
      var ret_msg = evt.data;
      self.postMessage(ret_msg);
    };

    ws.onopen = function (event) {
      console.log("-------DEM WebSocket opened");
    };
    ws.onclose = function (evt) {
      console.log("-------DEM WebSocket closed");
    };
  }

  function toDecimal(deg, min, sec) {
    return deg + min / 60 + sec / 3600;
  }

  function toDeg(dec) {
    deg_min_sec = [];
    deg_min_sec[0] = Math.floor(dec);
    var po = dec % 1;
    deg_min_sec[1] = Math.floor(po * 60.0);
    deg_min_sec[2] = (po * 60.0 - deg_min_sec[1]) * 60.0;

    return deg_min_sec;
  }

  self.addEventListener(
    "message",
    function (e) {
      // data coming in:
      anz_x = e.data[0];

      // this is to update ws server address and port
      if (anz_x == 8993493) {
        ws_addr = e.data[1];
        startWsServer();
      }

      var timeout_if_ws_closed_ms = 0;
      if (ws.readyState == ws.CLOSED) {
        console.log(
          "----- websocket to DEM server is closed, attempting to reopen..."
        );
        startWsServer();
        timeout_if_ws_closed_ms = 1000;
      }
      setTimeout(function () {
        // will wait for time specified by 'timeout_if_ws_closed_ms', until executing code below
        // if websocket was closed, the 'timeout_if_ws_closed_ms' is set to a higher value,
        // in order to give the websocket time to be reopened
        if (ws.readyState != ws.OPEN) {
          console.log(
            "----- did not manage to open websocket to DEM within the timeout"
          );
        } else {
          // websocket is open
          var msg = "";

          // ----------------------------------receive message from main thread, parse it, send the query to the websocket server--

          // data coming in:
          anz_x = e.data[0];

          // this is to upload sensor
          if (anz_x == SENSOR_UPLOAD_ID) {
            msg = SENSOR_UPLOAD_ID + "," + e.data[1];
          }

          // this is radar coverage computation request
          if (anz_x == 559765) {
            var rad_id = e.data[1];
            var rad_lat = e.data[2];
            var rad_lon = e.data[3];
            var flight_height = e.data[4];
            var pow = e.data[5];
            var antenna_diam = e.data[6];
            var freq = e.data[7];
            var pulse_width = e.data[8];
            var cpi_pulses = e.data[9];
            var bandwidth = e.data[10];
            var pfa = e.data[11];
            var rcs = e.data[12];
            var min_elev_deg = e.data[13];
            var max_elev_deg = e.data[14];
            var radio_prop_en = e.data[15];
            var magl_en = e.data[16];

            msg =
              559765 +
              "," +
              rad_id +
              "," +
              rad_lat +
              "," +
              rad_lon +
              "," +
              flight_height +
              "," +
              pow +
              "," +
              antenna_diam +
              "," +
              freq +
              "," +
              pulse_width +
              "," +
              cpi_pulses +
              "," +
              bandwidth +
              "," +
              pfa +
              "," +
              rcs +
              "," +
              min_elev_deg +
              "," +
              max_elev_deg +
              "," +
              radio_prop_en +
              "," +
              magl_en;
          } else if (anz_x == 2340902) {
            // this is adding a new sensor
            curr_lat = e.data[1];
            curr_lon = e.data[2];
            curr_id = e.data[3];
            msg = 2340902 + "," + curr_lat + "," + curr_lon + "," + curr_id;
          } else if (anz_x == 5340905) {
            // this is adding a new gbad effector
            curr_lat = e.data[1];
            curr_lon = e.data[2];
            curr_id = e.data[3];
            msg = 5340905 + "," + curr_lat + "," + curr_lon + "," + curr_id;
          } else if (anz_x == 5340906) {
            // this is adding POI
            var urr_lat = e.data[1];
            var curr_lon = e.data[2];
            var curr_id = e.data[3];
            msg = 5340906 + "," + curr_lat + "," + curr_lon + "," + curr_id;
          } else if (anz_x == 6200901) {
            // this is t0 convert (lat, lon) to pixels
            var curr_lat = e.data[1];
            var curr_lon = e.data[2];
            var poi_lat = e.data[3];
            var poi_lon = e.data[4];
            msg =
              6200901 +
              "," +
              curr_lat +
              "," +
              curr_lon +
              "," +
              poi_lat +
              "," +
              poi_lon;
          } else if (anz_x == 6200902) {
            // for PET
            var curr_lat = e.data[1];
            var curr_lon = e.data[2];
            var poi_lat = e.data[3];
            var poi_lon = e.data[4];
            msg =
              6200902 +
              "," +
              curr_lat +
              "," +
              curr_lon +
              "," +
              poi_lat +
              "," +
              poi_lon;
          } else if (anz_x == 6200903) {
            // for PCL
            var curr_lat = e.data[1];
            var curr_lon = e.data[2];
            var poi_lat = e.data[3];
            var poi_lon = e.data[4];
            msg =
              6200903 +
              "," +
              curr_lat +
              "," +
              curr_lon +
              "," +
              poi_lat +
              "," +
              poi_lon;
          } else if (anz_x == 29824733) {
            // this is propagation model request
            msg = e.data;
          } else if (anz_x == 3456178) {
            // this is terrain matrix request
            msg = e.data;
          }
          ws.send(msg);
        }
      }, timeout_if_ws_closed_ms);
    },
    false
  );
})(); // closure
