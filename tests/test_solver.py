# ruff: noqa: PLR2004

import dataclasses

import pytest

from cp2077solver.solver import CodeMatrix
from cp2077solver.solver import GameSpecification
from cp2077solver.solver import Solution
from cp2077solver.solver import SolutionStep
from cp2077solver.solver import SolutionStrategy
from cp2077solver.solver import UploadSequence
from cp2077solver.solver import solve


def assert_solution_fits_spec(solution: Solution, spec: GameSpecification):
    """Check that the solution is valid and fits the game specification."""
    # Check that all cells are unique.
    assert len(set(solution.steps)) == len(solution.steps)

    # Check each step.
    for step_idx, step in enumerate(solution.steps):
        # Check that the cell value in the code matrix matches the step value.
        assert spec.code_matrix[step.row_idx, step.col_idx] == step.value

        # Check that the solution is alternating between rows and columns at each step.
        if step_idx > 0:
            if step_idx % 2 == 0:
                assert solution.steps[step_idx].row_idx == solution.steps[step_idx - 1].row_idx
            else:
                assert solution.steps[step_idx].col_idx == solution.steps[step_idx - 1].col_idx

    # Check that the solution actually completes the upload sequences.
    stringified_sequences = [
        ",".join(str(cell) for cell in sequence.cells) for sequence in spec.upload_sequences
    ]
    stringified_solution = ",".join(str(step.value) for step in solution.steps)

    assert all(
        stringified_sequence in stringified_solution
        for stringified_sequence in stringified_sequences
    )


def test_solve_single_sequence_easy_matrix():
    # A simple code matrix where there is only one possible solution.
    spec = GameSpecification(
        code_matrix=CodeMatrix(
            cells=[
                ["BD", "55"],
                ["E9", "1C"],
            ],
        ),
        upload_sequences=[
            UploadSequence(["55", "1C"], priority=1),
        ],
        buffer_size=2,
    )
    solutions = solve(spec)

    assert len(solutions) == 1
    assert solutions[0] == Solution(
        steps=[
            SolutionStep(value="55", row_idx=0, col_idx=1),
            SolutionStep(value="1C", row_idx=1, col_idx=1),
        ],
    )
    assert_solution_fits_spec(solutions[0], spec)


def test_no_solutions():
    # A simple code matrix where there are no possible solutions.
    spec = GameSpecification(
        code_matrix=CodeMatrix(
            cells=[
                ["BD", "55"],
                ["E9", "1C"],
            ],
        ),
        upload_sequences=[
            UploadSequence(["7A", "1C"], priority=1),
        ],
        buffer_size=2,
    )
    solutions = solve(spec)
    assert solutions == []


def test_solve_single_sequence_easy_matrix_multiple_solutions():
    # A simple code matrix where there are multiple solutions.
    spec = GameSpecification(
        code_matrix=CodeMatrix(
            cells=[
                ["1C", "55"],
                ["55", "1C"],
            ],
        ),
        upload_sequences=[
            UploadSequence(["55", "1C"], priority=1),
        ],
        buffer_size=3,
    )
    solutions = solve(spec, strategy=SolutionStrategy.FIND_ALL_SOLUTIONS)
    assert len(solutions) == 2

    for solution in solutions:
        assert_solution_fits_spec(solution, spec)


def test_solve_one_unique_cell_value():
    # The same cell value everywhere.
    spec = GameSpecification(
        code_matrix=CodeMatrix(
            cells=[
                ["55", "55", "55"],
                ["55", "55", "55"],
                ["55", "55", "55"],
            ],
        ),
        upload_sequences=[
            UploadSequence(["55", "55", "55"], priority=1),
        ],
        buffer_size=3,
    )
    solutions = solve(spec, strategy=SolutionStrategy.FIND_ALL_SOLUTIONS)
    assert len(solutions) == 12

    for solution in solutions:
        assert_solution_fits_spec(solution, spec)


def test_solve_must_consume_irrelevant_cells_in_the_beginning():
    # The solution paths contain irrelevant values: must consume "wrong" cells in the beginning.
    spec = GameSpecification(
        code_matrix=CodeMatrix(
            cells=[
                ["BD", "7A", "C8"],
                ["1C", "55", "55"],
                ["55", "E9", "1C"],
            ],
        ),
        upload_sequences=[
            UploadSequence(["55", "1C"], priority=1),
        ],
        buffer_size=3,
    )
    solutions = solve(spec, strategy=SolutionStrategy.FIND_ALL_SOLUTIONS)
    assert len(solutions) == 3

    for solution in solutions:
        assert_solution_fits_spec(solution, spec)


def test_solve_must_consume_irrelevant_cells_in_the_middle():
    # A single solution that fits all upload sequences.
    # The solution path contains irrelevant values: must consume "wrong" cells in the middle.
    spec = GameSpecification(
        code_matrix=CodeMatrix(
            cells=[
                ["BD", "7A", "7A", "FF"],
                ["1C", "55", "55", "FF"],
                ["55", "E9", "1C", "FF"],
                ["C8", "C8", "7A", "FF"],
            ],
        ),
        upload_sequences=[
            UploadSequence(["BD", "55"], priority=1),
            UploadSequence(["C8", "1C", "55"], priority=2),
            UploadSequence(["55", "E9", "FF"], priority=3),
        ],
        buffer_size=9,
    )
    solutions = solve(spec, strategy=SolutionStrategy.FIND_ALL_SOLUTIONS)
    assert len(solutions) == 1

    expected_solution = Solution(
        steps=[
            SolutionStep(value="BD", row_idx=0, col_idx=0),
            SolutionStep(value="55", row_idx=2, col_idx=0),
            SolutionStep(value="1C", row_idx=2, col_idx=2),  # "wrong" cell
            SolutionStep(value="7A", row_idx=3, col_idx=2),  # "wrong" cell
            SolutionStep(value="C8", row_idx=3, col_idx=0),
            SolutionStep(value="1C", row_idx=1, col_idx=0),
            SolutionStep(value="55", row_idx=1, col_idx=1),
            SolutionStep(value="E9", row_idx=2, col_idx=1),
            SolutionStep(value="FF", row_idx=2, col_idx=3),
        ]
    )

    assert_solution_fits_spec(solutions[0], spec)
    assert solutions[0] == expected_solution


def test_solve_partial_must_discard_lower_priorities():
    # A real-life case where there are no solutions that satisfy all sequences,
    # and we must discard the first two sequences and solve for the remaining two.
    spec = GameSpecification(
        code_matrix=CodeMatrix(
            cells=[
                ["1C", "BD", "55", "E9", "55"],
                ["1C", "BD", "1C", "55", "E9"],
                ["55", "E9", "E9", "BD", "BD"],
                ["55", "FF", "FF", "1C", "1C"],
                ["FF", "E9", "1C", "BD", "FF"],
            ],
        ),
        upload_sequences=[
            UploadSequence(["1C", "1C", "55"], priority=1),
            UploadSequence(["55", "FF", "1C"], priority=2),
            UploadSequence(["BD", "E9", "BD", "55"], priority=3),
            UploadSequence(["55", "1C", "FF", "BD"], priority=4),
        ],
        buffer_size=8,
    )

    solutions = solve(spec, strategy=SolutionStrategy.FIND_FIRST_SOLUTION)

    with pytest.raises(AssertionError):
        assert_solution_fits_spec(solutions[0], spec)

    reduced_spec = dataclasses.replace(spec, upload_sequences=spec.upload_sequences[2:])
    assert_solution_fits_spec(solutions[0], reduced_spec)
