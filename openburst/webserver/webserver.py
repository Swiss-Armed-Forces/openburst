"""
This Websocket server serves as the webserver for the client browser
"""

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.options
import tornado.websocket
import os.path
from tornado.options import define, options
import json
import logging

from openburst.functions import dbfunctions
from openburst.functions import basefunctions

proxy_port = 0
# this is the port of the proxy server. will be set in function main()

define("port", default=8888, help="run on the given port", type=int)


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")


class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("login.html")


class LoginHandler(BaseHandler):
    @tornado.gen.coroutine
    def get(self):
        incorrect = self.get_secure_cookie("incorrect")
        if incorrect and int(incorrect) > 20:
            self.write("<center>blocked</center>")
            return
        self.render("login.html")

    @tornado.gen.coroutine
    def post(self):
        incorrect = self.get_secure_cookie("incorrect")
        if incorrect and int(incorrect) > 20:
            self.write("<center>blocked</center>")
            return

        getteamname = tornado.escape.xhtml_escape(self.get_argument("teamname"))
        getpassword = tornado.escape.xhtml_escape(self.get_argument("password"))
        getnode = tornado.escape.xhtml_escape(self.get_argument("node"))
        if "white" == getteamname:
            self.render("white.html")
        elif "admin" == getteamname and "admin" == getpassword:
            self.render("admin.html")
        elif "red" == getteamname:
            self.render("red.html")
        elif "theater" == getnode:
            proxy_server_add = "ws://localhost:8888/proxy"
            print("burst_hmiserver: sending: ", proxy_server_add)
            self.render(
                "bluetheater.html",
                proxy_server=proxy_server_add,
                team=getteamname,
                node=getnode,
            )
        elif "airpic" == getnode:
            proxy_server_add = "ws://localhost:8888/proxy"
            self.render(
                "blueairpic.html",
                proxy_server=proxy_server_add,
                team=getteamname,
                node=getnode,
            )

        else:
            incorrect = self.get_secure_cookie("incorrect") or 0
            increased = str(int(incorrect) + 1)
            self.set_secure_cookie("incorrect", increased)
            self.write(
                """<center>
                            openBURST: Something Wrong With Your Login (%s)<br />
                            <a href="/">Try Again</a>
                          </center>"""
                % increased
            )


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(self.get_argument("next", self.reverse_url("main")))

    # client disconnected
    def on_close(self):
        pass


class ProxyWebSocketHandler(tornado.websocket.WebSocketHandler):

    def check_origin(self, origin):
        return True

    # the client connected
    def open(self):
        logging.getLogger("HMI").info("New Proxy client connected")

    # the client sent the message
    def on_message(self, message):
        line = message
        logging.getLogger("HMI").info("proxy client wrote: %s", line)
        [ip, port] = dbfunctions.read_server_ip_port_from_db(line)
        logging.getLogger("HMI").info("ip, port: %s,%s", "localhost", port)
        retwsstr = "ws://" + "localhost" + ":" + str(port) + "/" + line
        retval = [line, retwsstr]
        logging.getLogger("HMI").info("returning: %s", retval)
        self.write_message(json.dumps(retval))


class Application(tornado.web.Application):
    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # print "base_dir = ", base_dir

        settings = {
            "cookie_secret": "bZJc2sWbQLKos6GkHn/VB9oXwQt8S0R0kRvJ5/xJ89E=",
            "login_url": "/login",
            "template_path": os.path.join(base_dir, "../templates"),
            "static_path": os.path.join(base_dir, "../static"),
            "debug": True,
            "xsrf_cookies": False,
        }

        tornado.web.Application.__init__(
            self,
            [
                tornado.web.url(r"/", MainHandler, name="main"),
                tornado.web.url(r"/login", LoginHandler, name="login"),
                tornado.web.url(r"/logout", LogoutHandler, name="logout"),
                (r"/proxy", ProxyWebSocketHandler),
            ],
            **settings
        )


def main():
    logger_dir = basefunctions.get_openburst_logging_dir()
    logger_file = logger_dir + "burst_hmi_logging.json"
    logger = basefunctions.setup_logging(logger_file, "hmi")
    logger.info(
        "----------------------------------------------------------------------------------------"
    )
    logger.info(
        "-------------------------------------HMI Server newly started---------------------------"
    )
    logger.info(
        "----------------------------------------------------------------------------------------"
    )

    tornado.options.parse_command_line()
    global proxy_port
    proxy_port = options.port
    Application().listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
