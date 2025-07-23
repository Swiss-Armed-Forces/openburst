-- using postgres 9.4 (version is important especially for the json commands used below)
-- http://coussej.github.io/2015/09/15/Listening-to-generic-JSON-notifications-from-PostgreSQL-in-Go/
-- https://www.postgresql.org/docs/9.4/static/functions-json.html

CREATE OR REPLACE FUNCTION notify_trigger() RETURNS trigger AS $$
	DECLARE
		data1 json;
		notification json;
		channel_name varchar;
		
				
	BEGIN
		channel_name := TG_TABLE_SCHEMA || '_' || TG_TABLE_NAME;
		raise notice 'noticing channel: %', channel_name;
		IF TG_OP = 'INSERT' THEN
			
			data1 = row_to_json(NEW);
			--raise notice 'noticing INSERT: ';
			--raise notice 'json data1: %', data1;	
			notification = json_build_object('table', TG_TABLE_SCHEMA || '_' || TG_TABLE_NAME, 'action', TG_OP, 'data', data1);
			raise notice 'notification : %', notification ;	
         		-- Execute pg_notify(channel, notification)
			PERFORM pg_notify(channel_name, notification::text);
			RETURN NULL; 
		END IF;
		IF TG_OP = 'DELETE' THEN
		   	data1 = row_to_json(OLD);
			--raise notice 'json data1: %', data1;	
			notification = json_build_object('table', TG_TABLE_SCHEMA || '_' || TG_TABLE_NAME, 'action', TG_OP, 'data', data1);
			--raise notice 'notification : %', notification ;	
         		-- Execute pg_notify(channel, notification)
			PERFORM pg_notify(channel_name, notification::text);
        		--RETURN OLD;
			RETURN NULL; 
		END IF;
		IF TG_OP = 'UPDATE' THEN
			--PERFORM pg_notify(channel_name, '{"UPDATE": "' || NEW.id_nr || '"}');
			--RETURN NEW;
			--RETURN NULL; 
			data1 = row_to_json(NEW);
			--raise notice 'json data1: %', data1;	
			notification = json_build_object('table', TG_TABLE_SCHEMA || '_' || TG_TABLE_NAME, 'action', TG_OP, 'data', data1);
			--raise notice 'notification : %', notification ;	
         		-- Execute pg_notify(channel, notification)
			PERFORM pg_notify(channel_name, notification::text);
			RETURN NULL; 
		END IF;
	END;
	$$ LANGUAGE plpgsql;

----TRIGGER FOR table: blue_live.rad
DROP TRIGGER IF EXISTS blue_live_rad_trigger on blue_live.rad;
CREATE TRIGGER blue_live_rad_trigger AFTER INSERT OR UPDATE OR DELETE ON blue_live.rad FOR EACH ROW EXECUTE PROCEDURE notify_trigger();

----TRIGGER FOR table: blue_live.pcl_rx
DROP TRIGGER IF EXISTS blue_live_pcl_rx_trigger on blue_live.pcl_rx;
CREATE TRIGGER blue_live_pcl_rx_trigger AFTER INSERT OR UPDATE OR DELETE ON blue_live.pcl_rx FOR EACH ROW EXECUTE PROCEDURE notify_trigger();

----TRIGGER FOR table: blue_live.pcl_tx
DROP TRIGGER IF EXISTS blue_live_pcl_tx_trigger on blue_live.pcl_tx;
CREATE TRIGGER blue_live_pcl_tx_trigger AFTER INSERT OR UPDATE OR DELETE ON blue_live.pcl_tx FOR EACH ROW EXECUTE PROCEDURE notify_trigger();


----TRIGGER FOR table: blue_live.target
DROP TRIGGER IF EXISTS blue_live_target_trigger on blue_live.target;
CREATE TRIGGER blue_live_target_trigger AFTER INSERT OR UPDATE OR DELETE ON blue_live.target FOR EACH ROW EXECUTE PROCEDURE notify_trigger();

----TRIGGER FOR table: blue_live.detection
DROP TRIGGER IF EXISTS blue_live_detection_trigger on blue_live.detection;
CREATE TRIGGER blue_live_detection_trigger AFTER INSERT OR UPDATE OR DELETE ON blue_live.detection FOR EACH ROW EXECUTE PROCEDURE notify_trigger();

----TRIGGER FOR table: blue_live.pcl_detection
DROP TRIGGER IF EXISTS blue_live_pcl_detection_trigger on blue_live.pcl_detection;
CREATE TRIGGER blue_live_pcl_detection_trigger AFTER INSERT OR UPDATE OR DELETE ON blue_live.pcl_detection FOR EACH ROW EXECUTE PROCEDURE notify_trigger();

