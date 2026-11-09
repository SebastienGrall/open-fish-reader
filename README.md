# Open Fish Reader

Socle V0.1 du logiciel de dépouillement des vidéos Open Fish Counter.

## Windows PowerShell

```powershell
cd open-fish-reader
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
python -m open_fish_reader
```

Tests :

```powershell
pytest
ruff check .
```
