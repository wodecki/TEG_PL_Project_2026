"""Wspólny mechanizm programów sprawdzających (src/check.py) we wszystkich miniprojektach.
Gotowy plik: nie edytujesz go."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path


class Checker:
    """Zbiera wiersze PASS/FAIL i wypisuje podsumowanie."""

    def __init__(self, title: str):
        self.results: list[bool] = []
        print(f"=== {title} ===\n")

    def check(self, name: str, passed: bool, detail: str = "") -> bool:
        self.results.append(bool(passed))
        print(f"[{'PASS' if passed else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
        return bool(passed)

    @property
    def all_passed(self) -> bool:
        return bool(self.results) and all(self.results)

    def summary(self) -> None:
        print(f"\nSUMMARY: zaliczone sprawdzenia: {sum(self.results)}/{len(self.results)}")
        if not self.all_passed:
            print("Popraw pierwszy wiersz FAIL powyżej i uruchom sprawdzanie jeszcze raz.")


def unimplemented_functions(path: Path) -> list[str]:
    """Nazwy funkcji w `path`, których treść nadal zgłasza NotImplementedError."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.Raise) and sub.exc is not None:
                    target = sub.exc.func if isinstance(sub.exc, ast.Call) else sub.exc
                    if isinstance(target, ast.Name) and target.id == "NotImplementedError":
                        names.append(node.name)
                        break
    return names


def run_pytest(test_path: Path, cwd: Path) -> tuple[bool, str]:
    """Uruchamia pytest na jednym pliku lub folderze; zwraca (czy przeszło, ostatni wiersz podsumowania pytest)."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "--color=no", "-p", "no:cacheprovider", str(test_path)],
        cwd=cwd, capture_output=True, text=True,
    )
    lines = [line for line in proc.stdout.strip().splitlines() if re.search(r"\d+ (passed|failed|error)", line)]
    return proc.returncode == 0, (lines[-1].strip("= ") if lines else "nie uruchomiono żadnego testu")


def run_script(script: Path, cwd: Path) -> tuple[bool, str]:
    """Uruchamia skrypt Pythona; zwraca (czy kod wyjścia to 0, ostatni wiersz stderr)."""
    proc = subprocess.run([sys.executable, str(script)], cwd=cwd, capture_output=True, text=True)
    return proc.returncode == 0, (proc.stderr.strip().splitlines() or [""])[-1]

