import subprocess
subprocess.Popen(['powershell', '-Command', "Start-Process 'notepad'"], creationflags=subprocess.CREATE_NO_WINDOW)
