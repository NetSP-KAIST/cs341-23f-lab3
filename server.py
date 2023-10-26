#!/usr/bin/python3

from http.server import BaseHTTPRequestHandler, HTTPServer

class CS341RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        client = self.client_address[0]
        host = self.headers.get('Host')
        self.wfile.write('Hello {}, I am {}\n'.format(client,host).encode('utf-8'))
    def do_POST(self):
        self.do_GET()

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 80), CS341RequestHandler)
    server.serve_forever()