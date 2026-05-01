import subprocess

# 危险命令关键词，执行前需要用户确认
DANGEROUS = ["rm -rf", "rm -r", "drop table", "truncate", "format",
             "mkfs", "> /dev/", "dd if="]

def is_dangerous(command):
    return any(d in command.lower() for d in DANGEROUS)

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
