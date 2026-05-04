import os
import sys
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT_PATH = ROOT / "project"

REQUIRED_FOLDERS = [
    PROJECT_PATH,
    PROJECT_PATH / "app",
    PROJECT_PATH / "data",
    PROJECT_PATH / "core",
    PROJECT_PATH / "visual",
]

REQUIRED_FILES = [
    PROJECT_PATH / "__init__.py",
    PROJECT_PATH / "app" / "__init__.py",
    PROJECT_PATH / "data" / "__init__.py",
    PROJECT_PATH / "core" / "__init__.py",
    PROJECT_PATH / "visual" / "__init__.py",
]

REQUIRED_DEPENDENCIES = [
    "yfinance",
    "pandas",
    "numpy",
    "plotly",
    "streamlit",
    "sklearn",
]


def check_root_directory():
    print("\n=== CHECK 1: Are you running from correct ROOT? ===")
    print(f"Current working directory:\n  {os.getcwd()}")
    print(f"Project root should be:\n  {ROOT}")

    if str(ROOT) != os.getcwd():
        print("❌ ERROR: You are NOT running from TrendProject root folder!")
        print("➡ FIX: Run this command first:")
        print(f"cd {ROOT}")
    else:
        print("✔ OK: You are in the correct project root.")


def check_folders():
    print("\n=== CHECK 2: Required folders exist ===")
    for folder in REQUIRED_FOLDERS:
        if not folder.exists():
            print(f" MISSING FOLDER: {folder}")
        else:
            print(f" Found folder: {folder}")


def check_init_files():
    print("\n=== CHECK 3: __init__.py files ===")
    for file in REQUIRED_FILES:
        if not file.exists():
            print(f" MISSING __init__.py: {file}")
        else:
            print(f" Found __init__.py: {file}")


def check_python_path():
    print("\n=== CHECK 4: Python search path ===")
    for p in sys.path:
        print(" -", p)

    if str(ROOT) not in sys.path:
        print("\n ERROR: Project root NOT in Python path!")
        print("➡ FIX: Add this before running Streamlit:\n")
        print(f"export PYTHONPATH={ROOT}   # mac/linux")
        print(f"set PYTHONPATH={ROOT}      # windows")
    else:
        print("\n✔ OK: Root folder is in Python path.")


def check_imports():
    print("\n=== CHECK 5: Import test ===")

    modules_to_test = [
        "project",
        "project.data.collector",
        "project.data.processor",
        "project.core.trend_detector",
        "project.visual.charts",
        "project.app.dashboard",
    ]

    for module in modules_to_test:
        try:
            importlib.import_module(module)
            print(f"✔ Import OK: {module}")
        except Exception as e:
            print(f" Import FAILED: {module}")
            print("  Reason:", e)


def check_dependencies():
    print("\n=== CHECK 6: Dependency availability ===")
    for dep in REQUIRED_DEPENDENCIES:
        try:
            importlib.import_module(dep)
            print(f"✔ Found {dep}")
        except ImportError:
            print(f" MISSING {dep}")
            print(f"➡ Run: pip install {dep}")


def summary():
    print("\n\n==================== FINAL SUMMARY ====================")
    print("If ANY  appears above, fix it and re-run validator.")
    print("When everything is ✔, Streamlit will work 100%.\n")
    print("To run app:")
    print("streamlit run project/app/dashboard.py")
    print("========================================================\n")


if __name__ == "__main__":
    print("===== PROJECT VALIDATOR RUNNING =====")
    check_root_directory()
    check_folders()
    check_init_files()
    check_python_path()
    check_imports()
    check_dependencies()
    summary()

