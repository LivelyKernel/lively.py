import ast


def print_ast(node):
    def __print__(node, path):
        if len(path) > 0:
            print(path[-1])
        path_from_parent = path[-1] if len(path) > 0 else []
        return "{}{} ({})".format(
            " " * len(path),
            node.__class__.__name__,
            ".".join(map(str, path_from_parent)))
    return "\n".join([__print__(node, path) for node, path in visit_ast(node)])


def visit_ast(node, path=[]):
    """simple linear generator for nodes and their path"""
    yield (node, path)
    for field, value in ast.iter_fields(node):
        if isinstance(value, list):
            for n, item in enumerate(value):
                if isinstance(item, ast.AST):
                    yield from visit_ast(item, path + [[field, n]])
        elif isinstance(value, ast.AST):
            yield from visit_ast(value, path + [[field]])


# import astor
# print(astor.codegen.to_source(parsed))
