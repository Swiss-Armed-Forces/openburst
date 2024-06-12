"""
module for enabling non-persistentread/write access to the postgreSQL DB. 
All listeners of DB changes subscribed here.

Also provides listen and notify function for other processes interested in
changes to openburst DB tables (observer pattern). 

"""
import logging
import logging.config
import select
import json
import psycopg2
import psycopg2.extensions
from psycopg2.extensions import AsIs
from openburst.constants import openburst_config
from openburst.types import requestwrapper


def connect_to_db():
    """! connects to the DB and returns the connection"""
    conn = None
    try:
        logger = logging.getLogger(__name__)
        logger.info(
            "starting temporary connection to DB: %s, %s, %s, %s ",
            openburst_config.BURST_DB_NAME,
            openburst_config.BURST_DB_SERVER_USERNAME,
            openburst_config.BURST_DB_SERVER_IP,
            openburst_config.BURST_DB_SERVER_PASSWORD,
        )
        conn = psycopg2.connect(
            "dbname=%s user=%s host=%s password=%s"
            % (
                openburst_config.BURST_DB_NAME,
                openburst_config.BURST_DB_SERVER_USERNAME,
                openburst_config.BURST_DB_SERVER_IP,
                openburst_config.BURST_DB_SERVER_PASSWORD,
            )
        )
    except psycopg2.Error as e:
        logger = logging.getLogger(__name__)
        logger.error("...unable to connect to the psql DB", exc_info=True)
        logger.error(e)
    return conn


def write_server_start_to_db(servername, ip, port):
    """! given the name of the server (e.g. "DEM"), the DB is updated with the given ip"""
    logger = logging.getLogger(__name__)
    logger.info("updating DB with server start: %s, %s, %s", servername, ip, port)
    conn = connect_to_db()
    cur = conn.cursor()
    cur.execute(
        """UPDATE admin.servers SET ip = (%s) WHERE name = (%s);""", (ip, servername)
    )
    conn.commit()
    cur.execute(
        """UPDATE admin.servers SET port = (%s) WHERE name = (%s);""",
        (port, servername),
    )
    conn.commit()
    cur.close()
    conn.close()



def remove_team_from_table(team, table):
    """! remove all rows of the given table for the given team"""
    conn = connect_to_db()
    with conn.cursor() as cur:
        logger = logging.getLogger(__name__)
        logger.info("removing all rows for %s", table)
        table_name = "blue_live." + table
        if team == "blue":
            table_name = "blue_live." + table
        elif team == "red":
            table_name = "red_live." + table 
        with conn.cursor() as cur:
            cur.execute("""DELETE FROM %s;""", (AsIs(table_name),))

        cur.close()
    conn.close()

def remove_pcl_detections():
    """ removes pcl detections"""
    conn = connect_to_db()
    with conn.cursor() as cur:
        cur.execute("""DELETE FROM %s;""", (AsIs("blue_live.detection"),))
        cur.close()
    conn.close()

def read_server_ip_port_from_db(servername):
    """! given the name of the server (e.g. "DEM"), the DB is updated with the given ip and port is returned"""
    logger = logging.getLogger(__name__)
    logger.info("reading DB for ip and port for server: %s ", servername)
    conn = connect_to_db()
    cur = conn.cursor()
    try:
        cur.execute("""SELECT * from admin.servers WHERE name = (%s);""", (servername,))
        conn.commit()
    except psycopg2.Error as e:
        logger.error(
            "read_server_ip_port_from_db: unable SELECT from admin.servers. For given servername: %s, with error: %s",
            servername, e
        )

    rows = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    row = rows[0]
    return [row[1], row[2]]  # returns ip and port of the server



def listen_and_notify(queue, table, event_name, event=None):
    """! listens for changes on a DB table notifies when changes happen. 
    see: http://initd.org/psycopg/docs/advanced.html """
    conn = connect_to_db()
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

    curs = conn.cursor()
    # listen on the given table
    listen_query = "LISTEN " + table + ";"
    curs.execute(listen_query)
    conn.commit()
    logger = logging.getLogger(__name__)
    logger.info("Waiting for notifications on channel: %s", table)

    while not event.is_set():
        if select.select([conn],[],[],1) == ([],[],[]):
            pass
        else:
            conn.poll()
            while conn.notifies:
                notify = conn.notifies.pop(0)
                json_notice = json.loads(notify.payload)
                snd_msg = json_notice
                nbr_args = 1
                args=[snd_msg]
                response = requestwrapper.RequestWrapper(event_name, nbr_args, args)
                response_json = json.dumps(response.__dict__)
                queue.put(response_json)
                
                
    # while ended because the event was set (by the calling process)
    logger.info("notification stopped for: %s", table)
    conn.commit()
    curs.close()
    conn.close()