//(function() { // use closure to avoid global variables (otherwise memory leak in browser)

//------------ OBJECT IDS for communication with the replay server
var REPLAY_START_SEND_TEST_DATA_FLOW = 5467;
var REPLAY_STOP_SEND_TEST_DATA_FLOW = 5468;
var TEST_REPLAY_REPORT = 5469;
var REF_REPLAY_REPORT = 5470;
var REF_REPLAY_REPORT_DATETIME = 5471;
var REPLAY_PAUSE_SEND_TEST_DATA_FLOW = 5472;
var REF_REPLAY_STATS = 5473;
var GET_REPLAY_REF_DATA = 5474;
var GET_REPLAY_TEST_DATA = 5475;
var REPLAY_EXCEPTION = 5476;

var replayRunning = false;
var paused = 0;

// get replay ref files
function getReplayRefFiles(replay_worker) {
  // send request
  var request = new request_wrapper();
  request.request_type = "GET_REPLAY_REF_DATA";
  request.nbr_args = 0;
  request.args = [];
  var query = JSON.stringify(request);
  console.log("sending to replay worker: ", query);
  replay_worker.postMessage([request.request_type, query]);
}

// get replay test files
function getReplayTestFiles(replay_worker) {
  // send request
  var request = new request_wrapper();
  request.request_type = "GET_REPLAY_TEST_DATA";
  request.nbr_args = 0;
  request.args = [];
  var query = JSON.stringify(request);
  console.log("sending to replay worker: ", query);
  replay_worker.postMessage([request.request_type, query]);
}

// start replay

function startReplay(
  ref_file_name,
  test_file_name,
  sampling_time,
  update_rate,
  test_track_del_time,
  ref_track_deletion_time,
  replay_worker,
  tgt_rcs
) {
  if (!replayRunning) {
    replayRunning = true;
    paused = 0;

    // send request
    var request = new request_wrapper();
    request.request_type = "REPLAY_START_SEND_TEST_DATA_FLOW";
    request.nbr_args = 7;
    request.args = [
      JSON.stringify(ref_file_name),
      JSON.stringify(test_file_name),
      JSON.stringify(sampling_time),
      JSON.stringify(update_rate),
      JSON.stringify(test_track_del_time),
      JSON.stringify(ref_track_deletion_time),
      JSON.stringify(tgt_rcs),
    ];

    var query = JSON.stringify(request);
    console.log("sending to replay worker: ", query);
    replay_worker.postMessage([request.request_type, query]);

    document.getElementById("start_replay").value = "Play/Pause";
    document.getElementById("stop_replay").disabled = false;
  } else {
    if (paused == 0) {
      paused = 1;

      // send request
      var request = new request_wrapper();
      request.request_type = "REPLAY_PAUSE_SEND_TEST_DATA_FLOW";
      request.nbr_args = 0;
      request.args = [];
      var query = JSON.stringify(request);
      console.log("sending to replay worker: ", query);
      replay_worker.postMessage([request.request_type, query]);
    } else {
      paused = 1;
      // send request
      var request = new request_wrapper();
      request.request_type = "REPLAY_PAUSE_SEND_TEST_DATA_FLOW";
      request.nbr_args = 0;
      request.args = [];
      var query = JSON.stringify(request);
      console.log("sending to replay worker: ", query);
      replay_worker.postMessage([request.request_type, query]);
    }
  }
}

// stop the simulation of a target
function stopReplay(replay_worker) {
  replayRunning = false;

  // send request
  var request = new request_wrapper();
  request.request_type = "REPLAY_STOP_SEND_TEST_DATA_FLOW";
  request.nbr_args = 0;
  request.args = [];
  var query = JSON.stringify(request);
  console.log("sending to replay worker: ", query);
  replay_worker.postMessage([request.request_type, query]);

  document.getElementById("start_replay").disabled = false;
  document.getElementById("start_replay").value = "Play";
}
