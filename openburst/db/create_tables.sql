CREATE TABLE blue_live.waypoint
(
  id_nr integer NOT NULL,
  team character varying(15),
  name character varying(15) NOT NULL,
  agl_asl integer,
  waypoints double precision[],
  CONSTRAINT waypoint_pkey PRIMARY KEY (id_nr, name)
);
ALTER TABLE blue_live.waypoint
  OWNER TO CURRENT_USER;


CREATE TABLE blue_live.detection
(
  targ_id bigint NOT NULL,
  sensor_id integer NOT NULL,
  team character varying(15),
  pd double precision,
  plot double precision,
  track double precision,
  det_time double precision,
  lat double precision,
  lon double precision,
  height double precision,
  vx double precision,
  vy double precision,
  vz double precision,
  cpx double precision,
  cpy double precision,
  cpz double precision,
  cvx double precision,
  cvy double precision,
  cvz double precision,
  recording_time double precision,
  CONSTRAINT my_table_pkey PRIMARY KEY (targ_id, sensor_id)
);
ALTER TABLE blue_live.detection
  OWNER TO CURRENT_USER;


CREATE TABLE blue_live.rad
(
  id_nr integer NOT NULL,
  name character varying(15) NOT NULL,
  status integer,
  lat double precision,
  lon double precision,
  power integer,
  antenna_diam double precision,
  freq double precision,
  pulse_width double precision,
  cpi_pulses integer,
  bandwidth double precision,
  pfa double precision,
  rotation_time integer,
  category character varying(15),
  min_elevation integer,
  max_elevation integer,
  orientation double precision,
  horiz_aperture integer,
  min_detection_range double precision,
  max_detection_range double precision,
  min_detection_height integer,
  max_detection_height integer,
  min_detection_tgt_speed double precision,
  max_detection_tgt_speed double precision,
  update_time double precision,
  team character varying(15),
  CONSTRAINT rad_pkey PRIMARY KEY (id_nr, name)
);
ALTER TABLE blue_live.rad
  OWNER TO CURRENT_USER;


CREATE TABLE blue_live.target
(
  id_nr bigint NOT NULL,
  team character varying(15),
  rcs double precision,
  name character varying(15) NOT NULL,
  running integer,
  velocity double precision,
  lat double precision,
  lon double precision,
  height integer,
  vx double precision,
  vy double precision,
  vz double precision,
  corridor_breadth double precision,
  noftargets integer,
  typed character varying(15),
  threed_waypoints_id integer,
  status integer,
  maneuvring integer,
  classification character varying(15),
  waypoints double precision[],
  waypoints_index integer,
  update_time double precision,
  terrainheight integer,
  recording_time double precision,
  CONSTRAINT target_pkey PRIMARY KEY (id_nr, name)
);
ALTER TABLE blue_live.target
  OWNER TO CURRENT_USER;



CREATE TABLE blue_live.targettrigger
(
  id_nr integer NOT NULL,
  name character varying(15) NOT NULL,
  team character varying(15),
  source_target_id integer,
  dest_target_id integer,
  dist_to_poi double precision,
  poi_id_nr integer,
  CONSTRAINT targettrigger_pkey PRIMARY KEY (id_nr, name)
);
ALTER TABLE blue_live.targettrigger
  OWNER TO CURRENT_USER;


CREATE TABLE blue_live.poi
(
  id_nr integer NOT NULL,
  name character varying(15) NOT NULL,
  team character varying(15),
  lat double precision,
  lon double precision,
  CONSTRAINT poi_pkey PRIMARY KEY (id_nr, name)
);
ALTER TABLE blue_live.poi
  OWNER TO CURRENT_USER;


CREATE TABLE admin.servers(name varchar(15), ip varchar(15), port integer, status varchar(15), info varchar(20));


CREATE TABLE blue_live.pcl_rx
(
  rx_id integer NOT NULL,
  name character varying(50) NOT NULL,
  team character varying(15),
  lat double precision,
  lon double precision,
  status  integer,
  masl integer,
  ahmagl integer,
  signal_type character varying(50),
  bandwidth double precision,
  horiz_diagr_att character varying(300),
  vert_diagr_att character varying(300),
  gain double precision,
  losses double precision,
  temp_sys double precision,
  limit_distance integer,
  update_time double precision,
  txcallsigns character varying(8000),
  CONSTRAINT pcl_rx_pkey PRIMARY KEY (name)
);
ALTER TABLE blue_live.pcl_rx
  OWNER TO CURRENT_USER;


CREATE TABLE blue_live.pcl_tx
(
  tx_id integer NOT NULL,
  callsign character varying(50) NOT NULL,
  sitename character varying(100),   
  team character varying(50),
  lat double precision,
  lon double precision,
  status  integer,
  masl integer,
  ahmagl integer,
  signal_type character varying(50),
  freq double precision,
  erp_h double precision,
  erp_v double precision,
  bandwidth double precision,
  horiz_diagr_att character varying(10000),
  vert_diagr_att  character varying(10000),
  pol character varying(5),
      	    
  CONSTRAINT pcl_tx_pkey PRIMARY KEY (callsign)
);
ALTER TABLE blue_live.pcl_tx
  OWNER TO CURRENT_USER;


CREATE TABLE blue_live.pcl_detection
(
  rx_id integer NOT NULL,
  tx_id integer NOT NULL,
  pcl_rx_name character varying(50) NOT NULL,
  pcl_tx_callsign character varying(50) NOT NULL,	
  targ_id bigint NOT NULL,
  det_time double precision,
  range double precision,
  doppler double precision,
  tgt_lat double precision,
  tgt_lon double precision,
  tgt_height double precision,
  recording_time double precision,
  vx double precision,
  vy double precision,
  vz double precision,
  velocity double precision,
  bistatic_velocity double precision,
  snr double precision,
  target_time double precision,
  CONSTRAINT pcl_detection_pkey PRIMARY KEY (pcl_rx_name, pcl_tx_callsign, targ_id)
);
ALTER TABLE blue_live.pcl_detection
  OWNER TO CURRENT_USER;
