# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# main
import argparse
import asyncio
from lively.eval_server import (start, default_host, default_port)

def main():
    parser = argparse.ArgumentParser(description='Starts a websocket server for eval requests')
    parser.add_argument('--hostname', dest="hostname", type=str, default=default_host, help='hostname, defaults to '.format(default_host))
    parser.add_argument('--port', dest="port", type=int, default=default_port, help='port, defaults to {}'.format(default_port))
    args = parser.parse_args()
    loop = asyncio.get_event_loop()
    start(args.hostname, args.port, loop)
    loop.run_forever()
