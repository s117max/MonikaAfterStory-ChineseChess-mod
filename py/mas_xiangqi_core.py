# -*- coding: utf-8 -*-

RED = "red"
BLACK = "black"
EMPTY = "."

ROOK = "r"
HORSE = "h"
ELEPHANT = "e"
ADVISOR = "a"
KING = "k"
CANNON = "c"
PAWN = "p"

FILES = "abcdefghi"
OPPOSITE_SIDE = {
    RED: BLACK,
    BLACK: RED,
}

PIECE_LABELS = {
    RED + ROOK: u"车",
    RED + HORSE: u"马",
    RED + ELEPHANT: u"相",
    RED + ADVISOR: u"仕",
    RED + KING: u"帅",
    RED + CANNON: u"炮",
    RED + PAWN: u"兵",
    BLACK + ROOK: u"车",
    BLACK + HORSE: u"马",
    BLACK + ELEPHANT: u"象",
    BLACK + ADVISOR: u"士",
    BLACK + KING: u"将",
    BLACK + CANNON: u"炮",
    BLACK + PAWN: u"卒",
}


class XiangqiMove(object):
    __slots__ = ("src", "dst", "piece", "captured")

    def __init__(self, src, dst, piece, captured=None):
        self.src = tuple(src)
        self.dst = tuple(dst)
        self.piece = piece
        self.captured = captured

    def clone(self):
        return XiangqiMove(self.src, self.dst, self.piece, self.captured)

    def as_key(self):
        return (
            self.src[0],
            self.src[1],
            self.dst[0],
            self.dst[1],
            self.piece,
            self.captured,
        )

    def to_iccs(self):
        return "%s%d%s%d" % (
            FILES[self.src[0]],
            self.src[1],
            FILES[self.dst[0]],
            self.dst[1],
        )

    def __repr__(self):
        return "<XiangqiMove %s>" % self.to_iccs()


class XiangqiUndo(object):
    __slots__ = (
        "src",
        "dst",
        "piece",
        "captured",
        "prev_side",
        "prev_last_move",
        "applied_move",
        "tracked_key",
    )

    def __init__(self, src, dst, piece, captured, prev_side, prev_last_move, applied_move, tracked_key=None):
        self.src = tuple(src)
        self.dst = tuple(dst)
        self.piece = piece
        self.captured = captured
        self.prev_side = prev_side
        self.prev_last_move = prev_last_move
        self.applied_move = applied_move
        self.tracked_key = tracked_key


