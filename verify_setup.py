#!/usr/bin/env python3
"""Verify Claude Code Chatbot setup."""
import sys
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.11+."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        return False, f"Python {version.major}.{version.minor} (need 3.11+)"
    return True, f"Python {version.major}.{version.minor}.{version.micro}"

def check_file_exists(file_path):
    """Check if a file exists."""
    return Path(file_path).exists()

def check_env_file():
    """Check if .env file exists and has API key."""
    if not check_file_exists(".env"):
        return False, ".env file not found (copy from .env.example)"

    try:
        with open(".env") as f:
            content = f.read()
            if "CLAUDE_API_KEY=" in content and "your_claude_api_key_here" not in content:
                return True, ".env file configured"
            else:
                return False, ".env file exists but API key not set"
    except Exception as e:
        return False, f"Error reading .env: {e}"

def check_dependencies():
    """Check if key dependencies are installed."""
    try:
        import fastapi
        import anthropic
        import streamlit
        import sqlalchemy
        return True, "Key dependencies installed"
    except ImportError as e:
        return False, f"Missing dependency: {e.name}"

def main():
    """Run setup verification."""
    print("🔍 Claude Code Chatbot - Setup Verification\n")
    print("=" * 50)

    checks = [
        ("Python Version", check_python_version),
        ("Backend directory", lambda: (check_file_exists("backend"), "backend/ found")),
        ("Frontend directory", lambda: (check_file_exists("frontend"), "frontend/ found")),
        ("Backend requirements", lambda: (check_file_exists("backend/requirements.txt"), "Found")),
        ("Frontend requirements", lambda: (check_file_exists("frontend/requirements.txt"), "Found")),
        ("Environment file", check_env_file),
        ("Dependencies", check_dependencies),
    ]

    all_passed = True

    for name, check_func in checks:
        try:
            passed, message = check_func()
            status = "✅" if passed else "❌"
            print(f"{status} {name:25} {message}")
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"❌ {name:25} Error: {e}")
            all_passed = False

    print("=" * 50)

    if all_passed:
        print("\n✅ Setup verification passed!")
        print("\nNext steps:")
        print("1. Run start.bat (Windows) or ./start.sh (Linux/Mac)")
        print("2. Open http://localhost:8501 in your browser")
        print("3. Start chatting with Claude!")
    else:
        print("\n❌ Setup verification failed!")
        print("\nTo fix:")
        print("1. Install Python 3.11+")
        print("2. Copy .env.example to .env")
        print("3. Add your Claude API key to .env")
        print("4. Run: pip install -r backend/requirements.txt")
        print("5. Run: pip install -r frontend/requirements.txt")
        print("\nThen run this script again.")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
