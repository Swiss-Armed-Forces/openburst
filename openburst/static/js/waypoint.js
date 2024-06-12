function ThreeD_Waypoints(object_ID, id, name, poi_name, agl_asl) {
  // object_id = THREE_D_WAYPOINTS_PARAM_ID
  this.object_id = object_ID;
  this.id = id;
  this.name = name;
  this.poi_name = poi_name;
  this.agl_asl = agl_asl;
  this.targetLocationArray = [];
  this.mapLayersArray = [];
  this.shown = true;
}

// to store a tracking positon
function TrackPosition(type) {
  this.lat = -1;
  this.lon = -1;
  this.pd = 0.0;
  this.terrainHeight = 0.0;

  this.delta_x_kms = 0.0; // this should be updated if the center is moved
  this.delta_y_kms = 0.0; // this should be updated id the center is moved
  this.z = 0.0; //flight_mesh.position.z;

  this.line = null; // this is the track line connected to the previous track pos
}

function Waypoint() {
  this.three_d_waypoints_array = []; // this will contain an array of ThreeD_Waypoints

  function getWaypointFromID(id) {
    var wayp = null;
    for (var i = 0, l = three_d_waypoints_array.length; i < l; i++) {
      if (three_d_waypoints_array[i].id == id) {
        return three_d_waypoints_array[i];
      }
    }

    return wayp;
  }

  function getAll3DWaypointsMessage() {
    var msg_json = JSON.stringify(three_d_waypoints_array, [
      "object_id",
      "id",
      "name",
      "poi_name",
      "agl_asl",
      "target_location_array",
      "lat",
      "lon",
      "terrainHeight",
      "flightHeight",
      "agl_asl",
    ]);
    return msg_json;
  }

  function updateWaypointsArrayFromTable() {
    console.log("updating waypoints");
    for (
      var i = 2, l = document.getElementById("3d_waypoints_table").rows.length;
      i < l;
      i++
    ) {
      var data = document.getElementById("3d_waypoints_table").rows[i].cells;
      var curr_id = parseInt(data[0].innerHTML);
      for (var j = 0, ll = three_d_waypoints_array.length; j < ll; j++) {
        if (parseInt(three_d_waypoints_array[j].id) == curr_id) {
          three_d_waypoints_array[j].name = String(data[1].innerHTML);
          three_d_waypoints_array[j].agl_asl = parseInt(data[2].innerHTML);
          three_d_waypoints_array[j].poi_name = String(data[3].innerHTML);
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

  function updateWayPoints(
    wayp_id,
    wayp_name,
    poi_name,
    agl_asl,
    targLocArray
  ) {
    console.log(
      "updating waypoint: ",
      wayp_id,
      wayp_name,
      ", with loc array: ",
      targLocArray
    );
    console.log(
      "three_d_waypoints_array.length = ",
      three_d_waypoints_array.length
    );
    for (var i = 0, l = three_d_waypoints_array.length; i < l; i++) {
      console.log(
        "three_d_waypoints_array[i].id, wayp_id = ",
        three_d_waypoints_array[i].id,
        wayp_id
      );
      if (parseInt(three_d_waypoints_array[i].id) == wayp_id) {
        console.log("got in");
        three_d_waypoints_array[i].targetLocationArray = targLocArray;
        three_d_waypoints_array[i].name = wayp_name;
        three_d_waypoints_array[i].poi_name = poi_name;
        three_d_waypoints_array[i].agl_asl = agl_asl;

        // first remove all elements in the mapLayersArray
        for (
          var u = 0, ll = three_d_waypoints_array[i].mapLayersArray.length;
          u < ll;
          u++
        ) {
          map.removeLayer(three_d_waypoints_array[i].mapLayersArray[u]);
        }

        // then remove the mapLayersArray element itself
        three_d_waypoints_array[i].mapLayersArray = [];

        // now draw the new waypoints on the map
        drawWayPoints(wayp_id);

        // toggle view twice to also show the terrain heig chartshow the waypoints if they were shown before, and otherwise not
        if (three_d_waypoints_array[i].shown) {
          toggleWaypointsView(wayp_id); // will make the currently shown invisible
          toggleWaypointsView(wayp_id); // this will load the layers from the targetLocationArray as the layers were set to null when data downloaded from server
        } else {
          toggleWaypointsView(wayp_id);
        }

        console.log(
          "updated waypoint with downloaded data: ",
          three_d_waypoints_array[i]
        );
      }
    }
  }
} // closure
