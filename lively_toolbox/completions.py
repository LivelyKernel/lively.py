import inspect
import jedi
from .eval import run_eval

async def get_completions(source, row, column, file):
    compl_data = []
    
    # try jedi
    script = jedi.Script(source, row, column, file)
    completions = script.completions()

    if (len(completions) > 0):
      compl_attrs = ["module_name", "module_path", "is_keyword", "type", "name", "full_name"]
      for compl in completions:
        data = {name: getattr(compl, name) for name in compl_attrs}
        data['priority'] = 1000
        if compl.type == "function":
          signature = "({})".format(",".join([p.name for p in compl.params]))
          data['name'] += signature
        compl_data.append(data)
      return compl_data


    # try to eval code snippet in front of column and dynamically use dir() on eval result
    line = source.splitlines()[row-1][:column]
    *_, expr = line.split(" ")
    prefix = ""
    if expr.endswith("."):
      expr = expr[:-1]
    elif "." in expr:
      *front_parts, prefix = expr.split(".")
      expr = ".".join(front_parts)

    result = await run_eval(expr)
    if result.isError: return []

    for key in dir(result.value):
      val = getattr(result.value, key)
      name = key
      if (inspect.ismethod(val)):
        type = "function"
        name += str(inspect.signature(val))
      else:
        type = "instance"
      compl_data.append({
        "name": name, "type": type,
        "module_name": expr, "prefix": prefix,
        "priority": 1000
      })
    return compl_data
