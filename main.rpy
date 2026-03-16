screen mas_xiangqi_rules_overlay(can_return=False):
    modal True
    zorder 210

    add Solid("#0008")

    frame:
        xalign 0.5
        yalign 0.5
        xmaximum 980
        ymaximum 620
        xpadding 24
        ypadding 20

        vbox:
            spacing 12

            text "中国象棋规则" size 34 color "#4a2b1f" outlines [(1, "#f7efe7", 0, 0)]
            text "1. 你执红先手，Monika 执黑后手。点击己方棋子后，会高亮当前所有合法落点。" size 24 color "#4a2b1f" outlines [(1, "#f7efe7", 0, 0)]
            text "2. 车走直线，炮平走直吃且必须隔一子，马走日字并受马腿限制。" size 24 color "#4a2b1f" outlines [(1, "#f7efe7", 0, 0)]
            text "3. 相不能过河，仕与帅只能在九宫内活动，兵过河前只能前进，过河后可以左右平移。" size 24 color "#4a2b1f" outlines [(1, "#f7efe7", 0, 0)]
            text "4. 将帅不能照面。若你走子后自己的帅仍被将军，这步就不合法。" size 24 color "#4a2b1f" outlines [(1, "#f7efe7", 0, 0)]
            text "5. 首版支持将死、困毙和三次重复判和；更细的长将长捉裁决暂未加入。" size 24 color "#4a2b1f" outlines [(1, "#f7efe7", 0, 0)]

            if can_return:
                textbutton "关闭" action Return(True) xalign 1.0 text_color "#4a2b1f" text_outlines [(1, "#fff7f0", 0, 0)]
            else:
                textbutton "关闭" action Hide("mas_xiangqi_rules_overlay") xalign 1.0 text_color "#4a2b1f" text_outlines [(1, "#fff7f0", 0, 0)]


screen mas_xiangqi_game(game):
    modal True
    tag mas_xiangqi_game
    zorder 200

    add Solid("#f4ead8")
    add game

    frame:
        xpos 40
        ypos 48
        xsize 510
        ysize 630
        xpadding 20
        ypadding 18

        vbox:
            spacing 12

            text "中国象棋" size 36 color "#4a2b1f" outlines [(1, "#f7efe7", 0, 0)]
            text "难度：[game.difficulty_label()]" size 24 color "#5a3724" outlines [(1, "#f7efe7", 0, 0)]
            text "[game.turn_label()]" size 25 color "#4a2b1f" outlines [(1, "#f7efe7", 0, 0)]
            text "[game.status_label()]" size 24 color "#5a3724" outlines [(1, "#f7efe7", 0, 0)]
            text "[game.result_label()]" size 24 color "#5a3724" outlines [(1, "#f7efe7", 0, 0)]

            if game.is_ai_thinking():
                text "[game.ai_progress_text()]" size 20 color "#6b452d" outlines [(1, "#fff7f0", 0, 0)]
                fixed:
                    xmaximum 380
                    ymaximum 18
                    frame:
                        xpos 0
                        ypos 0
                        xmaximum 380
                        ymaximum 18
                        background Solid("#ead8bc")
                    frame:
                        xpos 0
                        ypos 0
                        xmaximum int(380 * game.ai_progress_fraction())
                        ymaximum 18
                        background Solid("#cf8f4e")

            null height 6

            textbutton "规则" action Show("mas_xiangqi_rules_overlay", can_return=False) text_color "#4a2b1f" text_outlines [(1, "#fff7f0", 0, 0)]

            if not game.is_game_over:
                textbutton "重新开始" action Return({"action": "restart"}) text_color "#4a2b1f" text_outlines [(1, "#fff7f0", 0, 0)]
                textbutton "认输" action Return({"action": "surrender"}) text_color "#4a2b1f" text_outlines [(1, "#fff7f0", 0, 0)]
                textbutton "返回" action Return({"action": "quit", "result": None, "reason": "quit_midgame"}) text_color "#4a2b1f" text_outlines [(1, "#fff7f0", 0, 0)]

            else:
                textbutton "再来一局" action Return({"action": "restart", "result": game.result_code, "reason": game.result_reason}) text_color "#4a2b1f" text_outlines [(1, "#fff7f0", 0, 0)]
                textbutton "返回" action Return({"action": "quit", "result": game.result_code, "reason": game.result_reason}) text_color "#4a2b1f" text_outlines [(1, "#fff7f0", 0, 0)]

    timer 0.10 repeat True action Function(game.pulse)

