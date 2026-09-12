import asyncio
import pygame
import random

pygame.init()

async def main():
    # --- 基準となるウィンドウサイズ ---
    BASE_W, BASE_H = 256, 240
    SCREEN_W, SCREEN_H = BASE_W*2, BASE_H*2

    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    # -------------------------
    # 背景
    # -------------------------
    bg = pygame.image.load("background.png").convert()
    bg_x = 0
    SCROLL_SPEED = 6

    last_switch = pygame.time.get_ticks()
    current_frame = 0

    # --- スコア ---
    score = 0
    raw_scores = [
        pygame.image.load("0.png").convert_alpha(),
        pygame.image.load("1.png").convert_alpha(),
        pygame.image.load("2.png").convert_alpha(),
        pygame.image.load("3.png").convert_alpha(),
        pygame.image.load("4.png").convert_alpha(),
        pygame.image.load("5.png").convert_alpha(),
        pygame.image.load("6.png").convert_alpha(),
        pygame.image.load("7.png").convert_alpha(),
        pygame.image.load("8.png").convert_alpha(),
        pygame.image.load("9.png").convert_alpha(),
    ]

    # --- キャラの状態 ---
    state = "run"  # "run" or "jump_up" or "jump_down" or "damaged"
    ANIMATION_SWITCH_TIME = 200 * 3 // SCROLL_SPEED

    # ジャンプ物理
    GRAVITY = 0.5
    JUMP_POWER = -11
    JUMP_CUT = -2
    jump_hold = False
    vy = 0
    y_offset = 0
    GROUND_Y = 177

    # ダメージ処理
    damaged_timer = 0
    DAMAGED_INTERVAL = 400  # ミリ秒

    # --- 元画像 ---
    raw_frames = {
        "run": [
            pygame.image.load("run0.png").convert_alpha(),
            pygame.image.load("run1.png").convert_alpha(),
            pygame.image.load("run2.png").convert_alpha(),
            pygame.image.load("run3.png").convert_alpha(),
        ],
        "jump_up": [
            pygame.image.load("jump_up0.png").convert_alpha(),
            pygame.image.load("jump_up1.png").convert_alpha(),
        ],
        "jump_down": [
            pygame.image.load("jump_down0.png").convert_alpha(),
            pygame.image.load("jump_down1.png").convert_alpha(),
        ],
        "damaged": [
            pygame.image.load("damaged0.png").convert_alpha(),
            pygame.image.load("damaged1.png").convert_alpha(),
        ]
    }

    # -------------------------
    # 敵
    # -------------------------
    enemy_raw = [
        pygame.image.load("enemy0.png").convert_alpha(),
        pygame.image.load("enemy1.png").convert_alpha()
    ]
    enemy_x = SCREEN_W

    # 敵を出す間隔
    enemy_timer = 0
    ENEMY_INTERVAL = 2000  # ミリ秒

    # --- スケール済み画像キャッシュ ---
    scaled_frames = {}
    enemy_scaled_frames = []
    score_scaled_frames = []
    prev_scale = None  # スケール変更検出用

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # 被ダメ時は何もしない
            if state == "damaged":
                continue

            # マウスクリックでジャンプ開始
            if event.type == pygame.MOUSEBUTTONDOWN:
                # 再開時
                if state == "stop":
                    state = "run"
                    score = 0

                elif y_offset == 0:      # 地面にいる
                    vy = JUMP_POWER    # ジャンプの初速
                    jump_hold = True   # ジャンプクリック中
                    state = "jump_up"  # 上昇中のモーション
                    current_frame = 0  # アニメーションのフレームを初期化

            if event.type == pygame.MOUSEBUTTONUP:
                jump_hold = False

        # 停止中
        if state == "stop":
            await asyncio.sleep(0)
            continue

        # --- 現在のウィンドウサイズ ---
        win_w, win_h = screen.get_size()

        # --- ウィンドウサイズからスケールを計算 ---
        scale_x = win_w / BASE_W
        scale_y = win_h / BASE_H
        SCALE = min(scale_x, scale_y)  # 縦横比を維持

        # --- スケールが変わったときだけ再生成 ---
        if SCALE != prev_scale:
            # プレイヤー
            scaled_frames.clear()

            for key, imgs in raw_frames.items():
                scaled_list = []
                for img in imgs:
                    w, h = img.get_size()
                    scaled = pygame.transform.scale(
                        img,
                        (int(w * SCALE), int(h * SCALE))
                    )
                    scaled_list.append(scaled)
                scaled_frames[key] = scaled_list

            # 敵キャラ
            enemy_scaled_frames.clear()
            for img in enemy_raw:
                w, h = img.get_size()
                scaled = pygame.transform.scale(
                    img,
                    (int(w * SCALE), int(h * SCALE))
                )
                enemy_scaled_frames.append(scaled)

            # スコア
            score_scaled_frames.clear()
            for img in raw_scores:
                w, h = img.get_size()
                scaled = pygame.transform.scale(
                    img,
                    (int(w * SCALE), int(h * SCALE))
                )
                score_scaled_frames.append(scaled)

            prev_scale = SCALE
            current_frame = 0
            last_switch = pygame.time.get_ticks()

        # -------------------------
        # ジャンプ物理処理
        # -------------------------
        if y_offset != 0 or vy != 0:
            # 重力
            vy += GRAVITY

            # ジャンプカット
            if not jump_hold and vy < JUMP_CUT:
                if state != "damaged":
                    vy = JUMP_CUT

            y_offset += vy

            # 状態切り替え
            if state != "damaged":
                if vy < 0:
                    state = "jump_up"
                else:
                    state = "jump_down"

            # 着地
            if y_offset > 0:
                y_offset = 0
                vy = 0
                if state != "damaged":
                    state = "run"

        # -------------------------
        # 背景スクロール
        # -------------------------
        if bg_x <= -win_w:
            bg_x = 0

        bg_scaled = pygame.transform.scale(bg, (win_w, win_h))

        screen.blit(bg_scaled, (bg_x, 0))
        screen.blit(bg_scaled, (bg_x + win_w, 0))

        bg_x -= SCROLL_SPEED

        # -------------------------
        # 敵を出す
        # -------------------------
        now = pygame.time.get_ticks()

        if now - enemy_timer >= ENEMY_INTERVAL:
            enemy_x = win_w
            enemy_timer = now + random.randint(-2, 2)*150

        # 敵を左へ移動
        enemy_x -= SCROLL_SPEED

        # -------------------------
        # アニメーション
        # -------------------------
        frames = scaled_frames[state]

        if now - last_switch >= ANIMATION_SWITCH_TIME:
            current_frame = (current_frame + 1) % len(frames)
            last_switch = now
            if state != "damaged":
                score += 1
            # スピードアップ
            if score > 0 and score % 25 == 0:
                SCROLL_SPEED += 1

        img = frames[current_frame]

        # --- プレイヤー ---
        player_x = (win_w - img.get_width()) // 5
        base_y = (GROUND_Y * SCALE) - img.get_height()
        player_y = base_y + y_offset

        screen.blit(img, (player_x, player_y))

        # -------------------------
        # 敵を描画
        # -------------------------
        index = current_frame % len(enemy_raw)
        enemy_img = enemy_scaled_frames[index]
        enemy_y = (GROUND_Y * SCALE) - enemy_img.get_height()

        screen.blit(enemy_img, (enemy_x, enemy_y))

        # -------------------------
        # スコアを描画
        # -------------------------
        for i, num in enumerate(reversed(str(score))):
            num_img = score_scaled_frames[int(num)]
            screen.blit(num_img, (BASE_W*SCALE - (i+2)*8*SCALE, 16*SCALE))

        # -------------------------
        # 当たり判定
        # -------------------------
        player_rect = pygame.Rect(
            player_x,
            player_y,
            img.get_width(),
            img.get_height()
        )

        enemy_rect = pygame.Rect(
            enemy_x,
            enemy_y,
            enemy_img.get_width(),
            enemy_img.get_height()
        )

        # 衝突時は被ダメ状態へ
        if state != "damaged":
            if player_rect.colliderect(enemy_rect):
                state = "damaged"
                current_frame = 0
                damaged_timer = now
                SCROLL_SPEED = 6

        # 時間経過で一旦停止
        else:
            if now - damaged_timer >= DAMAGED_INTERVAL:
                state = "stop"
                current_frame = 0

        # 画面を更新
        pygame.display.flip()

        # 待ち時間
        clock.tick(60)

        await asyncio.sleep(0)

    pygame.quit()


asyncio.run(main())
