import os
import subprocess

def read_file(path):
    if os.path.isdir(path):
        items = os.listdir(path)
        return f"[目录] {path}: {items}"
    try:
        lines = open(path, encoding="utf-8").readlines()
        return "".join(f"{i+1:4}: {l}" for i, l in enumerate(lines))
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
            return "[错误] 找不到要替换的内容"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.replace(old_str, new_str, 1))
        return f"已修改: {path}"
    except FileNotFoundError:
        return f"[错误] 文件不存在: {path}"

def list_tree(path="."):
    result = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in
                   ("node_modules", "__pycache__", ".git", "dist", ".venv")]
        level = root.replace(path, "").count(os.sep)
        indent = "  " * level
        result.append(f"{indent}{os.path.basename(root)}/")
        for f in files:
            result.append(f"{indent}  {f}")
    return "\n".join(result)

def search_code(keyword, path="."):
    result = subprocess.run(
        ["grep", "-rn", keyword, path,
         "--include=*.py", "--include=*.js", "--include=*.ts",
         "--include=*.vue", "--include=*.go"],
        capture_output=True, text=True
    )
    return result.stdout or f"没有找到 '{keyword}'"