label mas_xiangqi_start:
    m 3eub "想和我来一局中国象棋吗？"
    m 1hub "这次我会认真下的，所以你也要拿出实力来哦。"

    if not persistent._mas_xiangqi_seen_rules:
        m 1eua "第一次玩的话，先看看简短规则会更轻松。"
        call mas_xiangqi_rules

    call mas_xiangqi_pick_difficulty
    jump mas_xiangqi_session


label mas_xiangqi_rules:
    $ persistent._mas_xiangqi_seen_rules = True
    call screen mas_xiangqi_rules_overlay(can_return=True)
    return


label mas_xiangqi_session:
    $ game = mas_xiangqi.MASXiangqiDisplayable(difficulty=persistent._mas_xiangqi_difficulty)
    call screen mas_xiangqi_game(game)

    if _return["action"] == "restart":
        jump mas_xiangqi_session

    elif _return["action"] == "surrender":
        $ persistent._mas_xiangqi_stats["losses"] += 1
        $ mas_xiangqi_result_reason = "surrender"
        call mas_xiangqi_result_loss
        return

    elif _return["action"] == "quit":
        if _return["result"] == "win":
            $ persistent._mas_xiangqi_stats["wins"] += 1
            $ mas_xiangqi_result_reason = _return["reason"]
            call mas_xiangqi_result_win
            return

        elif _return["result"] == "loss":
            $ persistent._mas_xiangqi_stats["losses"] += 1
            $ mas_xiangqi_result_reason = _return["reason"]
            call mas_xiangqi_result_loss
            return

        elif _return["result"] == "draw":
            $ persistent._mas_xiangqi_stats["draws"] += 1
            $ mas_xiangqi_result_reason = _return["reason"]
            call mas_xiangqi_result_draw
            return

        m 1eua "那我们下次再继续。"
        return

    return


label mas_xiangqi_pick_difficulty:
    m 1eua "这次想用什么难度和我下呢？"

    menu:
        "选择难度"
        "轻松":
            $ persistent._mas_xiangqi_difficulty = "easy"
            m 3hub "那我就稍微放慢一点节奏。"
        "标准":
            $ persistent._mas_xiangqi_difficulty = "normal"
            m 1hub "好，那就认真地下。"
        "挑战":
            $ persistent._mas_xiangqi_difficulty = "hard"
            m 2eub "想给我出难题吗？我会更仔细地思考。"
        "大师":
            $ persistent._mas_xiangqi_difficulty = "master"
            m 2tub "看来你是真的来挑战我的。"

    return


label mas_xiangqi_result_win:
    if mas_xiangqi_result_reason == "checkmate":
        m 1wub "欸，居然真让你把我将死了。"
        m 3hub "这盘是你下得更好，我认输。"
    elif mas_xiangqi_result_reason == "king_captured":
        m 1hub "你直接把我的将吃掉了，这一手很干脆。"
    else:
        m 1hub "这局是你赢了，厉害哦。"

    m 3eua "要是你愿意的话，我们随时可以再来一盘。"
    return


label mas_xiangqi_result_loss:
    if mas_xiangqi_result_reason == "surrender":
        m 1eka "没关系，认输也算是战略选择。"
        m 3hub "等你准备好了，我们再重新来过。"
    elif mas_xiangqi_result_reason == "checkmate":
        m 1hub "将死。看来这盘是我赢了。"
        m 3tub "不过你已经给我制造了不少麻烦呢。"
    else:
        m 1hub "这盘就算我小胜一局啦。"

    m 1eua "再来几盘的话，你肯定会越来越顺手的。"
    return


label mas_xiangqi_result_draw:
    if mas_xiangqi_result_reason == "threefold":
        m 1eua "我们重复到第三次同一局面了，按约定这盘算和棋。"
    else:
        m 1eua "这盘没有合法着法了，所以判和。"

    m 3hub "势均力敌的感觉也很不错，不是吗？"
    return
