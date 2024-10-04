def x1_connector(board, x=0, y=0, colors=['blue', 'red', 'red', 'yellow']):
    put(board, shape='bridge-h', color=colors[0], x=x, y=y)
    put(board, shape='screw', color=colors[1], x=x, y=y)
    put(board, shape='nut', color=colors[1], x=x+1, y=y+1)
    put(board, shape='bridge-v', color=colors[1], x=x, y=y+1)
