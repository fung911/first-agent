import subprocess
import os

def read_file(path):
    if os.path.isdir(path):
        return f"[提示] {path} 是目录，请用 list_tree 查看结构，或指定具体文件"
    try:
        lines = open(path, encoding="utf-8").readlines()
        return "".join(f"{i+1:3}: {l}" for i, l in enumerate(lines))
    except FileNotFoundError:
        return f"[错误] 文件不存在: {path}"

def write_file(path, content):
    dirpath = os.path.dirname(path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"已写入: {path} ({len(content.splitlines())} 行)"

def edit_file(path, old_str, new_str):
    try:
        content = open(path, encoding="utf-8").read()
        if old_str not in content:
            return "[错误] 找不到要替换的内容，请确认 old_str 和文件完全一致"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.replace(old_str, new_str, 1))
        return f"已修改: {path}"
    except FileNotFoundError:
        return f"[错误] 文件不存在: {path}"

def mkdir(path):
    os.makedirs(path, exist_ok=True)
    return f"已创建目录: {path}"

def list_tree(path="."):
    """显示目录树结构（只显示路径，不显示内容）"""
    result = []
    for root, dirs, files in os.walk(path):
        # 跳过 node_modules、__pycache__ 等噪音目录
        dirs[:] = [d for d in dirs if d not in
                   ("node_modules", "__pycache__", ".git", "dist", ".venv", "venv")]
        level = root.replace(path, "").count(os.sep)
        indent = "  " * level
        result.append(f"{indent}{os.path.basename(root)}/")
        for f in files:
            result.append(f"{indent}  {f}")
    return "\n".join(result) if result else "(空目录)"

def run_bash(command, cwd=None):
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True,
            text=True, timeout=60, cwd=cwd
        )
        out = result.stdout
        if result.stderr:
            out += f"\n[stderr]\n{result.stderr}"
        return out.strip() or "(无输出)"
    except subprocess.TimeoutExpired:
        return "[错误] 命令超时（60s）"

def dispatch(name, inputs):
    if name == "read_file":  return read_file(inputs["path"])
    if name == "write_file": return write_file(inputs["path"], inputs["content"])
    if name == "edit_file":  return edit_file(inputs["path"], inputs["old_str"], inputs["new_str"])
    if name == "mkdir":      return mkdir(inputs["path"])
    if name == "list_tree":  return list_tree(inputs.get("path", "."))
    if name == "run_bash":   return run_bash(inputs["command"], inputs.get("cwd"))
    return f"[错误] 未知工具: {name}"
