"""
Module for starting, stoppping and viewing logs of openburst web client and servers

"""


from subprocess import Popen
import tkinter
from tkinter import ttk
from tkinter import font
import os
import psutil
import signal

from openburst.functions import dbfunctions
from openburst.functions import basefunctions
from openburst.constants import openburst_config
basefunctions.set_openburst_system_path()
basefunctions.set_openburst_linked_lib_path()


server_ents = []

def popupmsg(msg):
    """
    Shows a pop up message to the user
    """
    popup = tkinter.Tk()
    [mx, my] = popup.winfo_pointerxy()
    postr = "500x300+" + str(mx - 100) + "+" + str(my - 100)
    popup.geometry(postr)  #'250x150+0+0'
    popup.wm_title("Error")
    helv36 = font.Font(family="Helvetica", size=12, weight="bold")
    label = ttk.Label(popup, text=msg, font=helv36)
    label.pack(side="top", fill="x", pady=100)
    B1 = ttk.Button(popup, text="Ok", command=popup.destroy)
    B1.pack()
    popup.wm_attributes("-topmost", 1)
    popup.focus_force()
    popup.overrideredirect(True)
    # popup.after(5000, lambda: popup.destroy() ) # Destroy the widget after 3 seconds
    popup.mainloop()


def startServer(server_name):

    # 'radterrain', 'webserver', 'geoplot', 'detection', 'sensorcontrol', 'pcl', 'pet', 'replay',

    if server_name == "radterrain":
        for process in psutil.process_iter():
            if process.cmdline() == [openburst_config.PYTHON_VERSION, openburst_config.radterrain_server_app]:
            #if server_name in process.name():
                popupmsg("radterrain Server running. Stop it first.")
                return
        # if not, start the script
        #print("radterrain started")
        Popen([openburst_config.PYTHON_VERSION, openburst_config.radterrain_server_app], cwd=openburst_config.radterrain_dir)

    if server_name == "webserver":
        for process in psutil.process_iter():
            if process.cmdline() == [openburst_config.PYTHON_VERSION, openburst_config.web_server_app]:
                popupmsg("Webserver running. Stop it first.")
                return
        # if not, start the script
        Popen([openburst_config.PYTHON_VERSION, openburst_config.web_server_app], cwd=openburst_config.web_dir)

    if server_name == "geoplot":
        for process in psutil.process_iter():
            if process.cmdline() == [openburst_config.PYTHON_VERSION, openburst_config.geoplot_server_app]:
                popupmsg("GEOPLOT Server running. Stop it first.")
                return
        # if not, start the script
        Popen([openburst_config.PYTHON_VERSION, openburst_config.geoplot_server_app], cwd=openburst_config.geoplot_dir)

    if server_name == "detection":
        for process in psutil.process_iter():
            if process.cmdline() == [openburst_config.PYTHON_VERSION, openburst_config.detection_server_app]:
                popupmsg("DETECTION Server running. Stop it first.")
                return
        # if not, start the script
        Popen([openburst_config.PYTHON_VERSION, openburst_config.detection_server_app], cwd=openburst_config.detection_dir)

    if server_name == "sensorcontrol":
        for process in psutil.process_iter():
            if process.cmdline() == [openburst_config.PYTHON_VERSION, openburst_config.sensor_control_app]:
                popupmsg("SENSOR Control server running. Stop it first.")
                return
        # if not, start the script
        Popen([openburst_config.PYTHON_VERSION, openburst_config.sensor_control_app], cwd=openburst_config.sensor_control_dir)

    if server_name == "pcl":
        for process in psutil.process_iter():
            if process.cmdline() == [openburst_config.PYTHON_VERSION, openburst_config.pcl_server_app]:
                popupmsg("PCL Server running. Stop it first.")
                return
        # if not, start the script
        Popen([openburst_config.PYTHON_VERSION, openburst_config.pcl_server_app], cwd=openburst_config.pcl_dir)

    if server_name == "pet":
        for process in psutil.process_iter():
            if process.cmdline() == [openburst_config.PYTHON_VERSION, openburst_config.pet_server_app]:
                popupmsg("PET Server running. Stop it first.")
                return
        # if not, start the script
        Popen([openburst_config.PYTHON_VERSION, openburst_config.pet_server_app], cwd=openburst_config.pet_dir)

    if server_name == "replay":
        for process in psutil.process_iter():
            if process.cmdline() == [openburst_config.PYTHON_VERSION, openburst_config.replay_server_app]:
                popupmsg("REPLAY Server running. Stop it first.")
                return
        # if not, start the script
        Popen([openburst_config.PYTHON_VERSION, openburst_config.replay_server_app], cwd=openburst_config.replay_dir)

    checkServers()

