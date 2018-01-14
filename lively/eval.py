import sys
import io
import asyncio
import json
import ast
from sexpdata import SExpBase
from logging import warning


class EvalResult(SExpBase):
    """result of run_eval"""

    def __init__(self, value, stdout="", stderr="", is_error=False):
        super().__init__(value)
        self.value = value
        self.stdout = stdout
        self.stderr = stderr
        self.value = value
        self.is_error = is_error

    def as_dict(self):
        return {
            'isError': self.is_error,
            "isEvalResult": True,
            "value": repr(self.value),
            "stdout": self.stdout,
            "stderr": self.stderr
        }

    def json_stringify(self):
        return json.dumps(self.as_dict())

    def tosexp(self, tosexp):
        return tosexp(self.as_dict())


class Evaluation(object):

    __validation_template__ = ("async def __eval_validation__():\n"
                               "        {}\n\n")

    __async_template__ = (
        "async def __eval__():\n"
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
    source: str = ""
    status: str = "not started"
    result: EvalResult = None

    def __init__(self, source, module_name):
        self.source = source
        self.module_name = module_name

    def is_valid(self, source, allow_async=False, module=None):
        source = self.__validation_template__.format("\n        ".join(source.splitlines()))
        parsed = ast.parse(source, mode='exec')
        errors = []
        for node in parsed.body[0].body:
            if not allow_async and isinstance(node, ast.Await):
                msg = "async statement in eval"
                if hasattr(node, "lineno"):
                    msg += " at line {}".format(node.lineno - 1)
                errors.append(msg)
            if isinstance(node, (ast.Yield, ast.YieldFrom)):
                msg = "yield statement in eval"
                if hasattr(node, "lineno"):
                    msg += " at line {}".format(node.lineno - 1)
                errors.append(msg)
        return (len(errors) == 0, errors)

    def prepare_source(self, source, template):
        callable_source = template.format(
            "\n        ".join(source.splitlines()))
        parsed = ast.parse(callable_source, mode='exec')

        # return the last expression
        last_expr = parsed.body[0].body[-1]
        ret_val = last_expr.value if isinstance(
            last_expr, ast.Expr) else ast.NameConstant(value=None)
        ret_assign = ast.Assign(
            targets=[ast.Name(id='__eval_result__', ctx=ast.Store())],
            value=ret_val)
        if (isinstance(last_expr, ast.Expr)):
            parsed.body[0].body[-1] = ret_assign
        else:
            parsed.body[0].body.append(ret_assign)
        # copy locals into globals so we "record" them
        parsed.body[0].body.extend(
            ast.parse(("globals().update(locals())\n"
                       "return __eval_result__")).body)

        return ast.fix_missing_locations(parsed)

    def sync_eval(self):
        """Evaluates self.source and returns EvalResult object synchronously. Changes in
        the module __dict__ of self.module_name will persist, such as declared toplevel
        variables."""
        self.__eval__(self.__sync_template__)
        return self.result

    def run_eval(self, when_done):
        """Evaluates self.source and calls when_done callback with EvalResult object.
        the module __dict__ of self.module_name will persist, such as declared toplevel
        variables."""
        return self.__eval__(self.__async_template__, when_done)

    def __eval__(self, code_template, when_done=None):
        "internal, do not use"

        # if module is specified, look it up. If not loaded, import it.
        eval_in_module = sys.modules.get(self.module_name or "__main__" or __name__)
        if not eval_in_module:
            try:
                __import__(self.module_name)
                eval_in_module = sys.modules.get(self.module_name)
                if not eval_in_module:
                    raise Exception("module " + self.module_name + " not found")
            except Exception:
                warning("[eval] could not load module %s".format(self.module_name))
                eval_in_module = sys.modules.get("__main__" or __name__)

        if not eval_in_module:
            raise Exception("[lively eval] could not find module " + self.module_name)

        # globals, locals for eval
        _globals = eval_in_module.__dict__
        _locals = eval_in_module.__dict__

        valid, errors = self.is_valid(self.source, True)
        if not valid:
            raise Exception("pre-eval errors:\n{}".format("\n".join(errors)))

        self.status = "started"

        parsed = self.prepare_source(self.source, code_template)

        def __eval_done__(value, is_error=False):
            call_count = _globals.get("__eval_done_called__")
            if (call_count > 0):
                warning("[lively eval] done callback was called multiple times, ignoring")
            else:
                _globals.__setitem__("__eval_done_called__", call_count + 1)
                sys.stdout, sys.stderr = oldout, olderr
                stdout = eval_output[0].getvalue()
                stderr = eval_output[1].getvalue()

                self.result = EvalResult(value, stdout, stderr, is_error)
                self.status = "done"
                if when_done:
                    when_done(self.result)

        _globals.__setitem__("__eval_done__", __eval_done__)
        _globals.__setitem__("__eval_done_called__", 0)

        # capture stdout + stderr
        oldout, olderr = sys.stdout, sys.stderr
        eval_output = [io.StringIO(), io.StringIO()]
        sys.stdout, sys.stderr = eval_output


        exec(compile(parsed, eval_in_module.__file__, 'exec'), _globals, _locals)

        return self


def sync_eval(source, module_name=None):
    """
    Evaluate source inside module specified by module_name and return EvalObject with properties value and is_error
    """
    return Evaluation(source, module_name).sync_eval()


def run_eval(source, module_name=None):
    """Evalualtes source in module specified by module_name and returns future. Note
    that you can use top-level await statements inside source."""
    result_fut = asyncio.Future()
    Evaluation(source, module_name).run_eval(
        lambda result: result_fut.set_result(result))
    return result_fut


# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def example():
    e = Evaluation("1+2\n23")
    e.run_eval(lambda val: print(print(val)))
    print(e.sync_eval())
    e.result.value
    sync_eval("1 + 2")

async def example2():
    """
    run with
    asyncio.get_event_loop().run_until_complete(example2())
    """
    result = await run_eval("1 + 2")
    print(result.__dict__)
