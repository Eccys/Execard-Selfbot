import ast
import builtins
import json
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


def test_g_py_compiles_without_syntax_warnings_or_undefined_names():
    source = (REPO_DIR / "G.py").read_text(encoding="utf-8")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", SyntaxWarning)
        tree = ast.parse(source, filename="G.py")
    assert [w for w in caught if issubclass(w.category, SyntaxWarning)] == []

    defined = set(dir(builtins)) | {"__file__"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                defined.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                defined.add(alias.asname or alias.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            defined.add(node.id)
        elif isinstance(node, ast.arg):
            defined.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            defined.add(node.name)

    undefined = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in defined:
                undefined.append((node.lineno, node.id))
    assert undefined == [], f"Undefined names: {undefined}"
