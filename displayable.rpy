init -90 python in mas_xiangqi:
    import pygame
    import threading
    import time

    BaseDisplayable = renpy.display.core.Displayable
    RenderClass = renpy.display.render.Render
    render_displayable = renpy.display.render.render
    redraw_displayable = renpy.display.render.redraw
    restart_interaction_fn = renpy.exports.restart_interaction
    ImageClass = renpy.display.im.Image

    class MASXiangqiDisplayable(BaseDisplayable):
        SCREEN_WIDTH = 1280
        SCREEN_HEIGHT = 720

        BOARD_X = 620
        BOARD_Y = 60
        BOARD_WIDTH = 560
        BOARD_HEIGHT = 620
        GRID_SPACING = 60
        GRID_X0 = 40
        GRID_Y0 = 40
        PIECE_SIZE = 50
        CLICK_TOLERANCE = 24

        RESULT_WIN = "win"
        RESULT_LOSS = "loss"
        RESULT_DRAW = "draw"

        def __init__(self, difficulty="normal"):
            BaseDisplayable.__init__(self)

            self.player_side = RED
            self.ai_side = BLACK
            self.board = XiangqiBoard()
            self.ai = XiangqiAI(self.ai_side, difficulty=difficulty)
            self.difficulty = difficulty

            self.selected_square = None
            self.selected_moves = []
            self.ai_busy = False
            self.is_game_over = False
            self.result_code = None
            self.result_reason = None
            self.status_message = u"你执红先手。点击棋子开始走吧。"
            self.current_state = self.board.get_game_state()
            self.ai_progress = {
                "percent": 0.0,
                "depth": 0,
                "max_depth": self.ai.get_difficulty()["max_depth"],
                "nodes": 0,
                "elapsed": 0.0,
                "done": False,
                "difficulty_label": self.ai.difficulty_label(),
            }
            self._ai_thread = None
            self._ai_result = None
            self._ai_error = None
            self._ai_lock = threading.Lock()

            self.board_image = ImageClass(
                "Submods/mas_xiangqi/mod_assets/games/xiangqi/board.png"
            )
            self.highlight_selected = ImageClass(
                "Submods/mas_xiangqi/mod_assets/games/xiangqi/highlight_selected.png"
            )
            self.highlight_move = ImageClass(
                "Submods/mas_xiangqi/mod_assets/games/xiangqi/highlight_move.png"
            )
            self.highlight_last = ImageClass(
                "Submods/mas_xiangqi/mod_assets/games/xiangqi/highlight_last.png"
            )
            self.highlight_check = ImageClass(
                "Submods/mas_xiangqi/mod_assets/games/xiangqi/highlight_check.png"
            )

            self.piece_images = {}
            for piece_code in PIECE_LABELS:
                self.piece_images[piece_code] = ImageClass(
                    "Submods/mas_xiangqi/mod_assets/games/xiangqi/pieces/%s.png" % piece_code
                )

            self._refresh_state()

        def render(self, width, height, st, at):
            renderer = RenderClass(self.SCREEN_WIDTH, self.SCREEN_HEIGHT)

            board_render = render_displayable(
                self.board_image,
                self.BOARD_WIDTH,
                self.BOARD_HEIGHT,
                st,
                at
            )
            renderer.blit(board_render, (self.BOARD_X, self.BOARD_Y))

            self._render_highlights(renderer, st, at)
            self._render_pieces(renderer, st, at)

            redraw_displayable(self, 0.05)
            return renderer

        def _render_highlights(self, renderer, st, at):
            selected_render = render_displayable(
                self.highlight_selected,
                self.PIECE_SIZE,
                self.PIECE_SIZE,
                st,
                at
            )
            move_render = render_displayable(
                self.highlight_move,
                self.PIECE_SIZE,
                self.PIECE_SIZE,
                st,
                at
            )
            last_render = render_displayable(
                self.highlight_last,
                self.PIECE_SIZE,
                self.PIECE_SIZE,
                st,
                at
            )
            check_render = render_displayable(
                self.highlight_check,
                self.PIECE_SIZE,
                self.PIECE_SIZE,
                st,
                at
            )

            if self.board.last_move is not None:
                renderer.blit(last_render, self.board_to_screen(*self.board.last_move.src))
                renderer.blit(last_render, self.board_to_screen(*self.board.last_move.dst))

            if self.selected_square is not None:
                renderer.blit(selected_render, self.board_to_screen(*self.selected_square))
                for move in self.selected_moves:
                    renderer.blit(move_render, self.board_to_screen(*move.dst))

            if self.current_state.get("in_check"):
                checked_side = self.board.side_to_move
                king_pos = self.board.find_king(checked_side)
                if king_pos is not None:
                    renderer.blit(check_render, self.board_to_screen(king_pos[0], king_pos[1]))

        def _render_pieces(self, renderer, st, at):
            for y in range(self.board.HEIGHT):
                for x in range(self.board.WIDTH):
                    piece = self.board.get_piece(x, y)
                    if piece == EMPTY:
                        continue
                    image = self.piece_images.get(piece)
                    if image is None:
                        continue
                    piece_render = render_displayable(
                        image,
                        self.PIECE_SIZE,
                        self.PIECE_SIZE,
                        st,
                        at
                    )
                    renderer.blit(piece_render, self.board_to_screen(x, y))

        def event(self, ev, x, y, st):
            if self.is_game_over or self.ai_busy or self.board.side_to_move != self.player_side:
                return None

            if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                board_pos = self.mouse_to_board(x, y)
                if board_pos is None:
                    return None

                self._handle_player_click(board_pos)
                restart_interaction_fn()
                return None

            return None

        def _handle_player_click(self, board_pos):
            piece = self.board.get_piece(board_pos[0], board_pos[1])

            if self.selected_square is None:
                if piece != EMPTY and self.board.piece_side(piece) == self.player_side:
                    self._select_square(board_pos)
                return

            if board_pos == self.selected_square:
                self._clear_selection()
                return

            if piece != EMPTY and self.board.piece_side(piece) == self.player_side:
                self._select_square(board_pos)
                return

            chosen_move = None
            for move in self.selected_moves:
                if move.dst == board_pos:
                    chosen_move = move
                    break

            if chosen_move is not None:
                self.board.apply_move(chosen_move)
                self._clear_selection()
                self._refresh_state(last_actor=self.player_side)

        def _select_square(self, board_pos):
            legal_moves = self.board.legal_moves_from(board_pos, self.player_side)
            if not legal_moves:
                self._clear_selection()
                return
            self.selected_square = tuple(board_pos)
            self.selected_moves = legal_moves

        def _clear_selection(self):
            self.selected_square = None
            self.selected_moves = []

        def _refresh_state(self, last_actor=None):
            self.current_state = self.board.get_game_state()

            if self.current_state["status"] == "ongoing":
                if last_actor == self.player_side:
                    if self.current_state.get("in_check"):
                        self.status_message = u"将军！轮到 Monika 了。"
                    else:
                        self.status_message = u"轮到 Monika 了。"
                elif last_actor == self.ai_side:
                    if self.current_state.get("in_check"):
                        self.status_message = u"Monika 将军了，小心应对。"
                    else:
                        self.status_message = u"轮到你了。"
                elif self.board.side_to_move == self.player_side:
                    self.status_message = u"你执红先手。点击棋子开始走吧。"
                else:
                    self.status_message = u"Monika 正在思考。"
                return

            self.is_game_over = True
            self.result_reason = self.current_state["reason"]
            winner = self.current_state["winner"]
            if winner == self.player_side:
                self.result_code = self.RESULT_WIN
                self.status_message = u"你赢了这盘棋。"
            elif winner == self.ai_side:
                self.result_code = self.RESULT_LOSS
                self.status_message = u"Monika 赢下了这盘棋。"
            else:
                self.result_code = self.RESULT_DRAW
                if self.result_reason == "threefold":
                    self.status_message = u"三次重复局面，判和。"
                else:
                    self.status_message = u"无合法着法，判和。"

        def should_run_ai(self):
            return (
                not self.is_game_over
                and not self.ai_busy
                and self.board.side_to_move == self.ai_side
            )

        def perform_ai_turn(self):
            self.pulse()

        def pulse(self):
            changed = False

            if self._ai_error is not None:
                self.ai_busy = False
                self.status_message = u"Monika 这一步想得太乱了，我们重新来一次吧。"
                self._ai_error = None
                changed = True

            if self.ai_busy:
                with self._ai_lock:
                    ai_result = self._ai_result
                    if ai_result is not None:
                        self._ai_result = None
                    progress_done = self.ai_progress.get("done", False)

                if ai_result is not None:
                    self._apply_ai_result(ai_result)
                    changed = True

                elif progress_done:
                    changed = True

            elif self.should_run_ai():
                self._start_ai_turn()
                changed = True

            if changed or self.ai_busy:
                restart_interaction_fn()

        def _start_ai_turn(self):
            if self.ai_busy or not self.should_run_ai():
                return

            self.ai_busy = True
            self.status_message = u"Monika 正在思考..."
            self.ai_progress = {
                "percent": 0.0,
                "depth": 0,
                "max_depth": self.ai.get_difficulty()["max_depth"],
                "nodes": 0,
                "elapsed": 0.0,
                "done": False,
                "difficulty_label": self.ai.difficulty_label(),
            }

            board_snapshot = self.board.clone()

            def progress_callback(progress_data):
                with self._ai_lock:
                    self.ai_progress.update(progress_data)

            def run_search():
                try:
                    result = self.ai.choose_move(
                        board_snapshot,
                        progress_callback=progress_callback
                    )
                    with self._ai_lock:
                        self._ai_result = result
                        self.ai_progress["done"] = True

                except Exception as ex:
                    with self._ai_lock:
                        self._ai_error = ex
                        self.ai_progress["done"] = True

            self._ai_thread = threading.Thread(target=run_search)
            self._ai_thread.daemon = True
            self._ai_thread.start()

        def _apply_ai_result(self, ai_result):
            self.ai_busy = False
            move_key = ai_result.get("move")
            if move_key is None:
                self._refresh_state(last_actor=self.ai_side)
                return

            legal_moves = self.board.generate_legal_moves(self.ai_side)
            selected_move = None
            for move in legal_moves:
                if move.as_key() == move_key:
                    selected_move = move
                    break

            if selected_move is not None:
                self.board.apply_move(selected_move)
                self._refresh_state(last_actor=self.ai_side)
            else:
                self.status_message = u"Monika 的着法同步失败了，请重新开始这一局。"

        def is_ai_thinking(self):
            return self.ai_busy

        def ai_progress_fraction(self):
            if not self.ai_busy:
                return 0.0
            return max(0.02, min(1.0, float(self.ai_progress.get("percent", 0.0))))

        def ai_progress_text(self):
            if not self.ai_busy:
                return u""

            depth = self.ai_progress.get("depth", 0)
            max_depth = self.ai_progress.get("max_depth", 1)
            nodes = self.ai_progress.get("nodes", 0)
            elapsed = self.ai_progress.get("elapsed", 0.0)
            return u"思考进度：深度 %d/%d  节点 %d  用时 %.2f 秒" % (
                depth,
                max_depth,
                nodes,
                elapsed
            )

        def difficulty_label(self):
            return self.ai.difficulty_label()

        def board_to_screen(self, x, y):
            center_x = self.BOARD_X + self.GRID_X0 + (x * self.GRID_SPACING)
            center_y = self.BOARD_Y + self.GRID_Y0 + (y * self.GRID_SPACING)
            return (
                int(center_x - (self.PIECE_SIZE / 2)),
                int(center_y - (self.PIECE_SIZE / 2))
            )

        def mouse_to_board(self, x, y):
            rel_x = x - self.BOARD_X - self.GRID_X0
            rel_y = y - self.BOARD_Y - self.GRID_Y0

            if rel_x < -self.CLICK_TOLERANCE or rel_y < -self.CLICK_TOLERANCE:
                return None
            if rel_x > (8 * self.GRID_SPACING) + self.CLICK_TOLERANCE:
                return None
            if rel_y > (9 * self.GRID_SPACING) + self.CLICK_TOLERANCE:
                return None

            board_x = int(round(float(rel_x) / float(self.GRID_SPACING)))
            board_y = int(round(float(rel_y) / float(self.GRID_SPACING)))

            if not self.board.inside_board(board_x, board_y):
                return None

            target_x = board_x * self.GRID_SPACING
            target_y = board_y * self.GRID_SPACING
            if abs(rel_x - target_x) > self.CLICK_TOLERANCE:
                return None
            if abs(rel_y - target_y) > self.CLICK_TOLERANCE:
                return None

            return (board_x, board_y)

        def turn_label(self):
            if self.is_game_over:
                return u"对局已结束"
            if self.board.side_to_move == self.player_side:
                return u"当前回合：你（红方）"
            return u"当前回合：Monika（黑方）"

        def status_label(self):
            return self.status_message

        def result_label(self):
            if self.result_code == self.RESULT_WIN:
                return u"结果：你获胜"
            if self.result_code == self.RESULT_LOSS:
                return u"结果：Monika 获胜"
            if self.result_code == self.RESULT_DRAW:
                return u"结果：和棋"
            return u"结果：对局中"
