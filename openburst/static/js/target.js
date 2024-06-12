(function () {
  // use closure to avoid global variables to avoid memory leak in browser

  function TargetLocation(
    object_id,
    id,
    lat,
    lon,
    terrainHeight,
    flightHeight
  ) {
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
    maneuvring,
    terrainHeight = -1
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
    this.terrainHeight = terrainHeight;
  }
  var targetArray = []; // this will contain all the targets

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
  var curTriggerID = 0;

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

  // returns rcs of a target from array
  function getTargetRCS(targetID) {
    for (var j = 0, ll = targetArray.length; j < ll; j++) {
      if (parseInt(targetArray[j].id) == targetID) {
        if (targetArray[j].rcs > 0) {
          return targetArray[j].rcs;
        } else {
          return -1;
        }
      }
    }
    return -1;
  }

  // sets rcs of target in array
  function setTargetRCS(targetID, rcs) {
    for (var j = 0, ll = targetArray.length; j < ll; j++) {
      if (parseInt(targetArray[j].id) == targetID) {
        targetArray[j].rcs = rcs;
      }
    }
  }
})(); // closure
