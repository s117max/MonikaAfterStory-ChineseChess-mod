# -*- coding: utf-8 -*-

import time

from mas_xiangqi_core import (
    RED,
    BLACK,
    KING,
    ROOK,
    HORSE,
    ELEPHANT,
    ADVISOR,
    CANNON,
    PAWN,
    OPPOSITE_SIDE,
)


class SearchTimeout(Exception):
    pass


class XiangqiAI(object):
    MATE_SCORE = 1000000
    TT_EXACT = 0
    TT_LOWER = 1
    TT_UPPER = 2
    MAX_TIME_LIMIT = 15.0
    MAX_NODE_LIMIT = 240000
    CHECK_EXTENSION_LIMIT = 2

    DIFFICULTIES = {
        "easy": {
            "label": u"轻松",
            "max_depth": 1,
            "time_limit": 1.00,
            "node_limit": 4000,
        },
        "normal": {
            "label": u"标准",
            "max_depth": 2,
            "time_limit": 4.00,
            "node_limit": 18000,
        },
        "hard": {
            "label": u"挑战",
            "max_depth": 3,
            "time_limit": 8.00,
            "node_limit": 80000,
        },
        "master": {
            "label": u"大师",
            "max_depth": 4,
            "time_limit": 15.00,
            "node_limit": 240000,
        }
    }

    POSITION_BONUS = {
        ROOK: 0,
        HORSE: 8,
        ELEPHANT: 3,
        ADVISOR: 3,
        KING: 2,
        CANNON: 6,
        PAWN: 0,
    }

    def __init__(self, side=BLACK, difficulty="normal"):
        self.side = side
        self.difficulty = difficulty if difficulty in self.DIFFICULTIES else "normal"
        self._reset_search_state()

    def _reset_search_state(self):
        self.nodes = 0
        self.tt = {}
        self.history = {}
        self.killers = {}
        self.start_time = 0.0
        self.deadline = 0.0
        self.node_limit = 0
        self.progress_callback = None
        self.last_progress_nodes = 0
        self.root_best_move = None
        self.root_best_score = 0
        self.completed_depth = 0

    def set_difficulty(self, difficulty):
        if difficulty in self.DIFFICULTIES:
            self.difficulty = difficulty

    def get_difficulty(self):
        return self.DIFFICULTIES[self.difficulty]

    def difficulty_label(self):
        return self.get_difficulty()["label"]

    def choose_move(self, board, progress_callback=None, stop_checker=None):
        config = self._build_runtime_config(board)
        self._reset_search_state()
        self.progress_callback = progress_callback
        self.start_time = time.time()
        self.deadline = self.start_time + config["time_limit"]
        self.node_limit = config["node_limit"]

        side = board.side_to_move
        legal_moves = board.generate_legal_moves(side)
        if not legal_moves:
            return {
                "move": None,
                "score": None,
                "depth": 0,
                "nodes": 0,
                "elapsed": 0.0,
            }

        immediate = self._pick_immediate_tactical_move(board, legal_moves, side)
        if immediate["forced_win"]:
            elapsed = time.time() - self.start_time
            self._notify_progress(
                depth=1,
                max_depth=config["max_depth"],
                best_move=immediate["move"],
                best_score=self.MATE_SCORE,
                done=True,
                force=True,
                elapsed=elapsed
            )
            return {
                "move": immediate["move"].as_key(),
                "score": self.MATE_SCORE,
                "depth": 1,
                "nodes": immediate["nodes"],
                "elapsed": elapsed,
            }

        forced_mate = self._find_endgame_forced_mate(
            board,
            legal_moves,
            side,
            stop_checker
        )
        if forced_mate is not None:
            elapsed = time.time() - self.start_time
            self._notify_progress(
                depth=forced_mate["depth"],
                max_depth=config["max_depth"],
                best_move=forced_mate["move"],
                best_score=self.MATE_SCORE - (forced_mate["depth"] * 100),
                done=True,
                force=True,
                elapsed=elapsed
            )
            return {
                "move": forced_mate["move"].as_key(),
                "score": self.MATE_SCORE - (forced_mate["depth"] * 100),
                "depth": forced_mate["depth"],
                "nodes": self.nodes,
                "elapsed": elapsed,
            }

        ordered_moves = immediate["ordered_moves"]
        best_move = immediate["move"]
        best_score = immediate["score"]

        self._notify_progress(
            depth=0,
            max_depth=config["max_depth"],
            best_move=best_move,
            best_score=best_score,
            done=False,
            force=True
        )

        for depth in range(1, config["max_depth"] + 1):
            alpha = -self.MATE_SCORE
            beta = self.MATE_SCORE
            iteration_best_move = best_move
            iteration_best_score = -self.MATE_SCORE

            try:
                root_moves = self.order_moves(board, legal_moves, side, 0, best_move.as_key())
                move_count = len(root_moves)

                for move_index, move in enumerate(root_moves):
                    self._check_limits(stop_checker)

                    undo = board.push_move(move, track_history=False)
                    try:
                        score = -self._search(
                            board,
                            depth - 1,
                            -beta,
                            -alpha,
                            OPPOSITE_SIDE[side],
                            side,
                            1,
                            stop_checker
                        )
                    finally:
                        board.pop_move(undo, track_history=False)

                    if score > iteration_best_score:
                        iteration_best_score = score
                        iteration_best_move = move

                    if score > alpha:
                        alpha = score

                    move_percent = float(move_index + 1) / float(max(1, move_count))
                    self._notify_progress(
                        depth=depth,
                        max_depth=config["max_depth"],
                        best_move=iteration_best_move,
                        best_score=iteration_best_score,
                        done=False,
                        root_fraction=move_percent,
                        force=(move_index == move_count - 1)
                    )

                best_move = iteration_best_move
                best_score = iteration_best_score
                self.root_best_move = best_move
                self.root_best_score = best_score
                self.completed_depth = depth

            except SearchTimeout:
                break

        elapsed = time.time() - self.start_time
        self._notify_progress(
            depth=self.completed_depth,
            max_depth=config["max_depth"],
            best_move=best_move,
            best_score=best_score,
            done=True,
            force=True,
            elapsed=elapsed
        )

        return {
            "move": best_move.as_key() if best_move is not None else None,
            "score": best_score,
            "depth": self.completed_depth,
            "nodes": self.nodes,
            "elapsed": elapsed,
        }

    def _build_runtime_config(self, board):
        base = dict(self.get_difficulty())
        enemy_side = OPPOSITE_SIDE[board.side_to_move]
        enemy_piece_count = self._count_side_pieces(board, enemy_side)

        if enemy_piece_count <= 1:
            base["max_depth"] += 2
            base["time_limit"] *= 1.8
            base["node_limit"] *= 3

        elif enemy_piece_count <= 3:
            base["max_depth"] += 1
            base["time_limit"] *= 1.4
            base["node_limit"] *= 2

        if base["time_limit"] > self.MAX_TIME_LIMIT:
            base["time_limit"] = self.MAX_TIME_LIMIT

        if base["node_limit"] > self.MAX_NODE_LIMIT:
            base["node_limit"] = self.MAX_NODE_LIMIT

        return base

    def _find_endgame_forced_mate(self, board, legal_moves, side, stop_checker):
        enemy_side = OPPOSITE_SIDE[side]
        enemy_non_king = self._count_non_king_pieces(board, enemy_side)
        if enemy_non_king > 2:
            return None

        search_depth = 6 if enemy_non_king <= 1 else 4
        candidate_moves = self._order_endgame_mate_moves(board, legal_moves, side)

        for move in candidate_moves:
            self._check_limits(stop_checker)
            undo = board.push_move(move, track_history=False)
            try:
                if self._forced_mate_search(
                    board,
                    enemy_side,
                    side,
                    search_depth - 1,
                    stop_checker
                ):
                    return {
                        "move": move,
                        "depth": search_depth,
                    }
            finally:
                board.pop_move(undo, track_history=False)

        return None

    def _forced_mate_search(self, board, side_to_move, attacker_side, depth, stop_checker):
        self.nodes += 1
        self._check_limits(stop_checker)

        state = board.get_game_state()
        if state["status"] == "win":
            return state["winner"] == attacker_side
        if state["status"] == "draw" or depth <= 0:
            return False

        legal_moves = board.generate_legal_moves(side_to_move)
        if not legal_moves:
            return False

        if side_to_move == attacker_side:
            candidate_moves = self._order_endgame_mate_moves(board, legal_moves, side_to_move)
            for move in candidate_moves:
                undo = board.push_move(move, track_history=False)
                try:
                    if self._forced_mate_search(
                        board,
                        OPPOSITE_SIDE[side_to_move],
                        attacker_side,
                        depth - 1,
                        stop_checker
                    ):
                        return True
                finally:
                    board.pop_move(undo, track_history=False)
            return False

        for move in legal_moves:
            undo = board.push_move(move, track_history=False)
            try:
                if not self._forced_mate_search(
                    board,
                    OPPOSITE_SIDE[side_to_move],
                    attacker_side,
                    depth - 1,
                    stop_checker
                ):
                    return False
            finally:
                board.pop_move(undo, track_history=False)

        return True

    def _order_endgame_mate_moves(self, board, legal_moves, side):
        scored = []
        enemy_side = OPPOSITE_SIDE[side]
        enemy_king = board.find_king(enemy_side)

        for move in legal_moves:
            score = self.score_move(board, move, side, 0, None)
            undo = board.push_move(move, track_history=False)
            try:
                state = board.get_game_state()
                if state["status"] == "win" and state["winner"] == side:
                    score += self.MATE_SCORE
                if board.is_in_check(enemy_side):
                    score += 500000
                replies = len(board.generate_legal_moves(enemy_side))
                score += max(0, 30 - replies) * 600
                if enemy_king is not None:
                    score += self._king_net_bonus(board, enemy_side, enemy_king)
            finally:
                board.pop_move(undo, track_history=False)
            scored.append((score, move))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored]

    def _king_net_bonus(self, board, enemy_side, previous_king_pos):
        king_pos = board.find_king(enemy_side)
        if king_pos is None:
            return 0

        bonus = 0
        center_distance = abs(4 - king_pos[0]) + abs((1 if enemy_side == BLACK else 8) - king_pos[1])
        bonus += max(0, 8 - center_distance) * 80

        mobility = 0
        for move in board.generate_legal_moves(enemy_side):
            if move.piece[-1] == KING:
                mobility += 1
        bonus += max(0, 4 - mobility) * 160

        if previous_king_pos != king_pos:
            bonus += 50

        return bonus

    def _pick_immediate_tactical_move(self, board, legal_moves, side):
        opponent = OPPOSITE_SIDE[side]
        scored_moves = []
        nodes = 0

        for move in legal_moves:
            nodes += 1
            undo = board.push_move(move, track_history=False)
            try:
                state = board.get_game_state()

                if state["status"] == "win" and state["winner"] == side:
                    return {
                        "forced_win": True,
                        "move": move,
                        "score": self.MATE_SCORE,
                        "ordered_moves": [move] + [other for other in legal_moves if other.as_key() != move.as_key()],
                        "nodes": nodes,
                    }

                score = self.score_move(board, move, side, 0, None)
                score += self.evaluate(board, side, state, 1)
                if board.is_in_check(opponent):
                    score += 25000
                if board.generate_legal_moves(opponent) == [] and board.is_in_check(opponent):
                    score += self.MATE_SCORE // 2

            finally:
                board.pop_move(undo, track_history=False)

            scored_moves.append((score, move))

        scored_moves.sort(key=lambda item: item[0], reverse=True)
        ordered_moves = [item[1] for item in scored_moves]

        return {
            "forced_win": False,
            "move": ordered_moves[0],
            "score": scored_moves[0][0],
            "ordered_moves": ordered_moves,
            "nodes": nodes,
        }

    def _search(self, board, depth, alpha, beta, side_to_move, perspective, ply, stop_checker):
        self.nodes += 1
        self._check_limits(stop_checker)

        state = board.get_game_state()
        if state["status"] != "ongoing":
            return self.evaluate(board, perspective, state, ply)

        if depth <= 0:
            return self._quiescence(board, alpha, beta, side_to_move, perspective, ply, stop_checker)

        if board.is_in_check(side_to_move) and ply <= self.CHECK_EXTENSION_LIMIT:
            depth += 1

        key = board.position_key()
        tt_entry = self.tt.get(key)
        tt_best_key = None
        if tt_entry is not None:
            tt_best_key = tt_entry.get("best")
            if tt_entry["depth"] >= depth:
                if tt_entry["flag"] == self.TT_EXACT:
                    return tt_entry["score"]
                elif tt_entry["flag"] == self.TT_LOWER and tt_entry["score"] > alpha:
                    alpha = tt_entry["score"]
                elif tt_entry["flag"] == self.TT_UPPER and tt_entry["score"] < beta:
                    beta = tt_entry["score"]
                if alpha >= beta:
                    return tt_entry["score"]

        legal_moves = board.generate_legal_moves(side_to_move)
        if not legal_moves:
            return self.evaluate(board, perspective, state, ply)

        original_alpha = alpha
        best_score = -self.MATE_SCORE
        best_move = None

        for move in self.order_moves(board, legal_moves, side_to_move, ply, tt_best_key):
            undo = board.push_move(move, track_history=False)
            try:
                score = -self._search(
                    board,
                    depth - 1,
                    -beta,
                    -alpha,
                    OPPOSITE_SIDE[side_to_move],
                    perspective,
                    ply + 1,
                    stop_checker
                )
            finally:
                board.pop_move(undo, track_history=False)

            if score > best_score:
                best_score = score
                best_move = move

            if score > alpha:
                alpha = score

            if alpha >= beta:
                self._remember_cutoff(move, side_to_move, depth, ply)
                self._store_tt(key, depth, beta, self.TT_LOWER, move)
                return beta

        if best_move is None:
            return self.evaluate(board, perspective, state, ply)

        flag = self.TT_EXACT
        if best_score <= original_alpha:
            flag = self.TT_UPPER
        elif best_score >= beta:
            flag = self.TT_LOWER

        self._store_tt(key, depth, best_score, flag, best_move)
        return best_score

    def _quiescence(self, board, alpha, beta, side_to_move, perspective, ply, stop_checker):
        self.nodes += 1
        self._check_limits(stop_checker)

        stand_pat = self.evaluate(board, perspective, board.get_game_state(), ply)
        if stand_pat >= beta:
            return beta
        if stand_pat > alpha:
            alpha = stand_pat

        tactical_moves = []
        for move in board.generate_legal_moves(side_to_move):
            if move.captured is not None:
                tactical_moves.append(move)
                continue

            undo = board.push_move(move, track_history=False)
            try:
                gives_check = board.is_in_check(OPPOSITE_SIDE[side_to_move])
            finally:
                board.pop_move(undo, track_history=False)
            if gives_check and ply <= 2:
                tactical_moves.append(move)

        if not tactical_moves:
            return alpha

        for move in self.order_moves(board, tactical_moves, side_to_move, ply, None):
            undo = board.push_move(move, track_history=False)
            try:
                score = -self._quiescence(
                    board,
                    -beta,
                    -alpha,
                    OPPOSITE_SIDE[side_to_move],
                    perspective,
                    ply + 1,
                    stop_checker
                )
            finally:
                board.pop_move(undo, track_history=False)

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    def order_moves(self, board, legal_moves, side, ply, tt_move_key):
        return sorted(
            legal_moves,
            key=lambda move: self.score_move(board, move, side, ply, tt_move_key),
            reverse=True
        )

    def score_move(self, board, move, side, ply, tt_move_key):
        move_key = move.as_key()
        score = 0

        if tt_move_key is not None and move_key == tt_move_key:
            score += 10000000

        killers = self.killers.get(ply, [])
        if move_key in killers:
            score += 4000000 - (killers.index(move_key) * 1000)

        score += self.history.get((side, move_key), 0)

        if move.captured:
            victim = board.PIECE_VALUES[move.captured[-1]]
            attacker = board.PIECE_VALUES[move.piece[-1]]
            score += 2000000 + (victim * 16) - attacker

        ptype = move.piece[-1]
        score += self.POSITION_BONUS.get(ptype, 0) * 100
        if ptype == PAWN and self._pawn_advanced(move.dst[1], side):
            score += 900
        if ptype in (ROOK, CANNON, HORSE):
            score += 300

        score += (4 - abs(4 - move.dst[0])) * 20

        return score

    def evaluate(self, board, perspective, precomputed_state=None, ply=0):
        state = precomputed_state or board.get_game_state()
        if state["status"] == "win":
            if state["winner"] == perspective:
                return self.MATE_SCORE - (ply * 100)
            return -self.MATE_SCORE + (ply * 100)

        if state["status"] == "draw":
            return 0

        score = 0
        for y in range(board.HEIGHT):
            for x in range(board.WIDTH):
                piece = board.get_piece(x, y)
                if piece == ".":
                    continue
                side = piece[:-1]
                ptype = piece[-1]
                piece_score = board.PIECE_VALUES[ptype]
                piece_score += self.positional_bonus(ptype, side, x, y)
                if side == perspective:
                    score += piece_score
                else:
                    score -= piece_score

        if board.is_in_check(OPPOSITE_SIDE[perspective]):
            score += 120
        if board.is_in_check(perspective):
            score -= 150

        return score

    def positional_bonus(self, piece_type, side, x, y):
        center_bonus = max(0, 4 - abs(4 - x))

        if piece_type == PAWN:
            bonus = 0
            if self._pawn_advanced(y, side):
                bonus += 36
            bonus += center_bonus * 5
            if side == RED:
                bonus += max(0, 6 - y) * 4
            else:
                bonus += max(0, y - 3) * 4
            return bonus

        if piece_type in (ROOK, CANNON):
            return center_bonus * 8

        if piece_type == HORSE:
            return center_bonus * 10

        if piece_type in (ELEPHANT, ADVISOR):
            return center_bonus * 3

        if piece_type == KING:
            return center_bonus * 4

        return 0

    def _remember_cutoff(self, move, side, depth, ply):
        move_key = move.as_key()
        self.history[(side, move_key)] = self.history.get((side, move_key), 0) + (depth * depth * 100)

        killer_bucket = self.killers.get(ply)
        if killer_bucket is None:
            self.killers[ply] = [move_key]
            return

        if move_key in killer_bucket:
            killer_bucket.remove(move_key)
        killer_bucket.insert(0, move_key)
        del killer_bucket[2:]

    def _store_tt(self, key, depth, score, flag, move):
        self.tt[key] = {
            "depth": depth,
            "score": score,
            "flag": flag,
            "best": move.as_key() if move is not None else None,
        }

    def _check_limits(self, stop_checker):
        if stop_checker is not None and stop_checker():
            raise SearchTimeout()

        if self.nodes >= self.node_limit:
            raise SearchTimeout()

        if self.nodes & 15 == 0:
            if time.time() >= self.deadline:
                raise SearchTimeout()

    def _notify_progress(
        self,
        depth,
        max_depth,
        best_move,
        best_score,
        done,
        root_fraction=0.0,
        force=False,
        elapsed=None
    ):
        if self.progress_callback is None:
            return

        if not force and (self.nodes - self.last_progress_nodes) < 768:
            return

        if elapsed is None:
            elapsed = time.time() - self.start_time

        max_depth = max(1, max_depth)
        percent = float(depth) / float(max_depth)
        percent = min(0.98, percent * 0.85 + (root_fraction * 0.15))
        if done:
            percent = 1.0

        self.last_progress_nodes = self.nodes

        self.progress_callback({
            "depth": depth,
            "max_depth": max_depth,
            "nodes": self.nodes,
            "elapsed": elapsed,
            "percent": percent,
            "best_move": best_move.as_key() if best_move is not None else None,
            "best_score": best_score,
            "done": done,
            "difficulty": self.difficulty,
            "difficulty_label": self.difficulty_label(),
        })

    @staticmethod
    def _pawn_advanced(y, side):
        if side == RED:
            return y <= 4
        return y >= 5

    @staticmethod
    def _count_side_pieces(board, side):
        count = 0
        for y in range(board.HEIGHT):
            for x in range(board.WIDTH):
                piece = board.get_piece(x, y)
                if piece != "." and piece[:-1] == side:
                    count += 1
        return count

    @staticmethod
    def _count_non_king_pieces(board, side):
        count = 0
        for y in range(board.HEIGHT):
            for x in range(board.WIDTH):
                piece = board.get_piece(x, y)
                if piece != "." and piece[:-1] == side and piece[-1] != KING:
                    count += 1
        return count
