#!/usr/bin/env python3
import socket
import threading
import queue
import tkinter as tk
from tkinter import ttk, scrolledtext
from openburst.types import bi_sensor_frame
import multiprocessing as mp

HOST = "0.0.0.0"
PORT = 9999
BUFFER_SIZE = 4096

sensor_frame_array = [] # list of sensr_frame_objects

def create_add_new_sensor_framer(id):
    framer = bi_sensor_frame.SensorFrame(id)
    sensor_frame_array.append(framer)
    process = mp.Process(
        target=framer.callback,
        args=(
            
        ),
    )
    process.start()

def insert_bistatic_plot(args):
    # args: time[s], plot_id, range[m], vel[m/s], targ_id
    plot_time = args[0] 
    plot_id = args[1]  
    bi_range = args[2]
    bi_vel = args[3]
    #targ_id = args[4] 

    done = False
    for sens_fr in sensor_frame_array:
        if (sens_fr.id == plot_id):
            done = True
            sens_fr.queue.put((plot_time, bi_range, bi_vel)) #insert_bistatic_plot_to_frame(plot_time, bi_range, bi_vel)
            break
    if not done:
        create_add_new_sensor_framer(plot_id)
        #sensor_frame_array[-1].insert_bistatic_plot_to_frame(plot_time, bi_range, bi_vel)
        sensor_frame_array[-1].queue.put((plot_time, bi_range, bi_vel))


def parse_msg(msg):
    """
    Erwartetes Format:
        CMD
        CMD arg1
        CMD arg1,arg2,arg3,arg4

    Regeln:
    - CMD ist Pflicht
    - Falls Argumente folgen, kommt genau nach CMD ein Leerschlag
    - Falls keine Argumente folgen, gibt es keinen Leerschlag
    - 0 bis 5 Argumente
    - Argumente sind durch Komma getrennt
    """

    msg = msg.rstrip("\r\n")

    if not msg:
        raise ValueError("empty message")

    if " " in msg:
        cmd, arg_text = msg.split(" ", 1)

        cmd = cmd.strip()

        if not cmd:
            raise ValueError("missing command")

        if arg_text.strip() == "":
            raise ValueError("space without arguments")

        args = [arg.strip() for arg in arg_text.split(",")]

    else:
        cmd = msg.strip()

        if not cmd:
            raise ValueError("missing command")

        args = []

    if len(args) > 5:
        raise ValueError(f"too many arguments: {len(args)}")

    for arg in args:
        if arg == "":
            raise ValueError("empty argument")

    return cmd, args


class UdpServiceGui:
    def __init__(self, root):
        self.root = root
        self.root.title("UDP Test Service")
        self.root.geometry("800x500")
        self.root.attributes("-topmost", True)

        self.msg_queue = queue.Queue()
        self.running = False
        self.sock = None
        self.thread = None

        self.create_widgets()
        self.start_server()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.process_queue)

    def create_widgets(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        self.status_label = ttk.Label(frame, text="UDP service not running")
        self.status_label.pack(anchor="w")

        # Buttons zuerst, damit sie beim Resize nicht verschwinden
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, pady=(10, 5))

        self.clear_button = ttk.Button(
            button_frame,
            text="Clear",
            command=self.clear_messages
        )
        self.clear_button.pack(side=tk.LEFT)

        self.quit_button = ttk.Button(
            button_frame,
            text="Quit",
            command=self.on_close
        )
        self.quit_button.pack(side=tk.RIGHT)

        self.text = scrolledtext.ScrolledText(
            frame,
            width=90,
            height=25,
            state="disabled"
        )
        self.text.pack(fill=tk.BOTH, expand=True)

    def start_server(self):
        self.running = True

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((HOST, PORT))
        self.sock.settimeout(0.5)

        self.thread = threading.Thread(target=self.server_loop, daemon=True)
        self.thread.start()

        self.status_label.config(text=f"UDP service listening on {HOST}:{PORT}")

    def server_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)

                msg = data.decode("utf-8", errors="replace")

                try:
                    cmd, args = parse_msg(msg)
                    display_msg = f"{cmd} {args}"
                    self.handle_command(cmd, args)

                except ValueError as e:
                    display_msg = f"INVALID MSG: {msg} ({e})"

                self.msg_queue.put(display_msg)

            except socket.timeout:
                continue

            except OSError:
                break

            except Exception as e:
                self.msg_queue.put(f"ERROR: {e}")
                break

    def handle_command(self, cmd, args):
        """
        Hier kannst du später die Kommandos auswerten.

        Beispiel:
            if cmd == "PING":
                ...
            elif cmd == "MOVE":
                ...
        """
        if cmd == "PLOT":
            # args: time[s], plot_id, range[m], vel[m/s], targ_id
            insert_bistatic_plot(args)

    def process_queue(self):
        while not self.msg_queue.empty():
            msg = self.msg_queue.get()
            self.add_message(msg)

        if self.running:
            self.root.after(100, self.process_queue)

    def add_message(self, msg):
        self.text.config(state="normal")
        self.text.insert(tk.END, msg + "\n")
        self.text.see(tk.END)
        self.text.config(state="disabled")

    def clear_messages(self):
        self.text.config(state="normal")
        self.text.delete("1.0", tk.END)
        self.text.config(state="disabled")

    def stop_server(self):
        if not self.running:
            return

        self.running = False

        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=1.0)

        self.status_label.config(text="UDP service stopped")

    def on_close(self):
        self.stop_server()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = UdpServiceGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
