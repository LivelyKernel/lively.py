import ast
from logging import warning


class EvalResult(object):
    """result of run_eval"""
    def __init__(self, value, isError = False):
        self.value = value
        self.isError = isError
        self.isEvalResult = True


class Evaluation(object):

    __validation_template__ = ("async def __eval_validation__():\n"
                               "        {}\n\n")

    __async_template__ = ("async def __eval__():\n"
                           "        {}\n\n"
                           "try:\n"
                           "    import asyncio\n"
                           "    loop = asyncio.get_event_loop()\n"
                           "    task = loop.create_task(__eval__())\n"
                           "    loop.run_until_complete(asyncio.wait([task]))\n"
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
            # transform so last expression is passed to callback function
            parsed.body[0].body[-1] = ast.Return(value=last_expr.value)
        else:
            parsed.body.append(ast.Return(value=ast.NameConstant(value=None)))

        return ast.fix_missing_locations(parsed)

    def prepare_source_async(self, source):
        # wrap code in a function and call it so we can do async stuff
        callable_source = self.__async_template__ .format(
            "\n        ".join(source.splitlines()))
        parsed = ast.parse(callable_source, mode='exec')

        last_expr = parsed.body[0].body[-1]
        if (isinstance(last_expr, ast.Expr)):
            # transform so last expression is passed to callback function
            parsed.body[0].body[-1] = ast.Expr(value=ast.Call(
                func=ast.Name(id='__eval_done__', ctx=ast.Load()),
                args=[last_expr.value], keywords=[]))
        else:
            parsed.body.append(
                ast.Expr(value=ast.Call(
                    func=ast.Name(id='__eval_done__', ctx=ast.Load()),
                    args=[ast.NameConstant(value=None)], keywords=[])))

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

        g = dict(g)
        g.__setitem__("__eval_done__", __eval_done__)
        g.__setitem__("__eval_done_called__", False)
        exec(compile(parsed, '<lively_eval>', 'exec'), g, l)

        return self.result

    def run_eval(self, when_done, g = globals(), l = locals()):
        valid, errors = self.is_valid(source, True)
        if not valid:
            raise Exception("pre-eval errors:\n{}".format("\n".join(errors)))

        self.status = "started"

        parsed = self.prepare_source_async(self.source)

        def __eval_done__(value, isError = False):
            if (g.get("__eval_done_called__")):
                warning("run_eval done callback was called multiple times, ignoring")
            else:
                g.__setitem__("__eval_done_called__", True)
                self.result = EvalResult(value, isError)
                self.status = "done"
                when_done(self.result)

        g = dict(g)
        g.__setitem__("__eval_done__", __eval_done__)
        g.__setitem__("__eval_done_called__", False)
        exec(compile(parsed, '<lively_eval>', 'exec'), g, l)

        return self

def sync_eval(source, glob = globals(), loc = locals()):
    return Evaluation(source).sync_eval(glob, loc)

def run_eval(source, when_done_fn, glob = globals(), loc = locals()):
    return Evaluation(source).run_eval(when_done_fn, glob, loc)


def example():
    e = Evaluation("1+2\n23")
    e.run_eval(lambda val: print(print_obj(val)))
    print_obj(e.sync_eval())
    e.result.value

def example2():
    sync_eval("1 + 2")
    run_eval("1 + 2", lambda result: print(result.value))
