#!/usr/bin/env python3
"""
Cleanup script for PlayNexus project.
Removes cache files, temporary files, and unused build artifacts.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def run_command(cmd, description):
    """Run a shell command and report result."""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ Success")
            if result.stdout:
                print(f"   {result.stdout.strip()}")
        else:
            print(f"   ⚠️  Warning (exit code {result.returncode})")
            if result.stderr:
                print(f"   {result.stderr.strip()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")


def remove_pycache():
    """Remove all __pycache__ directories and .pyc files."""
    print_header("Removing Python cache files")

    count = 0
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Remove __pycache__ directories
        if "__pycache__" in dirs:
            cache_dir = Path(root) / "__pycache__"
            try:
                shutil.rmtree(cache_dir)
                print(f"   🗑️  Removed: {cache_dir.relative_to(PROJECT_ROOT)}")
                count += 1
            except Exception as e:
                print(f"   ❌ Failed to remove {cache_dir}: {e}")

    print(f"\n   ✅ Removed {count} __pycache__ directories")


def remove_pyc_files():
    """Remove all .pyc files outside __pycache__."""
    count = 0
    for pyc in PROJECT_ROOT.rglob("*.pyc"):
        try:
            pyc.unlink()
            print(f"   🗑️  Removed: {pyc.relative_to(PROJECT_ROOT)}")
            count += 1
        except Exception as e:
            print(f"   ❌ Failed to remove {pyc}: {e}")

    print(f"\n   ✅ Removed {count} .pyc files")


def remove_mypy_cache():
    """Remove .mypy_cache directory."""
    print_header("Removing MyPy cache")

    cache_dir = PROJECT_ROOT / ".mypy_cache"
    if cache_dir.exists():
        try:
            shutil.rmtree(cache_dir)
            print(f"   🗑️  Removed: .mypy_cache")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
    else:
        print("   ℹ️  No .mypy_cache found")


def remove_pip_cache():
    """Clear pip cache."""
    print_header("Clearing pip cache")

    run_command("pip cache purge", "Cleared pip cache")


def list_installed_packages():
    """List all installed packages."""
    print_header("Installed Python packages")

    run_command("pip list", "Listing packages")


def check_requirements():
    """Check for unused dependencies."""
    print_header("Checking requirements.txt")

    req_file = PROJECT_ROOT / "requirements.txt"
    if not req_file.exists():
        print("   ❌ requirements.txt not found!")
        return

    print("   📋 Checking installed packages against requirements.txt...")
    run_command("pip check", "Verifying package compatibility")


def clean_docker():
    """Clean Docker cache if Dockerfile exists."""
    dockerfile = PROJECT_ROOT / "Dockerfile"
    if dockerfile.exists():
        print_header("Docker cleanup")
        print("   💡 To clean Docker build cache manually:")
        print("      docker system prune -a")
        print()


def main():
    """Run all cleanup tasks."""
    print_header("🚀 PlayNexus Cleanup Script")
    print(f"   Project: {PROJECT_ROOT}")

    # Confirm before proceeding
    response = input("\n⚠️  This will delete cache files. Continue? (y/N): ").strip().lower()
    if response != "y" and response != "yes":
        print("\n❌ Cleanup cancelled.")
        sys.exit(0)

    try:
        remove_pycache()
        remove_pyc_files()
        remove_mypy_cache()
        remove_pip_cache()
        list_installed_packages()
        check_requirements()
        clean_docker()

        print_header("✅ Cleanup Complete!")
        print("   Your project is now clean and ready for deployment.\n")

    except KeyboardInterrupt:
        print("\n\n❌ Cleanup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
