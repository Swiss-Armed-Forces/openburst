var ws = null;

function startWsServer() {
  ws = new WebSocket(ws_addr);
  ws.onmessage = function (evt) {
    var ret_msg = evt.data;
    self.postMessage(ret_msg);
  };

  ws.onopen = function (event) {
    console.log("-------PCL WebSocket opened");
  };
  ws.onclose = function (evt) {
    console.log("-------PCL WebSocket closed");
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

// receive input from main javascript thread
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
        "----- websocket to PCL server is closed, attempting to reopen..."
      );
      startWsServer();
      timeout_if_ws_closed_ms = 3000;
    }

    var request_type = e.data[0];

    setTimeout(function () {
      // will wait for time specified by 'timeout_if_ws_closed_ms', until executing code below
      // if websocket was closed, the 'timeout_if_ws_closed_ms' is set to a higher value,
      // in order to give the websocket time to be reopened
      if (ws.readyState != ws.OPEN) {
        console.log(
          "----- did not manage to open websocket to PCL within the timeout"
        );
      } else {
        // websocket is open
        console.log("----PCL worker got request:", request_type);

        // Passive Rad Server
        request_type = e.data[0];
        if (request_type == "findTxForRx_all") {
          var query = e.data[1];
          console.log("----Sending following request to wsPRServer: " + query);
          ws.send(query);
        } else if (request_type == "calcMinDetRCScoverage") {
          var query = e.data[1];
          console.log("----Sending following request to wsPRServer: " + query);
          ws.send(query);
        } else if (request_type == "calcDetRoute") {
          var query = e.data[1];
          console.log("----Sending following request to wsPRServer: " + query);
          ws.send(query);
        } else if (request_type == "calcCoverageCorridor") {
          var query = e.data[1];
          console.log("----Sending following request to wsPRServer: " + query);
          ws.send(query);
        } else if (request_type == "findOptRxPos") {
          var query = e.data[1];
          console.log("----Sending following request to wsPRServer: " + query);
          ws.send(query);
        }
      }
    }, timeout_if_ws_closed_ms);
  },
  false
);
