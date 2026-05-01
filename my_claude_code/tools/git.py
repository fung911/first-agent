from .bash import run_bash

def git_status():
    return run_bash("git status --short")

def git_diff(file=None):
    cmd = f"git diff {file}" if file else "git diff"
    return run_bash(cmd)

def git_log(n=10):
    return run_bash(f"git log --oneline -{n}")

def git_commit(message):
    run_bash("git add -A")
    return run_bash(f'git commit -m "{message}"')
