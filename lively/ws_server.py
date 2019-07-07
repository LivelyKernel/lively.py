import asyncio
from multiprocessing import Process
import json
import traceback
import websockets
from lively.eval import run_eval
from lively.completions import get_completions
from lively.code_formatting import code_format

def test():
    loop = asyncio.get_event_loop()
    start("0.0.0.0", 9942, loop)


debug = True

async def handle_eval(data, websocket):
    source = data.get("source")
    module_name = data.get("moduleName")

    if not source:
        await websocket.send(json.dumps({"error": "needs source"}))
        return

    if debug:
        print("evaluating {}".format(
            (source[:30] + "..." if len(source) > 30 else source).replace("\n", "")))

    result = await run_eval(source, module_name, websocket)
    # if debug: print("eval done", result, result.json_stringify())
    await websocket.send(result.json_stringify())


async def handle_completion(data, websocket):
    if "source" not in data:
        return await websocket.send(json.dumps({"error": "needs source"}))
    if "row" not in data:
        return await websocket.send(json.dumps({"error": "needs row"}))
    if "column" not in data:
        return await websocket.send(json.dumps({"error": "needs column"}))

    completions = await get_completions(
        data.get("source"),
        data.get("row"),
        data.get("column"),
        data.get("file") or "__workspace__.py")
    if debug:
        print("completions: {}".format(len(completions)))
    await websocket.send(json.dumps(completions))

async def handle_code_format(data, websocket):
    if "source" not in data:
        return await websocket.send(json.dumps({"error": "needs source"}))

    try:
        formatted_code = code_format(
            data.get("source"),
            data.get("lines"),
            data.get("file") or "<unknown>",
            data.get("style"))
        if debug:
            print("code_format done")
        answer = formatted_code
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
    if debug:
        print("got connection")
    connections.add(websocket)

    # allow client to send itself extra data
    websocket.send_raw_data = lambda data: websocket.send(data)

    while True:
        try:
            message = await websocket.recv()
        except websockets.exceptions.ConnectionClosed:
            if debug:
                print("connection closed")
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

def fix_pager():
    __import__("os").environ['PAGER'] = 'cat'

def start(hostname=default_host,
          port=default_port,
          loop=asyncio.get_event_loop()):
    fix_pager()
    serve = websockets.serve(handler, hostname, port)
    loop.run_until_complete(serve)
    print("server listening on {}:{}".format(hostname, port))
    return serve

def start_in_subprocess(**opts):
    def spawn():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        start(**{**opts, "loop": loop})
        loop.run_forever()
    process = Process(target=spawn, kwargs=opts)
    process.start()
    return process

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    start(loop=loop)
    loop.run_forever()
