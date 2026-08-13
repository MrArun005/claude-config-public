# Clone PlumbingApp to Desktop

## Context
Arun wants the GitHub repo https://github.com/MrArun005/PlumbingApp cloned onto the Desktop (same place as other side projects like `amusement-park` and the football tracker).

## Steps
1. Check `C:\Users\malliar\Desktop\PlumbingApp` doesn't already exist (if it does, report and stop).
2. `git clone https://github.com/MrArun005/PlumbingApp "C:\Users\malliar\Desktop\PlumbingApp"`
3. Inspect the cloned repo (README, package.json or equivalent) to identify the stack and report what it is.
4. If it's a Node project, note the install/run commands but don't install dependencies unless asked.

## Verification
- `git -C C:\Users\malliar\Desktop\PlumbingApp log --oneline -3` shows commits, confirming a successful clone.
