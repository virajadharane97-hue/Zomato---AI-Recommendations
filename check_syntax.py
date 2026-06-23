import ast
import sys

files = [
    'src/api/schemas.py',
    'src/api/routes.py',
    'src/main.py',
    'src/ui/cli.py',
    'src/ui/streamlit_app.py',
]

ok = True
for f in files:
    try:
        with open(f, encoding='utf-8') as fh:
            ast.parse(fh.read())
        print(f"  OK: {f}")
    except SyntaxError as e:
        print(f"  FAIL: {f} -> {e}")
        ok = False

if ok:
    print("\nAll files parse OK")
else:
    print("\nSome files have syntax errors")
    sys.exit(1)
