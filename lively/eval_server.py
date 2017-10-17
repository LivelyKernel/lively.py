import asyncio
import datetime
import random
import sys
import json
import traceback
import websockets
from .eval import run_eval
from .completions import get_completions
from yapf.yapflib.yapf_api import FormatCode


def test():
    loop = asyncio.get_event_loop()
    serve = start("0.0.0.0", 9942, loop)

# test()
# serve.server.close()

debug = True

async def handle_eval(data, websocket):
    source = data.get("source")

    if not source:
        await websocket.send(json.dumps({"error": "needs source"}))
        return

    if debug: print("evaluating {}".format((source[:30] + "..." if len(source) > 30 else source).replace("\n", "")))
    result = await run_eval(source)
    # if debug: print("eval done", result, result.json_stringify())
    await websocket.send(result.json_stringify())


async def handle_completion(data, websocket):
    if not "source" in data: return await websocket.send(json.dumps({"error": "needs source"}))
    if not "row" in data: return await websocket.send(json.dumps({"error": "needs row"}))
    if not "column" in data: return await websocket.send(json.dumps({"error": "needs column"}))

    completions = await get_completions(
      data.get("source"),
      data.get("row"),
      data.get("column"),
      data.get("file") or "__workspace__.py")
    if debug: print("completions: {}".format(len(completions)))
    await websocket.send(json.dumps(completions))

async def handle_code_format(data, websocket):
    if not "source" in data: return await websocket.send(json.dumps({"error": "needs source"}))

    try:
      (formatted_code, success) = FormatCode(
        data.get("source"),
        lines=data.get("lines"),
        filename=data.get("file") or "<unknown>",
        style_config=data.get("style"))
      if debug: print("code_format done")
      answer = formatted_code;
    except Exception as err:
      answer = json.dumps({'error': str(err)})
    print(data.get("lines"))
    await websocket.send(json.dumps(answer))


async def handle_message(message, websocket, path):
    """{action, data, target}"""
    action = message.get("action")
    data = message.get("data")

    if not action:
        await websocket.send(json.dumps({"error": "message needs action"}))
        return

    if action == "eval":
        return await handle_eval(data, websocket)
    if action == "completion":
        return await handle_completion(data, websocket)
    if action == "code_format":
        return await handle_code_format(data, websocket)

    await websocket.send(json.dumps({"error": "message not understood {}".format(action)}))


connections = set()

async def handler(websocket, path):
    if debug: print("got connection")
    connections.add(websocket)
    while True:
        try:
            message = await websocket.recv()
        except websockets.exceptions.ConnectionClosed:
            if debug: print("connection closed")
            connections.remove(websocket)
            break
        # if debug: print("got " + message)
        try:
            parsed = json.loads(message)
            await handle_message(parsed, websocket, path)
        except Exception as err:
            # err_str = json.dumps({"error": str(err)})
            # err_str = json.dumps({"error": "\n".join(traceback.format_tb(err.__traceback__))})
            err_str = json.dumps({"error": traceback.format_exc()})
            print("error in handle_message: " + err_str)
            await websocket.send(err_str)
            continue


# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# server start

default_port = 9942
default_host = "127.0.0.1"

def start(hostname=default_host,
          port=default_port,
          loop=asyncio.get_event_loop()):
    serve = websockets.serve(handler, hostname, port)
    loop.run_until_complete(serve)
    print("server listening on {}:{}".format(hostname, port))
    return serve