def on_terminate(proc):
    print("process {} terminated with exit code {}".format(proc, proc.returncode))



def find_proc_by_name(app_name):
    "Return a list of processes matching 'app_name'."
    #print(" checking to find proc: ", app_name)
    
    for process in psutil.process_iter():
        if process.cmdline() == [openburst_config.PYTHON_VERSION, app_name]: 
            return process
    return None

def kill_proc_tree(pid, sig=signal.SIGTERM, include_parent=True,
                   timeout=None, on_terminate=None):
    """
    from: https://psutil.readthedocs.io/en/latest/index.html#kill-process-tree
    Kill a process tree (including grandchildren) with signal
    "sig" and return a (gone, still_alive) tuple.
    "on_terminate", if specified, is a callback function which is
    called as soon as a child terminates.
    """
    assert pid != os.getpid(), "won't kill myself"
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    if include_parent:
        children.append(parent)
    for p in children:
        try:
            p.send_signal(sig)
        except psutil.NoSuchProcess:
            pass
    gone, alive = psutil.wait_procs(children, timeout=timeout,
                                    callback=on_terminate)
    return (gone, alive)

def stopServer(server_name):
     # 'radterrain', 'webserver', 'geoplot', 'detection', 'sensorcontrol', 'pcl', 'pet', 'replay',
    #print("stopping server: ", server_name)

    if server_name == "radterrain":
        proc = find_proc_by_name(openburst_config.radterrain_server_app) 
        if proc is not None:
            kill_proc_tree(proc.pid)

    if server_name == "webserver":
        proc = find_proc_by_name(openburst_config.web_server_app) 
        if proc is not None:
            kill_proc_tree(proc.pid)

    if server_name == "geoplot":
        proc = find_proc_by_name(openburst_config.geoplot_server_app) 
        if proc is not None:
            kill_proc_tree(proc.pid)
        
    if server_name == "detection":
        proc = find_proc_by_name(openburst_config.detection_server_app) 
        if proc is not None:
            kill_proc_tree(proc.pid)

    if server_name == "sensorcontrol":
        proc = find_proc_by_name(openburst_config.sensor_control_app) 
        if proc is not None:
            kill_proc_tree(proc.pid)

    if server_name == "pcl":
        proc = find_proc_by_name(openburst_config.pcl_server_app) 
        if proc is not None:
            kill_proc_tree(proc.pid)

    if server_name == "pet":
        proc = find_proc_by_name(openburst_config.pet_server_app) 
        if proc is not None:
            kill_proc_tree(proc.pid)

    if server_name == "replay":
        proc = find_proc_by_name(openburst_config.replay_server_app) 
        if proc is not None:
            kill_proc_tree(proc.pid)

    checkServers()


def showLog(server_name):
    # 'radterrain', 'webserver', 'geoplot', 'detection', 'sensorcontrol', 'pcl', 'pet', 'replay',

    if server_name == "radterrain":
        os.system('gnome-terminal --command "multitail /tmp/burst_dem.log" &')

    if server_name == "webserver":
        os.system('gnome-terminal --command "multitail /tmp/burst_hmi.log" &')
    if server_name == "geoplot":
        os.system('gnome-terminal --command "multitail /tmp/burst_geo.log" &')
    if server_name == "detection":
        os.system('gnome-terminal --command "multitail /tmp/burst_det.log" &')
    if server_name == "sensorcontrol":
        os.system('gnome-terminal --command "multitail /tmp/burst_sensor_control.log" &')

    if server_name == "pcl":
        os.system('gnome-terminal --command "multitail /tmp/burst_pcl.log" &')
    if server_name == "pet":
        os.system('gnome-terminal --command "multitail /tmp/burst_pet.log" &')
    if server_name == "replay":
        os.system('gnome-terminal --command "multitail /tmp/burst_replay.log" &')
        


def makeform(root, fields):
    """
    Makes the GUI form
    """
    entries = []

    for field in fields:
        row = tkinter.Frame(root)
        lab = tkinter.Label(row, width=40, text=field, anchor="w")
        start_butt = tkinter.Button(
            row, text="Start", command=(lambda e=[field], r=row: startServer(e[0]))
        )
        start_butt.pack(side=tkinter.LEFT, padx=5, pady=5)
        stop_butt = tkinter.Button(
            row, text="Stop", command=(lambda e=[field], r=row: stopServer(e[0]))
        )
        stop_butt.pack(side=tkinter.LEFT, padx=5, pady=5)
        log_butt = tkinter.Button(
            row, text="Show Log", command=(lambda e=[field], r=row: showLog(e[0]))
        )
        log_butt.pack(side=tkinter.LEFT, padx=5, pady=5)
        ent = tkinter.Entry(row, width=10)
        row.pack(side=tkinter.TOP, fill=tkinter.X, padx=5, pady=5)
        lab.pack(side=tkinter.LEFT)
        start_butt.pack(side=tkinter.RIGHT, expand=tkinter.YES, fill=tkinter.X)
        stop_butt.pack(side=tkinter.RIGHT, expand=tkinter.YES, fill=tkinter.X)
        log_butt.pack(side=tkinter.RIGHT, expand=tkinter.YES, fill=tkinter.X)
        ent.pack(side=tkinter.RIGHT, expand=tkinter.YES, fill=tkinter.X)
        entries.append((field, start_butt, stop_butt, log_butt, ent))

    return entries

