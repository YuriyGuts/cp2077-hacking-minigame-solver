import dataclasses
from collections import deque
from collections.abc import Iterator
from enum import IntEnum
from operator import itemgetter

# We could convert the values to integers internally, but it has a negligible impact on performance.
CellValueType = str


@dataclasses.dataclass(frozen=True)
class CodeMatrix:
    """The square matrix of codes to find the upload sequences in."""

    # The values of the cells in row-first order.
    cells: list[list[CellValueType]]

    def __getitem__(self, coords: tuple[int, int]) -> CellValueType:
        return self.cells[coords[0]][coords[1]]

    @property
    def size(self) -> int:
        return len(self.cells)

    def iterate_row(self, row_idx: int) -> Iterator[tuple[int, CellValueType]]:
        return enumerate(self.cells[row_idx])

    def iterate_col(self, col_idx: int) -> Iterator[tuple[int, CellValueType]]:
        return enumerate(row[col_idx] for row in self.cells)


@dataclasses.dataclass(frozen=True)
class UploadSequence:
    """A single "upload sequence" of codes that unlocks a reward when found in the code matrix."""

    # The values of cells in the upload sequence.
    cells: list[CellValueType]

    # The priority of this upload sequence.
    # E.g., lower value = "Basic Datamine", higher = "Advanced Datamine".
    priority: int

    def __getitem__(self, idx: int) -> CellValueType:
        return self.cells[idx]

    def __len__(self) -> int:
        return len(self.cells)


@dataclasses.dataclass(frozen=True)
class GameSpecification:
    """The full specification of the hacking minigame."""

    # Where to find the sequences.
    code_matrix: CodeMatrix

    # What sequences to find.
    upload_sequences: list[UploadSequence]

    # How long the input buffer is.
    buffer_size: int


@dataclasses.dataclass(frozen=True)
class SolutionStep:
    """A single step in the solution path."""

    # The cell value this step adds to the input buffer.
    value: CellValueType

    # The index of the row in the code matrix.
    row_idx: int

    # The index of the column in the code matrix.
    col_idx: int


@dataclasses.dataclass(frozen=True)
class Solution:
    """A single solution path that satisfies the game specification."""

    steps: list[SolutionStep]


class SolutionStrategy(IntEnum):
    """Specifies how to solve the hacking minigame."""

    # Stop when the first solution path is found (regardless of its length).
    # Extremely fast, but can produce paths that are longer than necessary.
    FIND_FIRST_SOLUTION = 0

    # Find all possible solution paths and sort them by length (from shortest to longest).
    # Still fast for the instances that realistically occur in the game,
    # but slow for theoretical, larger problem sizes.
    FIND_ALL_SOLUTIONS = 1


class CellChoiceDirection(IntEnum):
    """Specifies whether the next step in the path should pick cells from the row or the column."""

    ROW = 0
    COLUMN = 1


@dataclasses.dataclass
class SearchStackItem:
    """A single item in the solution search stack."""

    # The steps to take to arrive at this state.
    # Optimized for fast lookup of previously taken steps (key = step; value = step index).
    steps: dict[SolutionStep, int]

    # The last step in the sequence of steps to arrive at this state.
    current_step: SolutionStep

    # The number of cells in each upload sequence we yet have to complete.
    incomplete_sequence_length: list[int]

    # Whether we must pick the next cell from a row or a column.
    next_pick_direction: CellChoiceDirection


