"""Paths for both source checkout and future frozen Windows distributions."""
import os
import sys
from pathlib import Path


def application_dir():
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent


def resource_dir():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


def data_dir():
    # Preserve the existing local application's data; never put runtime state in Git.
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    return base / 'FluxStorage'


def system_dir():
    return Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32'
