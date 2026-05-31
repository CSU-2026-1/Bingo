import random
from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.cards import CardCell, CardResponse, WinnerCheckData


BALL_RANGES = {
    "B": range(1, 16),
    "I": range(16, 31),
    "N": range(31, 46),
    "G": range(46, 61),
    "O": range(61, 76),
}

COLUMN_LETTERS = tuple(BALL_RANGES.keys())
FREE_ROW = 2
FREE_COL = 2

WINNING_PATTERN_POSITIONS = {
    "top_row": [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)],
    "middle_row": [(2, 0), (2, 1), (2, 2), (2, 3), (2, 4)],
    "bottom_row": [(4, 0), (4, 1), (4, 2), (4, 3), (4, 4)],
    "left_column": [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)],
    "middle_column": [(0, 2), (1, 2), (2, 2), (3, 2), (4, 2)],
    "right_column": [(0, 4), (1, 4), (2, 4), (3, 4), (4, 4)],
    "main_diagonal": [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)],
    "anti_diagonal": [(0, 4), (1, 3), (2, 2), (3, 1), (4, 0)],
    "four_corners": [(0, 0), (0, 4), (4, 0), (4, 4)],
    "x_shape": [
        (0, 0), (1, 1), (2, 2), (3, 3), (4, 4),
        (0, 4), (1, 3), (3, 1), (4, 0),
    ],
    "plus_shape": [
        (0, 2), (1, 2), (2, 0), (2, 1), (2, 2),
        (2, 3), (2, 4), (3, 2), (4, 2),
    ],
    "small_frame": [
        (1, 1), (1, 2), (1, 3),
        (2, 1), (2, 3),
        (3, 1), (3, 2), (3, 3),
    ],
}


def generate_card(game_id: str, user_id: str) -> CardResponse:
    columns = {
        letter: random.sample(list(numbers), 5)
        for letter, numbers in BALL_RANGES.items()
    }
    rows: list[list[CardCell]] = []

    for row in range(5):
        cells: list[CardCell] = []
        for col, letter in enumerate(COLUMN_LETTERS):
            if row == FREE_ROW and col == FREE_COL:
                cells.append(
                    CardCell(
                        row=row,
                        col=col,
                        letter=letter,
                        label="FREE",
                        marked=True,
                        is_free=True,
                    )
                )
                continue

            number = columns[letter][row]
            cells.append(
                CardCell(
                    row=row,
                    col=col,
                    letter=letter,
                    number=number,
                    label=f"{letter}{number}",
                )
            )
        rows.append(cells)

    return CardResponse(
        card_id=str(uuid4()),
        game_id=game_id,
        user_id=user_id,
        created_at=datetime.now(UTC),
        cells=rows,
        marked_numbers=[],
    )


def mark_number(card: CardResponse, number: int) -> tuple[CardResponse, bool]:
    matched = False
    marked_numbers = set(card.marked_numbers)

    for row in card.cells:
        for cell in row:
            if cell.number == number:
                cell.marked = True
                matched = True
                marked_numbers.add(number)

    card.marked_numbers = sorted(marked_numbers)
    return card, matched


def pattern_cells(card: CardResponse, winning_pattern: str) -> list[CardCell]:
    positions = WINNING_PATTERN_POSITIONS.get(winning_pattern, WINNING_PATTERN_POSITIONS["top_row"])
    return [card.cells[row][col] for row, col in positions]


def card_pattern_progress(card: CardResponse, winning_pattern: str) -> tuple[int, int]:
    cells = pattern_cells(card, winning_pattern)
    progress = sum(1 for cell in cells if cell.is_free or cell.marked)
    return progress, len(cells)


def build_winner_check_data(card: CardResponse) -> WinnerCheckData:
    columns = [
        [card.cells[row][col] for row in range(5)]
        for col in range(5)
    ]
    diagonals = [
        [card.cells[index][index] for index in range(5)],
        [card.cells[index][4 - index] for index in range(5)],
    ]

    return WinnerCheckData(
        card_id=card.card_id,
        game_id=card.game_id,
        user_id=card.user_id,
        rows=card.cells,
        columns=columns,
        diagonals=diagonals,
        marked_numbers=card.marked_numbers,
    )
