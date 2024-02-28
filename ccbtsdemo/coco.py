import matplotlib.pyplot as plt
import numpy as np


def plot_screw(ax, x, y, factor=3, color="b", cell_size=1):
    if color == 'y':
        color = 'orange'


    circle = plt.Circle(
        (x + cell_size / 2, y + cell_size / 2),
        cell_size / factor,
        edgecolor="k",
        facecolor=color,
    )
    ax.add_patch(circle)
    return


def plot_washer(ax, x, y, color="r", cell_size=1):
    if color == 'y':
        color = 'orange'

    diamond = plt.Polygon(
        [
            (x + cell_size / 2, y),
            (x + cell_size, y + cell_size / 2),
            (x + cell_size / 2, y + cell_size),
            (x, y + cell_size / 2),
        ],
        linewidth=1,
        closed=True,
        edgecolor="k",
        facecolor=color,
    )
    ax.add_patch(diamond)
    return


def plot_nut(ax, x, y, factor=1.4, color="g", cell_size=1):
    if color == 'y':
        color = 'orange'

    square = plt.Rectangle(
        (
            x + (cell_size - cell_size / factor) / 2,
            y + (cell_size - cell_size / factor) / 2,
        ),
        cell_size / factor,
        cell_size / factor,
        linewidth=1,
        edgecolor="k",
        facecolor=color,
    )
    ax.add_patch(square)
    return


def plot_bridge_h(ax, x, y, factor=1.6, color="g", cell_size=1):
    if color == 'y':
        color = 'orange'

    bridge = plt.Rectangle(
        (
            x + (cell_size - cell_size / factor) / 2,
            y + (cell_size - cell_size / factor) / 2,
        ),
        (cell_size / factor + (cell_size - cell_size / factor) / 2) * 2,
        cell_size / factor,
        linewidth=1,
        edgecolor="k",
        facecolor=color,
    )
    ax.add_patch(bridge)
    return


def plot_bridge_v(ax, x, y, factor=1.6, color="g", cell_size=1):
    if color == 'y':
        color = 'orange'


    bridge = plt.Rectangle(
        (
            x + (cell_size - cell_size / factor) / 2,
            y + (cell_size - cell_size / factor) / 2,
        ),
        cell_size / factor,
        (cell_size / factor + (cell_size - cell_size / factor) / 2) * 2,
        linewidth=1,
        edgecolor="k",
        facecolor=color,
    )
    ax.add_patch(bridge)
    return


def set_up_board_plot(rows, cols, cell_size):
    # Create a figure and axis
    fig, ax = plt.subplots()

    # Loop through rows and columns to create the grid
    for row in range(rows):
        for col in range(cols):
            # Define the coordinates and size of each rectangle
            x = col
            y = row
            width = 1
            height = 1

            # Create a rectangle for each cell in the grid
            rect = plt.Rectangle(
                (x, y), width, height, linewidth=1, edgecolor="k", facecolor="w"
            )
            ax.add_patch(rect)

    # Set axis limits to match the grid size
    ax.set_xlim(0, cols)
    ax.set_ylim(0, rows)

    # Remove axis labels and ticks
    ax.set_xticks([])
    ax.set_yticks([])

    ax.set_aspect("equal", adjustable="box")

    # invert y, to move 0,0 to top left
    plt.gca().invert_yaxis()

    return fig, ax


def plot_board(board, filename=None):
    max_height, depth, rows, cols = board.shape

    fig, ax = set_up_board_plot(rows, cols, cell_size=1)

    for this_layer in board:
        obj = this_layer[0].T
        clr = this_layer[1].T

        for r in range(obj.shape[1]):
            for c in range(obj.shape[0]):
                if obj[r, c] == "S":
                    plot_screw(ax, r, c, color=clr[r, c])
                if obj[r, c] == "W":
                    plot_washer(ax, r, c, color=clr[r, c])
                if obj[r, c] == "N":
                    plot_nut(ax, r, c, color=clr[r, c])
                if obj[r, c] == "L":
                    plot_bridge_h(ax, r, c, color=clr[r, c])
                if obj[r, c] == "T":
                    plot_bridge_v(ax, r, c, color=clr[r, c])
    if filename:
        plt.savefig(filename, dpi=300)
    plt.close()


long_to_short = {"washer": "W", "nut": "N", "screw": "S"}
long_to_short_color = {"red": "r", "green": "g", "blue": "b", "yellow": "y"}


# custom exceptions
class SameShapeStackingError(Exception):
    "Raised when same shapes are stacked on top of each other"
    pass


class SameShapeAtAlternateLevels(Exception):
    "Raised when same shapes are stacked at alternate levels"
    pass

class SameColorAtAlternateLevels(Exception):
    "Raised when same colors are stacked at alternate levels"
    pass

class SameColorStackingError(Exception):
    "Raised when same colors are stacked on top of each other"
    pass


class NotOnTopOfScrewError(Exception):
    "Raised when a shape is placed on top of a screw"
    pass


class DepthMismatchError(Exception):
    "Raised when the depth of the new shape does not match the depth of existing shapes"
    pass


