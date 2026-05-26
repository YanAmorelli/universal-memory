import ast
from pathlib import Path

MIN_OPEN_ARGS_WITH_MODE = 2

# Explicitly flag functions/methods that write or mutate files.
# For open() or Path.open(), we analyze the mode argument to avoid flagging reads.
MUTATION_FUNCTIONS = {
    "replace",
    "rename",
    "unlink",
    "remove",
    "copy",
    "copy2",
    "move",
    "copyfile",
    "write_text",
    "write_bytes",
}


def test_interface_adapters_do_not_bypass_safe_write_use_case_for_mutations() -> None:
    interface_files = [
        path
        for path in Path("src/universal_memory/interfaces").rglob("*.py")
        if "__pycache__" not in path.parts
    ]

    violations: list[str] = []
    for path in interface_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _call_name(node.func)
                
                # Check for direct mutation calls like write_text, copy, replace, etc.
                if name in MUTATION_FUNCTIONS:
                    violations.append(f"{path}:{node.lineno}:{name}")
                    continue
                
                # Check for open() or Path.open() with write/append modes
                if name == "open":
                    if _is_write_mode_open(node):
                        violations.append(f"{path}:{node.lineno}:open (write/append mode)")

    assert violations == []


def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_write_mode_open(node: ast.Call) -> bool:
    # By default, open() opens in read mode ("r")
    mode = "r"
    
    # Check positional arguments. The mode is typically the second argument: open(file, mode)
    if len(node.args) >= MIN_OPEN_ARGS_WITH_MODE:
        mode_arg = node.args[1]
        if isinstance(mode_arg, ast.Constant) and isinstance(mode_arg.value, str):
            mode = mode_arg.value

    # Check keyword arguments: open(file, mode="w")
    for kw in node.keywords:
        if (
            kw.arg == "mode"
            and isinstance(kw.value, ast.Constant)
            and isinstance(kw.value.value, str)
        ):
            mode = kw.value.value

    # If mode contains w, a, x, or +, it is a mutation write/append
    return any(char in mode for char in "wax+")
