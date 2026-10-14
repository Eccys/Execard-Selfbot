import ast
import builtins
import json
import symtable
import warnings
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parent.parent


def test_config_and_launch_bat():
    config = json.loads((REPO_DIR / "config.json").read_text(encoding="utf-8"))
    assert isinstance(config, dict)
    assert "token" in config

    launch_bat = (REPO_DIR / "launch.bat").read_text(encoding="utf-8")
    assert "python G.py" in launch_bat
    assert "Main.py" not in launch_bat


def test_g_py_compiles_without_syntax_warnings_or_undefined_globals():
    source = (REPO_DIR / "G.py").read_text(encoding="utf-8")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", SyntaxWarning)
        tree = ast.parse(source, filename="G.py")
    assert [w for w in caught if issubclass(w.category, SyntaxWarning)] == []

    top = symtable.symtable(source, "G.py", "exec")
    builtin_names = set(dir(builtins)) | {"__file__", "__name__"}
    module_defined = {
        s.get_name()
        for s in top.get_symbols()
        if s.is_assigned() or s.is_imported() or s.is_namespace()
    }

    undefined = []

    def walk(table):
        for s in table.get_symbols():
            name = s.get_name()
            if s.is_global() and not s.is_assigned() and not s.is_imported():
                if name not in module_defined and name not in builtin_names:
                    undefined.append((table.get_name(), table.get_lineno(), name))
        for child in table.get_children():
            walk(child)

    walk(top)
    assert undefined == [], f"Undefined globals in lexical scopes: {undefined}"

    # Verify no top-level function overwrites the module-level `token` config string
    top_func_names = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert "token" not in top_func_names