def _solve_internal(
    spec: GameSpecification,
    strategy: SolutionStrategy = SolutionStrategy.FIND_FIRST_SOLUTION,
) -> list[Solution]:
    """
    Solve the "breach protocol" hacking minigame.

    Same interface as `solve`, but this function does not try to remove the lower-priority
    sequences if no solutions are found, so it is used as a helper in `solve`.
    """
    solutions: list[Solution] = []

    # Depth-first search (DFS) stack.
    search_stack: deque = deque()

    # We must start the input from the first row according to the rules of the game.
    initial_row_idx = 0

    # Populate the search stack with all candidate cells from the initial row.
    for col_idx, cell_value in spec.code_matrix.iterate_row(initial_row_idx):
        current_step = SolutionStep(value=cell_value, row_idx=initial_row_idx, col_idx=col_idx)
        stack_item = SearchStackItem(
            steps={current_step: 0},
            current_step=current_step,
            incomplete_sequence_length=[
                # If the initial cell moves us closer to completing this upload sequence,
                # decrement the number of incomplete cells. Otherwise, leave it at sequence length.
                len(upload_sequence) - (1 if upload_sequence[0] == cell_value else 0)
                for upload_sequence in spec.upload_sequences
            ],
            next_pick_direction=CellChoiceDirection.COLUMN,
        )
        search_stack.append(stack_item)

    while search_stack:
        # Get the next candidate cell from the stack.
        current_search_point = search_stack.pop()

        # Does this input buffer complete all upload sequences? If yes, a solution is found!
        if sum(current_search_point.incomplete_sequence_length) == 0:
            ordered_steps = [
                item[0] for item in sorted(current_search_point.steps.items(), key=itemgetter(1))
            ]
            solution = Solution(steps=ordered_steps)
            solutions.append(solution)

            if strategy == SolutionStrategy.FIND_FIRST_SOLUTION:
                break

            continue

        # If the remaining buffer is not enough to complete all upload sequences,
        # the path is hopeless, and we should abandon it.
        remaining_buffer_size = spec.buffer_size - len(current_search_point.steps)
        if remaining_buffer_size < max(current_search_point.incomplete_sequence_length):
            continue

        current_col_idx = current_search_point.current_step.col_idx
        current_row_idx = current_search_point.current_step.row_idx

        # Identify the next possible steps.
        # Are we allowed to pick cells from the current row or the current column?
        if current_search_point.next_pick_direction == CellChoiceDirection.ROW:
            next_steps = [
                SolutionStep(value=cell_value, row_idx=current_row_idx, col_idx=col_idx)
                for col_idx, cell_value in spec.code_matrix.iterate_row(current_row_idx)
                if col_idx != current_col_idx
            ]
            # According to the rules of the game, we must change the direction at each step.
            next_pick_direction = CellChoiceDirection.COLUMN
        else:
            next_steps = [
                SolutionStep(value=cell_value, row_idx=row_idx, col_idx=current_col_idx)
                for row_idx, cell_value in spec.code_matrix.iterate_col(current_col_idx)
                if row_idx != current_row_idx
            ]
            # According to the rules of the game, we must change the direction at each step.
            next_pick_direction = CellChoiceDirection.ROW

        # Now that we have identified the next possible steps, add them to the search stack.
        for next_step in next_steps:
            # We cannot use a cell more than once.
            if next_step in current_search_point.steps:
                continue

            # Add the unused cells in the row/column to the stack.
            next_search_point = SearchStackItem(
                steps=current_search_point.steps | {next_step: len(current_search_point.steps)},
                current_step=next_step,
                incomplete_sequence_length=[
                    # If the sequence is already completed, adding extra input won't change it.
                    (
                        0
                        if incomplete_length == 0
                        # If the next step moves us closer to completing this upload
                        # sequence, decrement the incomplete length. If an irrelevant cell
                        # is added to an incomplete sequence, reset the counter to the
                        # sequence's original length.
                        else (
                            incomplete_length - 1
                            if upload_sequence[-incomplete_length] == next_step.value
                            else len(upload_sequence)
                        )
                    )
                    for upload_sequence, incomplete_length in zip(
                        spec.upload_sequences,
                        current_search_point.incomplete_sequence_length,
                    )
                ],
                next_pick_direction=next_pick_direction,
            )
            search_stack.append(next_search_point)

    solutions = sorted(solutions, key=lambda sol: len(sol.steps))
    return solutions


def solve(
    spec: GameSpecification,
    strategy: SolutionStrategy = SolutionStrategy.FIND_FIRST_SOLUTION,
) -> list[Solution]:
    """
    Solve the "breach protocol" hacking minigame.

    Parameters
    ----------
    spec
        Specifies the minigame data (code matrix, upload sequences, buffer size).
    strategy
        Whether to terminate when the first solution is found or to find all solutions.
        See also: SolutionStrategy.

    Returns
    -------
    Solutions found for the minigame.

    If the strategy is `FIND_FIRST_SOLUTION`, returns a list with one item.
    If the strategy is `FIND_ALL_SOLUTIONS`, returns a list with all solutions.
    If no solutions are found, returns an empty list.
    """
    solutions = _solve_internal(spec=spec, strategy=strategy)

    # If there are no solutions that satisfy all upload sequences at once, discard lower-priority
    # sequences until a solution is found or there is nothing left to discard.
    if not solutions:
        unique_priorities = sorted(
            list(set(sequence.priority for sequence in spec.upload_sequences))
        )

        if len(unique_priorities) > 1:
            msg = (
                "Warning: Could not find a solution that satisfies all upload sequences. "
                f"Discarding all sequences with priority <= {unique_priorities[0]}."
            )
            print(msg)

            # Try solving again with a reduced set of upload sequences.
            higher_priority_sequences = [
                sequence
                for sequence in spec.upload_sequences
                if sequence.priority > unique_priorities[0]
            ]
            updated_spec = dataclasses.replace(spec, upload_sequences=higher_priority_sequences)
            solutions = solve(spec=updated_spec, strategy=strategy)

    return solutions
