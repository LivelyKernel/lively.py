"""

Server for epc / emacs connections.

# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

Client code:

(require 'epc)

(setq epc:debug-out t)

;; (setq my-epc (epc:start-epc "python" '("lively/epc-server.py")))
(setq my-epc
      (epc:init-epc-layer
       (make-epc:manager :server-process nil
                         :commands '()
                         :title "test epc"
                         :port 52130
                         :connection (epc:connect "localhost" "9934"))))

(deferred:$
  (epc:call-deferred my-epc 'run_eval '("123 / 123"))
  (deferred:nextc it
    (lambda (x) (message "Return : %S" x))))

(deferred:$
  (epc:call-deferred my-epc 'code_format '("foo(3,4)"))
  (deferred:nextc it
    (lambda (x) (message "Return : %S" x))))


(deferred:$
  (epc:call-deferred my-epc 'get_completions '("import os\nos.p" 2 4))
  (deferred:nextc it
    (lambda (x) (message "Return : %S" x))))



(epc:stop-epc my-epc)

"""

from epc.server import EPCServer
from lively.eval import run_eval
from lively.code_formatting import code_format
from lively.completions import get_completions
import asyncio


def asyncio_wait(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(future)
    wrapper.__name__ = f.__name__
    return wrapper


def start_server(host='localhost', port=0):
    server = EPCServer((host, port))
    server.register_function(asyncio_wait(run_eval))
    server.register_function(code_format)
    server.register_function(asyncio_wait(get_completions))
    server.print_port()
    server.serve_forever()


if __name__ == '__main__':
    start_server()
