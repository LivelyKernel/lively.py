import ast
import asyncio
import json
from logging import warning


class EvalResult(object):
    """result of run_eval"""
    def __init__(self, value, isError = False):
        self.value = value
        self.isError = isError
        self.isEvalResult = True

    def json_stringify(self):
        return json.dumps({
            'isError': self.isError,
            "isEvalResult": True,
            "value": repr(self.value)
        })


class Evaluation(object):

    __validation_template__ = ("async def __eval_validation__():\n"
                               "        {}\n\n")

    __async_template__ = ("async def __eval__():\n"
                           "        {}\n\n"
                           "try:\n"
                           "    import asyncio\n"
                           "    loop = asyncio.get_event_loop()\n"
                           "    future = asyncio.ensure_future(__eval__(), loop=loop)\n"
                           "    future.add_done_callback(lambda f: __eval_done__(f.exception() or f.result(), bool(f.exception())))\n"
                           "    if not loop.is_running():"
                           "        loop.run_until_complete(future)\n"
                           "except Exception as exc:\n"
                           "    __eval_done__(exc, True)\n")

    __sync_template__ = ("def __eval__():\n"
                           "        {}\n\n"
                           "try:\n"
                           "    __eval_done__(__eval__(), False)\n"
                           "except Exception as exc:\n"
                           "    __eval_done__(exc, True)\n")
    source = ""
    status = "not started"
    result = None

    def __init__(self, source):
        self.source = source

    def is_valid(self, source, allow_async = False):
        source = self.__validation_template__.format(
            "\n        ".join(source.splitlines()))
        parsed = ast.parse(source, mode='exec')
        errors = []
        for node in parsed.body[0].body:
            if not allow_async and isinstance(node, ast.Await):
                msg = "async statement in eval"
                if hasattr(node, "lineno"):
                    msg += " at line {}".format(node.lineno-1)
                errors.append(msg)
            if isinstance(node, (ast.Yield, ast.YieldFrom)):
                msg = "yield statement in eval"
                if hasattr(node, "lineno"):
                    msg += " at line {}".format(node.lineno-1)
                errors.append(msg)
        return (len(errors) == 0, errors)

    def prepare_source_sync(self, source):
        callable_source = self.__sync_template__.format(
            "\n        ".join(source.splitlines()))
        parsed = ast.parse(callable_source, mode='exec')

        last_expr = parsed.body[0].body[-1]
        if (isinstance(last_expr, ast.Expr)):
            parsed.body[0].body[-1] = ast.Return(value=last_expr.value)
        else:
            parsed.body[0].body.append(ast.Return(value=ast.NameConstant(value=None)))

        return ast.fix_missing_locations(parsed)

    def prepare_source_async(self, source):
        # wrap code in a function and call it so we can do async stuff
        callable_source = self.__async_template__ .format(
            "\n        ".join(source.splitlines()))
        parsed = ast.parse(callable_source, mode='exec')

        # return the last expression
        last_expr = parsed.body[0].body[-1]
        ret_val = last_expr.value if isinstance(last_expr, ast.Expr) else ast.NameConstant(value=None)
        ret_assign = ast.Assign(targets=[ast.Name(id='__eval_result__', ctx=ast.Store())], value=ret_val)
        if (isinstance(last_expr, ast.Expr)):
            parsed.body[0].body[-1] = ret_assign
        else:
            parsed.body[0].body.append(ret_assign)
        # copy locals into globals so we "record" them
        parsed.body[0].body.extend(
          ast.parse(("for k,v in locals().items():\n"
                     "    globals().__setitem__(k, v)\n"
                     "return __eval_result__")).body)
        
        # if (isinstance(last_expr, ast.Expr)):
        #     # transform so last expression is passed to callback function
        #     parsed.body[0].body[-1] = ast.Expr(value=ast.Call(
        #         func=ast.Name(id='__eval_done__', ctx=ast.Load()),
        #         args=[last_expr.value], keywords=[]))
        # else:
        #     parsed.body.append(
        #         ast.Expr(value=ast.Call(
        #             func=ast.Name(id='__eval_done__', ctx=ast.Load()),
        #             args=[ast.NameConstant(value=None)], keywords=[])))

        return ast.fix_missing_locations(parsed)


    def sync_eval(self, g = globals(), l = locals()):
        valid, errors = self.is_valid(source, False)
        if not valid:
            raise Exception("pre-eval errors:\n{}".format("\n".join(errors)))

        self.status = "started"
        parsed = self.prepare_source_sync(self.source)

        def __eval_done__(value, isError = False):
            if (g.get("__eval_done_called__")):
                warning("sync_eval done callback was called multiple times, ignoring")
            else:
                g.__setitem__("__eval_done_called__", True)
                self.result = EvalResult(value, isError)
                self.status = "done"

        # g = dict(g)
        g.__setitem__("__eval_done__", __eval_done__)
        g.__setitem__("__eval_done_called__", False)
        exec(compile(parsed, '<lively_eval>', 'exec'), g, l)

        return self.result

    def run_eval(self, when_done, g = globals(), l = locals()):
        valid, errors = self.is_valid(self.source, True)
        if not valid:
            raise Exception("pre-eval errors:\n{}".format("\n".join(errors)))

        self.status = "started"

        parsed = self.prepare_source_async(self.source)

        def __eval_done__(value, isError = False):
            call_count = g.get("__eval_done_called__")
            if (call_count > 0):
                warning("run_eval done callback was called multiple times, ignoring")
            else:
                g.__setitem__("__eval_done_called__", call_count+1)
                self.result = EvalResult(value, isError)
                self.status = "done"
                when_done(self.result)

        # g = dict(g)
        g.__setitem__("__eval_done__", __eval_done__)
        g.__setitem__("__eval_done_called__", 0)

        # import astor
        # print("Running code", astor.codegen.to_source(parsed))

        exec(compile(parsed, '<lively_eval>', 'exec'), g, l)

        return self

def sync_eval(source, glob = globals(), loc = locals()):
    return Evaluation(source).sync_eval(glob, loc)

def run_eval(source, glob = globals(), loc = locals()):
    result_fut = asyncio.Future()
    Evaluation(source).run_eval(
        lambda result: result_fut.set_result(result), glob, loc)
    return result_fut


# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def example():
    e = Evaluation("1+2\n23")
    e.run_eval(lambda val: print(print_obj(val)))
    print_obj(e.sync_eval())
    e.result.value
    sync_eval("1 + 2")

async def example2():
    """
    run with
    asyncio.get_event_loop().run_until_complete(example2())
    """
    result = await run_eval("1 + 2")
    print(result.__dict__)
