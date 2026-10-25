"""Run from the project virtual environment on Windows to build an onedir bundle."""

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("Build the Windows distribution on Windows.")
    if sys.prefix == sys.base_prefix:
        raise SystemExit("Run with .venv\\Scripts\\python.exe scripts\\build_windows.py")
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    subprocess.run([sys.executable, "-m", "pytest", "-q"], check=True)
    import PyInstaller.__main__

    PyInstaller.__main__.run(
        [
            "--noconfirm",
            "--clean",
            "--windowed",
            "--onedir",
            "--name",
            "SkinFlow",
            "--paths",
            str(root / "src"),
            "--collect-all",
            "skinflow",
            "--collect-submodules",
            "alembic",
            str(root / "scripts" / "run_skinflow.py"),
        ]
    )


if __name__ == "__main__":
    main()
