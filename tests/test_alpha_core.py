import subprocess
import sys


def test_alpha_boot_runs_and_exits():
    result = subprocess.run(
        [sys.executable, "app.py", "alpha"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    assert "mode=alpha" in result.stdout
    assert "Services:" in result.stdout
    assert "Plugins enabled:" in result.stdout


def test_alpha_crawl_flag_triggers_crawl_path():
    result = subprocess.run(
        [sys.executable, "app.py", "alpha", "--crawl"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0
    assert "Starting full crawl" in result.stdout
