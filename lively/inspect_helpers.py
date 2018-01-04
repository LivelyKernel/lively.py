import math
from collections import Iterable
import pprint

# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# tree printing
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def print_tree(node, print_fn, child_fn, depth=0):
    printed = print_fn(node)
    children = child_fn(node)
    if children and len(children) > 0:
        child_lines = []
        *first, last = children
        for child in first:
            printed_child = print_tree(child, print_fn, child_fn, depth + 1)
            first_line, *rest_lines = printed_child.splitlines()
            child_lines.append("|-" + first_line)
            child_lines.extend(map(lambda line: "| " + line, rest_lines))
        first_last, *rest_last = print_tree(last, print_fn, child_fn, depth + 1).splitlines()
        child_lines.append("\-" + first_last)
        child_lines.extend(map(lambda line: "  " + line, rest_last))
        printed += "\n" + "\n".join(child_lines)
    return printed


def example1():
    a = {'name': "foo", 'children': [
        {'name': 'oi\nnk'},
        {'name': 'bark', 'children': [
            {'name': "oooonka", "children": [{"name": "inner\ninner"}]},
            {'name': "doooka"},
        ]},
        {'name': 'zork'}
    ]}
    print(print_tree(a, lambda node: node.get("name"),
                     lambda node: node.get("children") or []))
    # =>
    # foo
    # |-oi
    # | nk
    # |-bark
    # | |-oooonka
    # | | \-inner
    # | |   inner
    # | \-doooka
    # \-zork

def example2():
    b = {"foo": 23, "bar": 24, "baz": {"zork": 99}}
    print(
        print_tree(("root", b),
                   lambda item: item[0] if isinstance(item[1], dict) else "{}: {}".format(*item),
                   lambda item: item[1].items() if isinstance(item[1], dict) else []))
    # =>
    # root
    # |-foo: 23
    # |-bar: 24
    # \-baz
    #   \-zork: 99




# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-
# pretty printing
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def print_obj(obj, max_depth=math.inf):
    return PPrinter().print(obj, max_depth)

class PPrinter():

    def __init__(self,
                 ignore_internal_attrs=False,
                 max_line_length=50,
                 indent="  "):
        self.ignore_internal_attrs = ignore_internal_attrs
        self.max_line_length = max_line_length
        self.indent = indent

    def __getattr__(self, name):
        if name.startswith("stringify_"):
            return self.stringify_generic
        raise NameError("name '{}' is not defined".format(name))

    def stringify_primitive(self, obj, max_depth, depth):
        return "{}".format(obj)

    def stringify_str(self, string, max_depth, depth):
        return pprint.saferepr(string)

    def stringify_generic(self, obj, max_depth, depth):
        if depth == max_depth:
            return str(obj)

        return "{} {}".format(
            obj,
            self.__stringify_dict_items__(obj.__dict__, max_depth, depth, False))

    def __stringify_dict_items__(self, dict, max_depth, depth, real_dict=True):
        if depth == max_depth:
            return "{...}"

        members = list(dict.items())
        members_stringified = []
        current_max_line_length = self.max_line_length if len(members) < 5 else 0
        rows = [[]]
        current_row = rows[0]
        row_length = 0

        for k, v in members:
            if (self.ignore_internal_attrs and k.startswith("__")):
                continue
            val_string = self.stringify(v, max_depth, depth + 1)
            key_string = "'{}'".format(k) if real_dict else k
            string = "{}: {}".format(key_string, val_string)
            if (len(current_row) > 0 and (row_length + len(string) > current_max_line_length or "\n" in string)):
                current_row = []
                row_length = 0
                rows.append(current_row)
            current_row.append(string)
            row_length += len(string)

        members_stringified = list(map(lambda row: ", ".join(row), rows))
        before_indent = ""
        after_indent = ""
        if len(rows) > 1 or row_length > current_max_line_length:
            members_stringified = map(lambda ea: self.indent * depth + ea, members_stringified)
            before_indent = "\n"
            after_indent = "\n" + self.indent * (depth - 1)

        return "{{{}{}{}}}".format(
            before_indent,
            ",\n".join(members_stringified),
            after_indent)

    def stringify_iterable(self, iterable, max_depth, depth):
        multi_line = False
        items_stringified = []
        stringified_len = 0
        for ea in iterable:
            stringified = self.stringify(ea, max_depth, depth + 1)
            stringified_len += len(stringified)
            if (not multi_line and ("\n" in stringified or stringified_len > self.max_line_length)):
                multi_line = True
            items_stringified.append(stringified)
        sep = ",\n{}".format(self.indent * depth) if multi_line else ", "
        before = "\n{}".format(self.indent * depth) if multi_line else ""
        after = "\n{}".format(self.indent * (depth - 1)) if multi_line else ""
        return "[{}{}{}]".format(before, sep.join(items_stringified), after)

    def stringify(self, obj, max_depth=math.inf, depth=1):
        if depth > max_depth:
            return "..."
        if not hasattr(obj, "__dict__"):
            if isinstance(obj, str):
                return self.stringify_str(obj, max_depth, depth)
            if isinstance(obj, dict):
                return self.__stringify_dict_items__(obj, max_depth, depth, True)
            if isinstance(obj, Iterable):
                return self.stringify_iterable(obj, max_depth, depth)
            return self.stringify_primitive(obj, max_depth, depth)
        return getattr(self, "stringify_" + type(obj).__name__)(obj, max_depth, depth)

    def print(self, obj, max_depth):
        return print(self.stringify(obj, max_depth))
