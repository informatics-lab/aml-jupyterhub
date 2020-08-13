import time
import http.server
import socketserver
import threading

TAKEN_PORTS = []
START_PORT = 9001
REDIRECTS = {}

# with thanks https://gist.github.com/shreddd/b7991ab491384e3c3331


def get_existing_redirect(url):
    port = REDIRECTS.get(url, None)
    return port if ("0.0.0.0", port) else None


def redirect_handler_factory(url):
    """
    Returns a request handler class that redirects to supplied `url`
    """
    class RedirectHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header('Location', url)
            self.end_headers()

    return RedirectHandler


def _create_server(url, port):
    port = port
    with socketserver.TCPServer(("", port), redirect_handler_factory(url)) as httpd:
        print("serving at port", port)
        httpd.serve_forever()


class RedirectServer:
    # A simple
    def __init__(self, redirect_to_url):
        self.url = redirect_to_url
        super().__init__()

    def start(self):
        global TAKEN_PORTS
        port = START_PORT
        while port in TAKEN_PORTS:
            port += 1
        TAKEN_PORTS += [port]
        self.port = port
        self.server_thread = threading.Thread(target=_create_server, args=[self.url, port], daemon=True)
        self.server_thread.start()

    def stop(self):
        try:
            self.server_thread.stop()
            TAKEN_PORTS.remove(self.port)
        except Exception as e:
            print(e)
            raise e
        pass

    @property
    def route(self):
        return ("0.0.0.0", self.port)


# rs = RedirectServer('https://google.com', 'theo')
# rs.start()
# print(rs.port, rs.url, rs.server_thread)

# time.sleep(15)
# print('no longer sleepy, everything should die...')
