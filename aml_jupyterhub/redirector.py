import time
import http.server
import socketserver
import multiprocessing


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
    _start_port = 9001
    _redirects = {}

    @classmethod
    def get_existing_redirect(cls, url):
        port = cls._redirects.get('port')
        return port if ("0.0.0.0", port) else None

    @classmethod
    def _get_free_port(cls):
        port = cls._start_port
        taken = list(cls._redirects.values())
        while port in taken:
            port += 1
        return port

    def __init__(self, redirect_to_url):
        self.url = redirect_to_url
        super().__init__()

    def start(self):

        print('start')
        self.port = RedirectServer._get_free_port()
        self.server_process = multiprocessing.Process(target=_create_server, args=[self.url, self.port], daemon=True)
        self.server_process.start()
        RedirectServer._redirects[self.url] = self.port

    def stop(self):
        try:
            self.server_process.terminate()
            del RedirectServer._redirects[self.url]

        except Exception as e:
            print(e)
            raise e
        pass

    @property
    def route(self):
        return ("0.0.0.0", self.port)