class XiangqiBoard(object):
    WIDTH = 9
    HEIGHT = 10

    PIECE_VALUES = {
        KING: 10000,
        ROOK: 900,
        CANNON: 450,
        HORSE: 400,
        ELEPHANT: 200,
        ADVISOR: 200,
        PAWN: 100,
    }

    def __init__(
        self,
        grid=None,
        side_to_move=RED,
        position_counts=None,
        move_history=None,
        last_move=None
    ):
        self.grid = self._copy_grid(grid) if grid is not None else self._build_start_grid()
        self.side_to_move = side_to_move
        self.move_history = list(move_history) if move_history is not None else []
        self.last_move = last_move.clone() if last_move is not None else None
        self.position_counts = dict(position_counts) if position_counts is not None else {}

        if not self.position_counts:
            key = self.position_key()
            self.position_counts[key] = 1

    @staticmethod
    def _copy_grid(grid):
        return [list(row) for row in grid]

    @classmethod
    def _build_start_grid(cls):
        grid = [[EMPTY for _x in range(cls.WIDTH)] for _y in range(cls.HEIGHT)]

        grid[0] = [
            BLACK + ROOK,
            BLACK + HORSE,
            BLACK + ELEPHANT,
            BLACK + ADVISOR,
            BLACK + KING,
            BLACK + ADVISOR,
            BLACK + ELEPHANT,
            BLACK + HORSE,
            BLACK + ROOK,
        ]
        grid[2][1] = BLACK + CANNON
        grid[2][7] = BLACK + CANNON
        for x in (0, 2, 4, 6, 8):
            grid[3][x] = BLACK + PAWN

        grid[9] = [
            RED + ROOK,
            RED + HORSE,
            RED + ELEPHANT,
            RED + ADVISOR,
            RED + KING,
            RED + ADVISOR,
            RED + ELEPHANT,
            RED + HORSE,
            RED + ROOK,
        ]
        grid[7][1] = RED + CANNON
        grid[7][7] = RED + CANNON
        for x in (0, 2, 4, 6, 8):
            grid[6][x] = RED + PAWN

        return grid

    def clone(self):
        return XiangqiBoard(
            grid=self.grid,
            side_to_move=self.side_to_move,
            position_counts=self.position_counts,
            move_history=[move.clone() for move in self.move_history],
            last_move=self.last_move,
        )

    @staticmethod
    def inside_board(x, y):
        return 0 <= x < XiangqiBoard.WIDTH and 0 <= y < XiangqiBoard.HEIGHT

    @staticmethod
    def piece_side(piece):
        if not piece or piece == EMPTY:
            return None
        if piece.startswith(RED):
            return RED
        return BLACK

    @staticmethod
    def piece_type(piece):
        if not piece or piece == EMPTY:
            return None
        return piece[-1]

    def get_piece(self, x, y):
        if not self.inside_board(x, y):
            return None
        return self.grid[y][x]

    def set_piece(self, x, y, piece):
        self.grid[y][x] = piece

    def position_key(self):
        return self.side_to_move + "|" + "/".join("".join(row) for row in self.grid)

    def reset_position_tracking(self):
        self.position_counts = {
            self.position_key(): 1
        }
        self.move_history = []
        self.last_move = None

    def find_king(self, side):
        target = side + KING
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                if self.grid[y][x] == target:
                    return (x, y)
        return None

    def palace_contains(self, x, y, side):
        if x < 3 or x > 5:
            return False
        if side == RED:
            return 7 <= y <= 9
        return 0 <= y <= 2

    def crossed_river(self, y, side):
        if side == RED:
            return y <= 4
        return y >= 5

    def is_enemy(self, piece, side):
        piece_side = self.piece_side(piece)
        return piece_side is not None and piece_side != side

    def iter_side_pieces(self, side):
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                piece = self.grid[y][x]
                if piece != EMPTY and self.piece_side(piece) == side:
                    yield x, y, piece

    def count_between(self, x1, y1, x2, y2):
        if x1 == x2:
            step = 1 if y2 > y1 else -1
            count = 0
            y = y1 + step
            while y != y2:
                if self.get_piece(x1, y) != EMPTY:
                    count += 1
                y += step
            return count

        if y1 == y2:
            step = 1 if x2 > x1 else -1
            count = 0
            x = x1 + step
            while x != x2:
                if self.get_piece(x, y1) != EMPTY:
                    count += 1
                x += step
            return count

        return None

    def _append_if_open_or_capture(self, moves, x, y, nx, ny, side):
        if not self.inside_board(nx, ny):
            return

        target = self.get_piece(nx, ny)
        if target == EMPTY or self.is_enemy(target, side):
            moves.append(XiangqiMove((x, y), (nx, ny), self.get_piece(x, y), target if target != EMPTY else None))

    def generate_pseudo_moves_for_piece(self, x, y):
        piece = self.get_piece(x, y)
        if piece == EMPTY:
            return []

        side = self.piece_side(piece)
        ptype = self.piece_type(piece)
        moves = []

        if ptype == ROOK:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx = x + dx
                ny = y + dy
                while self.inside_board(nx, ny):
                    target = self.get_piece(nx, ny)
                    if target == EMPTY:
                        moves.append(XiangqiMove((x, y), (nx, ny), piece))
                    else:
                        if self.is_enemy(target, side):
                            moves.append(XiangqiMove((x, y), (nx, ny), piece, target))
                        break
                    nx += dx
                    ny += dy

        elif ptype == CANNON:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx = x + dx
                ny = y + dy
                jumped = False
                while self.inside_board(nx, ny):
                    target = self.get_piece(nx, ny)
                    if not jumped:
                        if target == EMPTY:
                            moves.append(XiangqiMove((x, y), (nx, ny), piece))
                        else:
                            jumped = True
                    else:
                        if target != EMPTY:
                            if self.is_enemy(target, side):
                                moves.append(XiangqiMove((x, y), (nx, ny), piece, target))
                            break
                    nx += dx
                    ny += dy

        elif ptype == HORSE:
            steps = (
                ((1, 0), (2, 1)),
                ((1, 0), (2, -1)),
                ((-1, 0), (-2, 1)),
                ((-1, 0), (-2, -1)),
                ((0, 1), (1, 2)),
                ((0, 1), (-1, 2)),
                ((0, -1), (1, -2)),
                ((0, -1), (-1, -2)),
            )
            for leg, jump in steps:
                lx = x + leg[0]
                ly = y + leg[1]
                if not self.inside_board(lx, ly) or self.get_piece(lx, ly) != EMPTY:
                    continue
                nx = x + jump[0]
                ny = y + jump[1]
                self._append_if_open_or_capture(moves, x, y, nx, ny, side)

        elif ptype == ELEPHANT:
            for dx, dy in ((2, 2), (2, -2), (-2, 2), (-2, -2)):
                eye_x = x + (dx // 2)
                eye_y = y + (dy // 2)
                nx = x + dx
                ny = y + dy
                if not self.inside_board(nx, ny):
                    continue
                if self.get_piece(eye_x, eye_y) != EMPTY:
                    continue
                if side == RED and ny < 5:
                    continue
                if side == BLACK and ny > 4:
                    continue
                self._append_if_open_or_capture(moves, x, y, nx, ny, side)

        elif ptype == ADVISOR:
            for dx, dy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                nx = x + dx
                ny = y + dy
                if self.palace_contains(nx, ny, side):
                    self._append_if_open_or_capture(moves, x, y, nx, ny, side)

        elif ptype == KING:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx = x + dx
                ny = y + dy
                if self.palace_contains(nx, ny, side):
                    self._append_if_open_or_capture(moves, x, y, nx, ny, side)

            enemy_king_pos = self.find_king(OPPOSITE_SIDE[side])
            if enemy_king_pos is not None and enemy_king_pos[0] == x:
                if self.count_between(x, y, enemy_king_pos[0], enemy_king_pos[1]) == 0:
                    enemy_piece = self.get_piece(enemy_king_pos[0], enemy_king_pos[1])
                    moves.append(XiangqiMove((x, y), enemy_king_pos, piece, enemy_piece))

        elif ptype == PAWN:
            forward = -1 if side == RED else 1
            self._append_if_open_or_capture(moves, x, y, x, y + forward, side)

            if self.crossed_river(y, side):
                self._append_if_open_or_capture(moves, x, y, x + 1, y, side)
                self._append_if_open_or_capture(moves, x, y, x - 1, y, side)

        return moves

    def is_square_attacked(self, x, y, attacker_side):
        for px, py, piece in self.iter_side_pieces(attacker_side):
            for move in self.generate_pseudo_moves_for_piece(px, py):
                if move.dst == (x, y):
                    return True
        return False

    def is_in_check(self, side):
        king_pos = self.find_king(side)
        if king_pos is None:
            return True
        return self.is_square_attacked(king_pos[0], king_pos[1], OPPOSITE_SIDE[side])

    def generate_legal_moves(self, side=None):
        if side is None:
            side = self.side_to_move

        legal_moves = []
        for x, y, _piece in self.iter_side_pieces(side):
            for move in self.generate_pseudo_moves_for_piece(x, y):
                undo = self.push_move(move, track_history=False)
                is_legal = not self.is_in_check(side)
                self.pop_move(undo, track_history=False)
                if is_legal:
                    legal_moves.append(move)
        return legal_moves

    def legal_moves_from(self, src, side=None):
        return [move for move in self.generate_legal_moves(side) if move.src == tuple(src)]

    def push_move(self, move, track_history=True):
        piece = self.get_piece(move.src[0], move.src[1])
        captured = self.get_piece(move.dst[0], move.dst[1])
        actual_move = XiangqiMove(
            move.src,
            move.dst,
            piece,
            captured if captured != EMPTY else None,
        )

        undo = XiangqiUndo(
            move.src,
            move.dst,
            piece,
            captured,
            self.side_to_move,
            self.last_move.clone() if self.last_move is not None else None,
            actual_move,
        )

        self.set_piece(move.src[0], move.src[1], EMPTY)
        self.set_piece(move.dst[0], move.dst[1], piece)
        self.side_to_move = OPPOSITE_SIDE[self.side_to_move]
        self.last_move = actual_move
        self.move_history.append(actual_move)

        if track_history:
            key = self.position_key()
            self.position_counts[key] = self.position_counts.get(key, 0) + 1
            undo.tracked_key = key

        return undo

    def pop_move(self, undo, track_history=True):
        self.set_piece(undo.src[0], undo.src[1], undo.piece)
        self.set_piece(undo.dst[0], undo.dst[1], undo.captured)
        self.side_to_move = undo.prev_side
        self.last_move = undo.prev_last_move

        if self.move_history:
            self.move_history.pop()

        if track_history and undo.tracked_key in self.position_counts:
            self.position_counts[undo.tracked_key] -= 1
            if self.position_counts[undo.tracked_key] <= 0:
                del self.position_counts[undo.tracked_key]

        return undo.applied_move

    def apply_move(self, move, track_history=True):
        undo = self.push_move(move, track_history=track_history)
        return undo.applied_move

    def get_game_state(self):
        red_king = self.find_king(RED)
        black_king = self.find_king(BLACK)
        if red_king is None:
            return {
                "status": "win",
                "winner": BLACK,
                "reason": "king_captured",
                "in_check": False,
            }
        if black_king is None:
            return {
                "status": "win",
                "winner": RED,
                "reason": "king_captured",
                "in_check": False,
            }

        if self.position_counts.get(self.position_key(), 0) >= 3:
            return {
                "status": "draw",
                "winner": None,
                "reason": "threefold",
                "in_check": False,
            }

        current_side = self.side_to_move
        in_check = self.is_in_check(current_side)
        legal_moves = self.generate_legal_moves(current_side)

        if legal_moves:
            return {
                "status": "ongoing",
                "winner": None,
                "reason": None,
                "in_check": in_check,
            }

        if in_check:
            return {
                "status": "win",
                "winner": OPPOSITE_SIDE[current_side],
                "reason": "checkmate",
                "in_check": True,
            }

        return {
            "status": "draw",
            "winner": None,
            "reason": "stalemate",
            "in_check": False,
        }

    def board_rows(self):
        return [list(row) for row in self.grid]

    def pretty_lines(self):
        lines = []
        for y in range(self.HEIGHT):
            cols = []
            for x in range(self.WIDTH):
                piece = self.get_piece(x, y)
                cols.append(piece if piece != EMPTY else "..")
            lines.append(" ".join(cols))
        return lines
