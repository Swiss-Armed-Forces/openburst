"""

    multiple clients sending data to a single multithreaded server (i.e. all clients send data to the same IP and the same port, and the server starts a new thread for each connected client)
    adapted from: 
    https://medium.com/@denizhalil/advanced-socket-programming-with-python-multi-client-and-server-communication-c0416836c3bd


    8 Commands:
    (only one RX/TX/PLOT per sent command) 

    1) RESET
    2) RX id,lat,lon,alt[masl]  
    3) TX id,lat,lon,alt[masl]  
    4) SENSOR id,rx_id,tx_id, bist_range_std_dev[m], bist_vel_std_dev[m/s]
    5) ROI lat_south,lat_north,lon_west,lon_east
    6) BIST_WND max_bist_range[m],max_bistatic_vel[m/s]
    7) PLOT timestamp[ms_after_afternight],bistatic_range[m](with substracted baseline),bistatic_velocity[m/s]
    8) QUIT

    typical FM Sensors std devs for bist_range and bist_vel: 350[m],1.87[m/s]


"""
    
from __future__ import division
import socket
import threading
from openburst.constants import openburst_config

#########################################

def handle_client(conn, addr):
    print(f"Connection established with {addr}.")
    while True:
        try:
            data = conn.recv(1024)  # Receive data from the client
            if not data:
                break  # Terminate the connection if no data is received
            print(f"Received from {addr}: {data.decode()}")
            #conn.sendall(f"Server response: {data.decode()}".encode())  # Send the received data back to the client
        except ConnectionResetError:
            print(f"Client {addr} has disconnected.")
            break
    conn.close()
    print(f"Connection with {addr} closed.")# Start the server

###########################################

def start_server():
    """
    starts a server to listen for client data; opens a separate thread for each connected client
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((openburst_config.LIVE_PCL_DETECTION_SERVER_IP, openburst_config.LIVE_PCL_DETECTION_SERVER_PORT))
        server_socket.listen()
        print(f"Server listening on {openburst_config.LIVE_PCL_DETECTION_SERVER_IP}:{openburst_config.LIVE_PCL_DETECTION_SERVER_PORT}...")
        
        while True:
            conn, addr = server_socket.accept()  # Accept a client connection
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()  # Start a new thread for each client
            print(f"Active connections: {threading.activeCount() - 1}")

##############################################


def get_client_socket():
    """
    returns a client socket
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(2.0)
    return client_socket

def send_client_data(client_socket, message):
    """
    sends message through the client
    """
    client_socket.sendto(message.encode("utf-8"), (openburst_config.LIVE_PCL_DETECTION_SERVER_IP, openburst_config.LIVE_PCL_DETECTION_SERVER_PORT))


def send_reset_client_data(client_socket, message):
    """
    sends reset message to the cartesian tracker
    """
    client_socket.sendto(message.encode("utf-8"), (openburst_config.LIVE_PCL_BISTATIC_TRACK_SERVER_IP, openburst_config.LIVE_PCL_BISTATIC_TRACK_SERVER_PORT))
          

def send_client_bistatic_track_data(client_socket, message):
    client_socket.sendto(message.encode("utf-8"), (openburst_config.LIVE_PCL_BISTATIC_TRACK_SERVER_IP, openburst_config.LIVE_PCL_BISTATIC_TRACK_SERVER_PORT))
     

###############################################
