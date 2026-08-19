# Claude Code on Windows / PowerShell

Use this when the user is in PowerShell or Windows Terminal.

## Correct launch forms

- Change directory and launch Claude:
  ```powershell
  Set-Location 'G:\My Drive\beast'
  claude
  ```

- One-liner form:
  ```powershell
  Set-Location 'G:\My Drive\beast'; claude
  ```

## Pitfall

- `&&` is Bash syntax, not PowerShell statement chaining.
- If the user is in PowerShell, do not give Linux shell commands like `cd /opt/... && claude` unless you explicitly say they must run it inside WSL.

## WSL vs Windows

- Linux paths such as `/opt/data/...` are only valid inside WSL/Linux shells.
- Windows paths like `G:\My Drive\beast` are valid in PowerShell and Windows Terminal.
- If the task requires a Linux path, either:
  - open WSL first, or
  - tell the user the command is for a Linux shell, not PowerShell.
