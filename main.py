import asyncio
import pygame
import random

pygame.init()


async def main():
    # =========================================================
    # 基本設定
    # =========================================================
    BASE_W = 256
    BASE_H = 240

    # 実際のウィンドウ
    SCREEN_W = BASE_W * 2
    SCREEN_H = BASE_H * 2
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
    clock = pygame.time.Clock()

    # =========================================================
    # 背景
    # =========================================================
    bg = pygame.image.load("background.png").convert()

    # ゲーム内部では「256×240」の座標系で管理する
    bg_x = 0.0

    # pixels / second
    SCROLL_SPEED = 216.0
    INITIAL_SCROLL_SPEED = 216.0

    # =========================================================
    # スコア
    # =========================================================
    score = 0
    raw_scores = [pygame.image.load(f"{i}.png").convert_alpha() for i in range(10)]

    # =========================================================
    # キャラクター
    # =========================================================
    state = "run"
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

    # =========================================================
    # ジャンプ物理
    # =========================================================
    # すべて「1秒あたり」の値
    GRAVITY = 1200.0
    JUMP_POWER = -450.0

    # ジャンプを途中で切るときの速度
    JUMP_CUT = -100.0
    jump_hold = False

    # 縦方向の速度
    vy = 0.0

    # 地面からの相対位置
    y_offset = 0.0

    # 論理座標上の地面
    GROUND_Y = 177.0

    # =========================================================
    # ダメージ
    # =========================================================
    damaged_timer = 0
    DAMAGED_INTERVAL = 400  # ms

    # =========================================================
    # 敵
    # =========================================================
    enemy_raw = [
        pygame.image.load("enemy0.png").convert_alpha(),
        pygame.image.load("enemy1.png").convert_alpha()
    ]

    # 論理座標
    enemy_x = float(BASE_W)
    enemy_timer = 0
    ENEMY_INTERVAL = 2000

    # =========================================================
    # アニメーション
    # =========================================================
    ANIMATION_SWITCH_TIME = 100  # ms
    last_switch = pygame.time.get_ticks()
    current_frame = 0

    # =========================================================
    # スケール済み画像キャッシュ
    # =========================================================
    scaled_frames = {}
    enemy_scaled_frames = []
    score_scaled_frames = []
    prev_scale = None

    # =========================================================
    # ゲームループ
    # =========================================================
    running = True
    while running:
        # -----------------------------------------------------
        # dt
        # -----------------------------------------------------
        #
        # clock.tick() は「このフレームに何msかかったか」を返す
        #
        # 例えば
        # 60 FPS → 約0.0167秒
        # 30 FPS → 約0.0333秒
        #
        # これを使ってゲームを時間ベースで動かす
        # -----------------------------------------------------
        if state != "stop":
            dt = clock.tick(60) / 1000.0

            # Web環境などで極端に重くなった場合に
            # 1フレームでゲームが飛びすぎるのを防ぐ
            dt = min(dt, 0.05)

        # -----------------------------------------------------
        # イベント
        # -----------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # 被ダメ中は操作を受け付けない
            if state == "damaged":
                continue

            # -------------------------------------------------
            # マウスクリック
            # -------------------------------------------------
            if event.type == pygame.MOUSEBUTTONDOWN:
                # ゲームオーバー後の再開
                if state == "stop":
                    state = "run"
                    score = 0

                # 地面にいる場合のみジャンプ
                elif y_offset == 0:
                    vy = JUMP_POWER
                    jump_hold = True
                    state = "jump_up"
                    current_frame = 0

            # -------------------------------------------------
            # マウスを離した
            # -------------------------------------------------
            if event.type == pygame.MOUSEBUTTONUP:
                jump_hold = False

        # -----------------------------------------------------
        # 停止中
        # -----------------------------------------------------
        if state == "stop":
            await asyncio.sleep(0)
            continue

        # =====================================================
        # 現在のウィンドウサイズ
        # =====================================================
        win_w, win_h = screen.get_size()

        # =====================================================
        # SCALE
        # =====================================================
        scale_x = win_w / BASE_W
        scale_y = win_h / BASE_H
        SCALE = max(scale_x, scale_y)

        game_w = BASE_W * SCALE
        game_h = BASE_H * SCALE

        offset_x = (win_w - game_w) / 2
        offset_y = (win_h - game_h) / 2

        # =====================================================
        # スケール済み画像を作成
        # =====================================================
        if SCALE != prev_scale:
            # -------------------------------------------------
            # プレイヤー
            # -------------------------------------------------
            scaled_frames.clear()
            for key, imgs in raw_frames.items():
                scaled_list = []
                for img in imgs:
                    w, h = img.get_size()
                    scaled = pygame.transform.scale(img, (int(w * SCALE), int(h * SCALE)))
                    scaled_list.append(scaled)

                scaled_frames[key] = scaled_list

            # -------------------------------------------------
            # 敵
            # -------------------------------------------------
            enemy_scaled_frames.clear()
            for img in enemy_raw:
                w, h = img.get_size()
                scaled = pygame.transform.scale(img, (int(w * SCALE), int(h * SCALE)))
                enemy_scaled_frames.append(scaled)

            # -------------------------------------------------
            # スコア
            # -------------------------------------------------
            score_scaled_frames.clear()
            for img in raw_scores:
                w, h = img.get_size()
                scaled = pygame.transform.scale(img, (int(w * SCALE), int(h * SCALE)))
                score_scaled_frames.append(scaled)

            prev_scale = SCALE
            current_frame = 0
            last_switch = pygame.time.get_ticks()

        # =====================================================
        # ジャンプ物理
        # =====================================================
        if y_offset != 0 or vy != 0:
            # 重力
            vy += GRAVITY * dt

            # ---------------------------------------------
            # ジャンプボタンを離した場合
            # ---------------------------------------------
            if not jump_hold and vy < JUMP_CUT:
                if state != "damaged":
                    vy = JUMP_CUT

            # ---------------------------------------------
            # 移動
            # ---------------------------------------------
            y_offset += vy * dt

            # ---------------------------------------------
            # 状態切り替え
            # ---------------------------------------------
            if state != "damaged":
                if vy < 0:
                    state = "jump_up"
                else:
                    state = "jump_down"

            # ---------------------------------------------
            # 着地
            # ---------------------------------------------
            if y_offset > 0:
                y_offset = 0.0
                vy = 0.0
                if state != "damaged":
                    state = "run"

        # =====================================================
        # 背景スクロール
        # =====================================================
        bg_x -= SCROLL_SPEED * dt

        # 背景1枚分移動したら戻す
        if bg_x <= -BASE_W:
            bg_x += BASE_W

        # -----------------------------------------------------
        # 背景を論理座標で扱う
        # -----------------------------------------------------
        bg_scaled = pygame.transform.scale(bg, (int(BASE_W * SCALE), int(BASE_H * SCALE)))

        # 実際の画面上の位置に変換
        bg_screen_x = int(offset_x + bg_x * SCALE)
        screen.blit(bg_scaled, (bg_screen_x, 0))
        screen.blit(bg_scaled, (bg_screen_x + int(BASE_W * SCALE), 0))

        # =====================================================
        # 敵を出す
        # =====================================================
        now = pygame.time.get_ticks()
        if now - enemy_timer >= ENEMY_INTERVAL:
            enemy_x = float(BASE_W)
            enemy_timer = (now + random.randint(-2, 2) * 150)

        # -----------------------------------------------------
        # 敵を移動
        # -----------------------------------------------------
        enemy_x -= SCROLL_SPEED * dt

        # =====================================================
        # アニメーション
        # =====================================================
        frames = scaled_frames[state]
        if now - last_switch >= ANIMATION_SWITCH_TIME:
            current_frame = (current_frame + 1) % len(frames)
            last_switch = now

            # 被ダメ中以外はスコア加算
            if state != "damaged":
                score += 1

            # -------------------------------------------------
            # スピードアップ
            # -------------------------------------------------
            if score > 0 and score % 25 == 0:
                SCROLL_SPEED += 30

        # =====================================================
        # プレイヤー
        # =====================================================
        img = frames[current_frame]

        # -----------------------------------------------------
        # 論理座標でキャラクター位置を計算
        # -----------------------------------------------------
        player_w = img.get_width() / SCALE
        player_h = img.get_height() / SCALE
        player_x = (BASE_W - player_w) / 5

        # 地面のY座標
        base_y = (GROUND_Y - player_h)

        # ジャンプによるY移動
        player_y = base_y + y_offset

        # -----------------------------------------------------
        # 実際の画面座標へ変換
        # -----------------------------------------------------
        player_screen_x = int(offset_x + player_x * SCALE)
        player_screen_y = int(offset_y + player_y * SCALE)
        screen.blit(img, (player_screen_x, player_screen_y))

        # =====================================================
        # 敵
        # =====================================================
        index = (current_frame % len(enemy_raw))
        enemy_img = enemy_scaled_frames[index]
        enemy_w = enemy_img.get_width() / SCALE
        enemy_h = enemy_img.get_height() / SCALE
        enemy_y = (GROUND_Y - enemy_h)

        # 論理座標 → 画面座標
        enemy_screen_x = int(offset_x + enemy_x * SCALE)
        enemy_screen_y = int(offset_y + enemy_y * SCALE)
        screen.blit(enemy_img, (enemy_screen_x, enemy_screen_y))

        # =====================================================
        # スコア
        # =====================================================
        for i, num in enumerate(reversed(str(score))):
            num_img = score_scaled_frames[int(num)]
            score_x = offset_x + BASE_W * SCALE - (i + 2) * 8 * SCALE
            score_y = offset_y + 16 * SCALE
            screen.blit(num_img, (int(score_x), int(score_y)))

        # =====================================================
        # 当たり判定
        # =====================================================
        #
        # 衝突判定は「論理座標」で行う
        # SCALE済み画面座標では判定しない
        # =====================================================
        player_rect = pygame.Rect(
            int(player_x),
            int(player_y),
            int(player_w),
            int(player_h)
        )

        enemy_rect = pygame.Rect(
            int(enemy_x),
            int(enemy_y),
            int(enemy_w),
            int(enemy_h)
        )

        # -----------------------------------------------------
        # 衝突
        # -----------------------------------------------------
        if state != "damaged":
            if player_rect.colliderect(
                enemy_rect
            ):
                state = "damaged"
                current_frame = 0
                damaged_timer = now

                # 初期速度に戻す
                SCROLL_SPEED = INITIAL_SCROLL_SPEED

        # =====================================================
        # ダメージ状態
        # =====================================================
        else:
            if now - damaged_timer >= DAMAGED_INTERVAL:
                state = "stop"
                current_frame = 0

        # =====================================================
        # 画面更新
        # =====================================================
        pygame.display.flip()

        # -----------------------------------------------------
        # pygbag / ブラウザに処理を返す
        # -----------------------------------------------------
        await asyncio.sleep(0)

    # =========================================================
    # 終了
    # =========================================================
    pygame.quit()


asyncio.run(main())