def clean_db():
    """cleans all hanging connections to DB if any"""
    conn = dbfunctions.connect_to_db()
    cur = conn.cursor()
    cur.execute(
        """SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'red' AND state = 'idle'"""
    )
    conn.commit()
    cur.close()
    conn.close()
    #popupmsg("Connections to DB killed. Please restart servers.")

def checkServers():

    # 'radterrain', 'webserver', 'geoplot', 'detection', 'sensorcontrol', 'pcl', 'pet', 'replay',
    for i in range(0, len(server_ents)):
        server_ents[i][4].delete(0, "end")  # this writes to the text field of RAD

    if (find_proc_by_name(openburst_config.radterrain_server_app) ) is not None:
        server_ents[0][4].insert(0, "running")
    if (find_proc_by_name(openburst_config.web_server_app) ) is not None:
        server_ents[1][4].insert(0, "running")
    if (find_proc_by_name(openburst_config.geoplot_server_app) ) is not None:
        server_ents[2][4].insert(0, "running")
    if (find_proc_by_name(openburst_config.detection_server_app) ) is not None:
        server_ents[3][4].insert(0, "running")
    if (find_proc_by_name(openburst_config.sensor_control_app) ) is not None:
        server_ents[4][4].insert(0, "running")
    if (find_proc_by_name(openburst_config.pcl_server_app) ) is not None:
        server_ents[5][4].insert(0, "running")
    if (find_proc_by_name(openburst_config.pet_server_app) ) is not None:
        server_ents[6][4].insert(0, "running")
    if (find_proc_by_name(openburst_config.replay_server_app) ) is not None:
        server_ents[7][4].insert(0, "running")

    return


###################################### main GUI function #############################

if __name__ == "__main__":

    print("******************************************************************************")
    print("*                                                                            *")
    print("*  This program is free software; you can redistribute it and/or modify it   *")
    print("*  under the terms of the GNU General Public License as published by the     *")
    print("*  Free Software Foundation; either version 3 of the License or any later    *")
    print("*  version.								     *")
    print("*  This program is distributed in the hope that it will useful, but WITHOUT  *")
    print("*  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or     *")
    print("*  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License     *")
    print("*  for more details.							     *")
    print("*  https://www.gnu.org/licenses/gpl-3.0.en.html                              *")
    print("******************************************************************************")

    root = tkinter.Tk()
    root.title("openburst Launchpad")

    ## -------------create all the tabs
    note = ttk.Notebook(root)
    tab_server = tkinter.Frame(note)
    tab_misc = tkinter.Frame(note)
    note.add(tab_server, text="Module", compound=tkinter.TOP)
    #note.add(tab_misc, text="Client")
    note.pack()

    # ------------------populate server fields
    server_ents = makeform(tab_server, openburst_config.server_fields)

    ############### populate root gui
    row1_root = tkinter.Frame(root)
    row2_root = tkinter.Frame(root)

    row2_root.pack(side=tkinter.TOP, fill=tkinter.X, padx=5, pady=5)

    # ------------ check button
    row3_root = tkinter.Frame(root)
    b2 = tkinter.Button(
        row3_root, text="Check", command=(lambda e=[], r=row3_root: checkServers())
    )
    row3_root.pack(side=tkinter.TOP, fill=tkinter.X, padx=5, pady=5)
    b2.pack(side=tkinter.LEFT)

    # ------------ clean DB
    b4 = tkinter.Button(
        row3_root, text="CleanDB", command=(lambda e=[], r=row3_root: clean_db())
    )
    row3_root.pack(side=tkinter.TOP, fill=tkinter.X, padx=5, pady=5)
    b4.pack(side=tkinter.RIGHT)

    # ------------ quit button
    b3 = tkinter.Button(row3_root, text="Quit", command=root.destroy)
    row3_root.pack(side=tkinter.TOP, fill=tkinter.X, padx=5, pady=5)
    b3.pack(side=tkinter.RIGHT)

    root.mainloop()
