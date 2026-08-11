---
name: reference_python_football_tracker
description: Python interpreter location + football-tracker standalone project
metadata: 
  node_type: memory
  type: reference
  originSessionId: 0d70d18f-c8cf-43f3-858d-a05290f7def8
---

**Python:** No Python on PATH (only Windows Store stubs). Real interpreter installed via winget at:
`C:\Users\malliar\AppData\Local\Programs\Python\Python312\python.exe` (3.12.10). Invoke it by full path. To run modules/pytest, `Set-Location` to the project dir first.

**football-tracker:** standalone computer-vision project at `C:\Users\malliar\Desktop\football-tracker` — live football "who's who" overlay (detect/track players + ball, team color, jersey number→name, possession, actions). Logic core is testable without GPU/weights via a synthetic match harness. **43 tests pass.** Pushed to `github.com/MrArun005/LiveStreamingFootBall` (branch main). Real detection backend uses YOLO (untested — needs GPU + clip). `live` command for streams not yet built; using highlight clips for now (DRM blocks tapping JioHotstar etc.).
