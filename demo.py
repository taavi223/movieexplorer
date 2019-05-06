import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import HTTPError

class ProxyHTTPRequestHandler(SimpleHTTPRequestHandler):
    proxy_routes = {}
    static_directory = None

    @classmethod
    def set_proxy_routes(cls, proxy_routes):
        cls.proxy_routes = proxy_routes

    @classmethod
    def set_static_directory(cls, static_directory):
        cls.static_directory = static_directory

    def __init__(self, *args, **kwargs):
        directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        kwargs['directory'] = self.static_directory
        print("Serving directory %s" % directory)
        super().__init__(*args, **kwargs)

    def do_HEAD(self):
        parts = self.path.split('/')
        if len(parts) >= 2 and parts[1] in self.proxy_routes:
            url = self.proxy_routes[parts[1]] + '/'.join(parts[2:])
            self.proxy_request(url, method="HEAD")
        else:
            super().do_HEAD()

    def do_GET(self):
        parts = self.path.split('/')
        if len(parts) >= 2 and parts[1] in self.proxy_routes:
            url = self.proxy_routes[parts[1]] + '/'.join(parts[2:])
            self.proxy_request(url, method="GET")
        else:
            super().do_GET()

    def do_POST(self):
        parts = self.path.split('/')
        print(parts)
        if len(parts) >= 2 and parts[1] in self.proxy_routes:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            url = self.proxy_routes[parts[1]] + '/'.join(parts[2:])
            self.proxy_request(url, data=post_data, method="POST")
        else:
            super().do_POST()
    
    def end_headers(self):
        # Make development easy by not caching anything.
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()
    
    def proxy_request(self, url, **kwargs):
        try:
            req = Request(url, headers=self.headers, **kwargs)
            response = urlopen(req)
        except HTTPError as e:
            self.send_response_only(e.code)
            self.end_headers()
            return

        self.send_response_only(response.status)
        for name, value in response.headers.items():
            self.send_header(name, value)
        # Don't cache anything!
        self.end_headers()
        self.copyfile(response, self.wfile)
        

if __name__ == "__main__":
    # Proxy the any request starting with /api.
    ProxyHTTPRequestHandler.set_proxy_routes({"api": "http://127.0.0.1:5000/api"})
    
    # Serve all other requests from the static folder.
    ProxyHTTPRequestHandler.set_static_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"))
    
    print("Starting HTTP server and proxy")
    print("You will need to run the api/app.py file on port 5000")
    httpd = HTTPServer(("127.0.0.1", 8000), ProxyHTTPRequestHandler)
    httpd.serve_forever()
