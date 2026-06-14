import marshal, dis, types

def show_code(code, indent=0):
    prefix = '  ' * indent
    print(f'{prefix}def {code.co_name}({", ".join(code.co_varnames[:code.co_argcount])})')
    # Print large string constants in this function
    for c in code.co_consts:
        if isinstance(c, str) and len(c) > 50:
            print(f'{prefix}  [String, len={len(c)}]')
            print(f'{prefix}  {c[:300].replace(chr(10), " ")}')
        elif isinstance(c, types.CodeType):
            show_code(c, indent + 1)

with open('main_fixed.pyc', 'rb') as f:
    f.read(16)
    code = marshal.load(f)

show_code(code)
