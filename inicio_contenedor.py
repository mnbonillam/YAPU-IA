"""Prepara el volumen montado y ejecuta Yapu con el usuario del servicio."""
import os
import pwd
import sys
from pathlib import Path

if __name__ == "__main__":
    if os.getuid() == 0:
        user = pwd.getpwnam("yapu")
        storage = Path(os.environ["YAPU_DATA"])
        storage.mkdir(parents=True, exist_ok=True)
        os.chown(storage, user.pw_uid, user.pw_gid)
        os.initgroups(user.pw_name, user.pw_gid)
        os.setgid(user.pw_gid)
        os.setuid(user.pw_uid)
    os.execv(sys.executable, [sys.executable, "-u", "app.py"])
