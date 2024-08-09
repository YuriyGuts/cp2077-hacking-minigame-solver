from pathlib import Path

import pytest

from cp2077solver.cli import main


@pytest.fixture
def fixtures_path():
    return Path(__file__).parent / "fixtures"


def test_single_solution_filename_only(fixtures_path, monkeypatch, capsys):
    # GIVEN a solvable game spec with a single possible solution
    monkeypatch.setattr("sys.argv", ["cli.py", str(fixtures_path / "easy-single-solution.txt")])

    # WHEN using the CLI with only the filename
    main()

    # THEN it prints the solution to stdout
    captured = capsys.readouterr()
    assert "Solution: 55 1C\n" in captured.out
    assert "Path: (0 1) > (1 1)\n" in captured.out
    assert "Found 1 solutions in " in captured.out


def test_multiple_solutions_find_all(fixtures_path, monkeypatch, capsys):
    # GIVEN a real-life, solvable game spec with multiple possible solutions
    monkeypatch.setattr(
        "sys.argv", ["cli.py", str(fixtures_path / "real-game-1.txt"), "--all-solutions"]
    )

    # WHEN using the CLI and requesting all solutions
    main()

    # THEN it prints all solutions to stdout
    captured = capsys.readouterr()
    assert "Solution: BD E9 55 7A 55\n" in captured.out
    assert "Solution: BD E9 55 1C 7A 55\n" in captured.out
    assert "Found 20 solutions in " in captured.out


def test_partial_solution_find_all(fixtures_path, monkeypatch, capsys):
    # GIVEN a real-life, partially solvable game spec
    # (where not all upload sequences can be completed and lower-priority ones must be discarded)
    monkeypatch.setattr(
        "sys.argv", ["cli.py", str(fixtures_path / "real-game-2.txt"), "--all-solutions"]
    )

    # WHEN using the CLI and requesting all solutions
    main()

    # THEN it prints all solutions to stdout
    captured = capsys.readouterr()
    assert (
        "Warning: Could not find a solution that satisfies all upload sequences. "
        "Discarding all sequences with priority <= 1."
    ) in captured.out
    assert (
        "Warning: Could not find a solution that satisfies all upload sequences. "
        "Discarding all sequences with priority <= 2."
    ) in captured.out

    assert "Solution: E9 BD E9 BD 55 1C FF BD\n" in captured.out
    assert "Path: (0 3) > (2 3) > (2 1) > (0 1) > (0 4) > (3 4) > (3 1) > (1 1)\n" in captured.out
    assert "Found 13 solutions in " in captured.out
