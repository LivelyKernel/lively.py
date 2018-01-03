<!-- -*- mode: markdown; -*- -->

# lively.py

[Lively-like](https://lively-next.org) live programming support for Python.

## Getting started

Starting in subprocess:
```py
__import__("lively.eval_server").eval_server.start_in_subprocess()
```

Starting in main thread and process with event loop passed in by users:

```py
import asyncio
import lively.eval_server
loop = asyncio.get_event_loop()
lively.eval_server.start(hostname="0.0.0.0", port=9942, loop=loop)
loop.run_forever()
```

# License

[MIT](LICENSE.txt)


<!--
upload to PyPi:

python setup.py sdist
python setup.py bdist_wheel --universal
python setup.py bdist_wheel
twine upload dist/* --skip-existing

-->

