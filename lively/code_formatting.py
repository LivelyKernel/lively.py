from yapf.yapflib.yapf_api import FormatCode

# see https://github.com/google/yapf


def code_format(source, lines=None, file="<formatted>", config=None):
    formatted_code, success = FormatCode(source,
                                         filename=file,
                                         style_config=config,
                                         lines=lines)
    return formatted_code
