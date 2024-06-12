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
  CONSTRAINT pcl_detection_pkey PRIMARY KEY (pcl_rx_name, pcl_tx_callsign, targ_id)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE blue_live.pcl_detection
  OWNER TO red3;
