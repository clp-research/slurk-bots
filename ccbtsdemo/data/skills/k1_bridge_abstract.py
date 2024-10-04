def k1_bridge(board, x=0, y=0, colors=['blue', 'red']):
    put(board, shape='bridge-h', color=colors[0], x=x, y=y)
    put(board, shape='screw', color=colors[1], x=x, y=y)
