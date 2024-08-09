#!/usr/bin/env python3

import argparse
import time

from cp2077solver.solver import CodeMatrix
from cp2077solver.solver import GameSpecification
from cp2077solver.solver import Solution
from cp2077solver.solver import SolutionStep
from cp2077solver.solver import SolutionStrategy
from cp2077solver.solver import UploadSequence
from cp2077solver.solver import solve

# The maximum number of solutions to print when using the `FIND_ALL_SOLUTIONS` strategy.
MAX_PRINTABLE_SOLUTIONS = 10_000


def print_solution(code_matrix: CodeMatrix, solution: Solution) -> None:
    """Print the code matrix marked up with the solution path."""
    print(f"Solution: {' '.join(step.value for step in solution.steps)}")
    print(f"Path: {' > '.join(f'({step.row_idx} {step.col_idx})' for step in solution.steps)}")

    for row_idx in range(code_matrix.size):
        for col_idx, value in code_matrix.iterate_row(row_idx):
            try:
                matching_step_idx = solution.steps.index(SolutionStep(value, row_idx, col_idx))
                formatted_step_idx = f"({matching_step_idx + 1})".ljust(6)
                formatted_value = f"{value} {formatted_step_idx}"
            except ValueError:
                formatted_value = f"{value: <9}"

            print(formatted_value, end="")

        print()
    print()


def solve_file(filename: str, strategy: SolutionStrategy) -> None:
    """
    Solve the minigame specified in the given file.

    Parameters
    ----------
    filename
        The name of the file containing the minigame data.
    strategy
        The solution strategy to use.
        See also: SolutionStrategy.
    """
    with open(filename) as f:
        lines = f.readlines()

    # Parse the lines in the file and organize the data into a GameSpecification object.
    buffer_size = int(lines[0])
    matrix_size = int(lines[1])
    upload_sequence_count = int(lines[2])

    matrix_lines = lines[3 : 3 + matrix_size]
    code_matrix = CodeMatrix(cells=[line.split() for line in matrix_lines])

    upload_sequence_lines = lines[3 + matrix_size : 3 + matrix_size + upload_sequence_count]
    upload_sequences = []
    for idx, line in enumerate(upload_sequence_lines):
        upload_sequences.append(UploadSequence(cells=line.split(), priority=idx + 1))

    spec = GameSpecification(
        code_matrix=code_matrix,
        upload_sequences=upload_sequences,
        buffer_size=buffer_size,
    )

    # Solve, then print the solutions.
    start_time = time.perf_counter()
    solutions = solve(spec=spec, strategy=strategy)
    end_time = time.perf_counter()

    for solution in solutions[:MAX_PRINTABLE_SOLUTIONS]:
        print_solution(code_matrix, solution)

    print(f"Found {len(solutions)} solutions in {end_time - start_time:.3f} seconds")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLI for solving the Breach Protocol minigame in Cyberpunk 2077.",
    )
    parser.add_argument(
        "filename",
        type=str,
        help="The name of the file with the minigame data.",
    )
    parser.add_argument(
        "--all-solutions",
        action="store_const",
        const=SolutionStrategy.FIND_ALL_SOLUTIONS,
        default=SolutionStrategy.FIND_FIRST_SOLUTION,
        help="Optional. If specified, find all solutions instead of the first matching one.",
    )

    args = parser.parse_args()
    return solve_file(filename=args.filename, strategy=args.all_solutions)


if __name__ == "__main__":
    main()
