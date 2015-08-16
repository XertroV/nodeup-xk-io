#!/usr/bin/env python3

import tornado.web
import tornado.wsgi
import argparse

from handlers import RandomRedirectHandler, UserHandler, APIHandler

parser = argparse.ArgumentParser()
args = parser.parse_args()

if __name__ == "__main__":
    application = tornado.web.Application([
        (r"/", RandomRedirectHandler),
        (r"/api", APIHandler),
        (r"/static/(.*)", tornado.web.StaticFileHandler, {'path': './static/'}),
        (r"/([^/]+)", UserHandler),
    ], debug=True, autoreload=True)
    application.listen(8888)

    print('Starting server...')
    tornado.ioloop.IOLoop.current().start()