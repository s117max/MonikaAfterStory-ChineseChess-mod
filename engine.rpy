init -100 python in mas_xiangqi:
    import os
    import sys
    import renpy

    _py_dir = os.path.normpath(
        os.path.join(renpy.config.gamedir, "Submods", "mas_xiangqi", "py")
    )
    if _py_dir not in sys.path:
        sys.path.insert(0, _py_dir)

    import mas_xiangqi_core as _core

    RED = _core.RED
    BLACK = _core.BLACK
    EMPTY = _core.EMPTY

    ROOK = _core.ROOK
    HORSE = _core.HORSE
    ELEPHANT = _core.ELEPHANT
    ADVISOR = _core.ADVISOR
    KING = _core.KING
    CANNON = _core.CANNON
    PAWN = _core.PAWN

    OPPOSITE_SIDE = _core.OPPOSITE_SIDE
    PIECE_LABELS = _core.PIECE_LABELS

    XiangqiMove = _core.XiangqiMove
    XiangqiBoard = _core.XiangqiBoard
