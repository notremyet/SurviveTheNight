
WIDTH = 1000
HEIGHT = 800
COLS = 10
ROWS = 7
CELL_SIZE = 90
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (120, 120, 120)
DARK = (25, 25, 35)


def cell_to_xy(cell):
    col = ord(cell[0].upper()) - ord("A")
    row = int(cell[1:]) - 1
    return col, row


def xy_to_cell(pos):
    x, y = pos
    return f"{chr(ord('A') + x)}{y + 1}"