class BridgePlacementError(Exception):
    "Raised when a bridge is placed at levels greater than 2"
    pass


class DimensionsMismatchError(Exception):
    "Raised when the dimensions of the board do not match the dimensions of input x,y"
    pass


def get_top_layer(board, x, y):
    this_stack = board[:, 0, x, y]
    top_layer = np.where(this_stack == "0")[0]
    if top_layer.size > 0:
        top_layer = top_layer[0]
    else:
        raise (ValueError("Placement not possible"))
    return top_layer

def check_for_errors(top_layer, board, shape, color, x, y):
    if board[top_layer - 1, 1, x, y] == "S":
        raise (NotOnTopOfScrewError("Placement not possible"))

    if board[top_layer - 1, 0, x, y] == long_to_short[shape]:
        raise (SameShapeStackingError("Placement not possible"))            

    if shape == "bridge-h":
        if board[top_layer - 1, 1, x, y] == long_to_short_color[color] or board[top_layer - 1, 1, x, y+1] == long_to_short_color[color]:
            raise (SameColorStackingError("Placement not possible"))
    elif shape == "bridge-v":
        if board[top_layer - 1, 1, x, y] == long_to_short_color[color] or board[top_layer - 1, 1, x+1, y] == long_to_short_color[color]:
            raise (SameColorStackingError("Placement not possible"))
    else:
        if board[top_layer - 1, 1, x, y] == long_to_short_color[color]:
            raise (SameColorStackingError("Placement not possible"))
    
    if top_layer > 1:
        # check if same shape is placed at alternate levels
        if board[top_layer - 2, 0, x, y] == long_to_short[shape]:
            raise (SameShapeAtAlternateLevels("Placement not possible"))    

        # check if same color is placed at alternate levels
        if board[top_layer - 2, 1, x, y] == long_to_short_color[color]:
            raise (SameColorAtAlternateLevels("Placement not possible"))    



# TODO: operate on copy of board, so that original board
# can be returned if placement not possible? (rather than
# raising an exception)
def put(board, shape, color, x, y):
    if x >= board.shape[2] or y >= board.shape[3]:
        raise (DimensionsMismatchError("Placement not possible"))

    top_layer = get_top_layer(board, x, y)

    if shape == "bridge-h":
        if y + 1 >= board.shape[3]:
            raise (ValueError("Placement not possible"))

        if top_layer >= 2:
            raise (BridgePlacementError("Placement not possible"))

        if top_layer > 0:
            check_for_errors(top_layer, board, shape, color, x, y)

        top_layer_adjacent = get_top_layer(board, x, y + 1)
        if top_layer != top_layer_adjacent:
            print(f"top_layer: {top_layer}, top_layer_adjacent: {top_layer_adjacent} raising DepthMismatchError")
            raise (DepthMismatchError("Placement not possible"))

        print("Setting values for bridge-h")
        board[top_layer, 0, x, y] = "L"
        board[top_layer, 1, x, y] = color


        board[top_layer, 0, x, y + 1] = "R"
        board[top_layer, 1, x, y + 1] = color
    elif shape == "bridge-v":
        if x + 1 >= board.shape[2]:
            raise (ValueError("Placement not possible"))

        if top_layer >= 2:
            raise (BridgePlacementError("Placement not possible"))

        if top_layer > 0:
            check_for_errors(top_layer, board, shape, color, x, y)

        top_layer_adjacent = get_top_layer(board, x + 1, y)
        if top_layer != top_layer_adjacent:
            raise (DepthMismatchError("Placement not possible"))

        board[top_layer, 0, x, y] = "T"
        board[top_layer, 1, x, y] = color


        board[top_layer, 0, x + 1, y] = "B"
        board[top_layer, 1, x + 1, y] = color
    else:
        # check if it is being placed on top of another screw
        if top_layer > 0:
            check_for_errors(top_layer, board, shape, color, x, y)           

        board[top_layer, 0, x, y] = long_to_short[shape]
        board[top_layer, 1, x, y] = color
    # check whether resulting board is legal
    return


def init_board(rows=6, cols=6, max_height=4, depth=2):
    # the board is represented via stacked matrices:
    # there are max_height layers (by default 4), representing the stacking
    # each layer has depth channels (by default 2), one of which will
    # hold the shape information, the other the colour information
    # each layer is a 2d matrix with dimensions as given by rows and cols
    return np.full((max_height, depth, rows, cols), "0", dtype=str)


def place_on_board(board, obj_board, x, y):
    board[
        :, :, slice(x, x + obj_board.shape[2]), slice(y, y + obj_board.shape[3])
    ] = obj_board
    return board


def board_rot90(board):
    board_r = np.rot90(board, axes=(2, 3))
    bridge_rot_dict = {
        "R": "T",
        "L": "B",
        "T": "L",
        "B": "R",
        "W": "W",
        "N": "N",
        "S": "S",
        "0": "0",
    }
    board_r[:, 0] = np.vectorize(bridge_rot_dict.get)(board_r[:, 0])
    return board_r
