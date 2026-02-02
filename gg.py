import math
import random

import arcade


SCREEN_WIDTH, SCREEN_HEIGHT = arcade.get_display_size()
SCREEN_TITLE = "Castle Shooter"

FPS = 60
TILE_SIZE = 50

BLACK = (10, 10, 10)
FLOOR_COLOR = (40, 30, 30)
WALL_COLOR = (80, 60, 60)
WHITE = (255, 255, 255)
RED = (200, 50, 50)
GREEN = (50, 200, 50)
PURPLE = (150, 50, 200)
YELLOW = (255, 255, 0)
PORTAL_COLOR = (0, 255, 255)
GOLD = (255, 215, 0)
DARK_RED = (100, 20, 20)
STONE = (120, 100, 80)


def load_texture_safe(path, size, color, flipped_horizontally=False):
    try:
        texture = arcade.load_texture(path, flipped_horizontally=flipped_horizontally)
        scale = min(size[0] / texture.width, size[1] / texture.height) if size else 1.0
        return texture, scale
    except OSError:
        texture = arcade.make_soft_square_texture(size[0], color, 255, 0)
        return texture, 1.0


def load_sound_safe(path):
    try:
        return arcade.load_sound(path)
    except OSError:
        return None


player_shoot_sound = load_sound_safe("shoot.wav")
enemy_shoot_sound = load_sound_safe("enemy_shot.wav")
teleport_sound = load_sound_safe("teleport.wav")
death_sound = load_sound_safe("death.wav")
lose_sound = load_sound_safe("lose_sound.mp3")
win_sound = load_sound_safe("win_sound.mp3")
music = load_sound_safe("music.mp3")


class Button:
    def __init__(self, x, y, width, height, text, color):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.color = color
        self.hover = False

    @property
    def rect(self):
        return (
            self.x - self.width / 2,
            self.y - self.height / 2,
            self.width,
            self.height,
        )

    def draw(self):
        x, y, width, height = self.rect
        if self.hover:
            arcade.draw_rectangle_outline(self.x, self.y, width + 10, height + 10, GOLD, 2)
        arcade.draw_rectangle_filled(self.x, self.y, width, height, self.color)
        arcade.draw_rectangle_outline(self.x, self.y, width, height, GOLD, 4)
        arcade.draw_text(
            self.text,
            self.x,
            self.y,
            GOLD if not self.hover else WHITE,
            font_size=24,
            anchor_x="center",
            anchor_y="center",
            font_name="Georgia",
        )

    def check_hover(self, pos):
        x, y, width, height = self.rect
        self.hover = x <= pos[0] <= x + width and y <= pos[1] <= y + height
        return self.hover

    def is_clicked(self, pos):
        x, y, width, height = self.rect
        return x <= pos[0] <= x + width and y <= pos[1] <= y + height


class Corpse(arcade.Sprite):
    def __init__(self, x, y, texture):
        super().__init__(texture=texture, center_x=x, center_y=y)
        self.lifetime = 300

    def update(self):
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.remove_from_sprite_lists()
        elif self.lifetime < 60:
            self.alpha = int((self.lifetime / 60) * 255)


class Wall(arcade.Sprite):
    def __init__(self, x, y):
        texture = arcade.make_soft_square_texture(TILE_SIZE, WALL_COLOR, 255, 0)
        super().__init__(texture=texture)
        self.center_x = x * TILE_SIZE + TILE_SIZE / 2
        self.center_y = y * TILE_SIZE + TILE_SIZE / 2


class Portal(arcade.Sprite):
    def __init__(self, x, y):
        texture, scale = load_texture_safe("portal.png", (150, 150), PORTAL_COLOR)
        super().__init__(texture=texture, scale=scale)
        self.center_x = x * TILE_SIZE + TILE_SIZE / 2
        self.center_y = y * TILE_SIZE + TILE_SIZE / 2


class Bullet(arcade.Sprite):
    def __init__(self, x, y, angle, is_player=True):
        if is_player:
            texture, scale = load_texture_safe("player_bullet.png", (30, 30), YELLOW)
            speed = 10
            damage = 25
            sound = player_shoot_sound
        else:
            texture = arcade.make_soft_square_texture(20, RED, 255, 0)
            scale = 1.0
            speed = 6
            damage = 15
            sound = enemy_shoot_sound

        super().__init__(texture=texture, scale=scale, center_x=x, center_y=y)
        self.change_x = math.cos(angle) * speed
        self.change_y = math.sin(angle) * speed
        self.damage = damage
        self.lifetime = 50
        if sound:
            arcade.play_sound(sound, volume=0.3)

    def update(self):
        self.center_x += self.change_x
        self.center_y += self.change_y
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.remove_from_sprite_lists()


class Player(arcade.Sprite):
    def __init__(self, x, y):
        texture_right, scale = load_texture_safe("player.png", (75, 75), GREEN)
        texture_left, _ = load_texture_safe("player.png", (75, 75), GREEN, flipped_horizontally=True)
        self.texture_right = texture_right
        self.texture_left = texture_left
        super().__init__(texture=self.texture_right, scale=scale, center_x=x, center_y=y)
        self.speed = 5
        self.hp = 100
        self.max_hp = 100
        self.last_shot = 0
        self.face_right = True

    def update(self):
        self.center_x += self.change_x
        self.center_y += self.change_y

    def update_direction(self):
        if self.change_x < 0 and self.face_right:
            self.texture = self.texture_left
            self.face_right = False
        elif self.change_x > 0 and not self.face_right:
            self.texture = self.texture_right
            self.face_right = True


class Enemy(arcade.Sprite):
    def __init__(self, x, y, player, kind, textures, walls):
        texture, scale = textures[kind]
        super().__init__(texture=texture, scale=scale, center_x=x, center_y=y)
        self.player = player
        self.kind = kind
        self.walls = walls
        self.aggro = False
        self.aggro_range = 200
        if kind == "weak":
            self.hp = 30
            self.max_hp = 30
            self.speed = 3
        elif kind == "norm":
            self.hp = 60
            self.max_hp = 60
            self.speed = 2
        else:
            self.hp = 300
            self.max_hp = 300
            self.speed = 2
            self.aggro_range = 350
        self.last_shot = 0

    def update(self, delta_time: float = 1 / 60):
        if not self.player:
            return
        dx = self.player.center_x - self.center_x
        dy = self.player.center_y - self.center_y
        dist = math.hypot(dx, dy)
        if dist < self.aggro_range:
            self.aggro = True
        if not self.aggro:
            return
        if dist != 0:
            dx, dy = dx / dist, dy / dist
        if dist > 50:
            self.center_x += dx * self.speed
            if arcade.check_for_collision_with_list(self, self.walls):
                self.center_x -= dx * self.speed
            self.center_y += dy * self.speed
            if arcade.check_for_collision_with_list(self, self.walls):
                self.center_y -= dy * self.speed


MAP1 = [
    "#########################################################",
    "#............#.................................#........#",
    "#....P.......#.............................w...#....n...#",
    "#............#.................................#........#",
    "#............#..w..#....................########........#",
    "#............#.....#....................................#",
    "#............#######....................................#",
    "#..........................#...........n................#",
    "#..........................#...................####.....#",
    "#..........................#...................#........#",
    "##############.........n...#...................#........#",
    "#..........................#...................#....w...#",
    "#..........................#......w............#........#",
    "#...............############...........##################",
    "#...............#.......................................#",
    "#...............#.....w.................................#",
    "#...............#...................................n...#",
    "#...............#.......................................#",
    "#...............###########.............................#",
    "#...................................##############......#",
    "#....n.....................................#............#",
    "#..........................................#............#",
    "#.............................#............#......N.....#",
    "#.................w...........#.......w....#............#",
    "#.............................#............#............#",
    "#########################################################",
]

MAP2 = [
    "#########################################################",
    "#.......................................................#",
    "#...............n..............w..................P.....#",
    "#.......................................................#",
    "#.......................................................#",
    "#....w......#############################################",
    "#.......................................................#",
    "#...................n...............w...................#",
    "#.......................................................#",
    "###############################................w........#",
    "#.......................................................#",
    "#...........w..............n............................#",
    "#.......................................................#",
    "#.................................#######################",
    "#.......................................................#",
    "#............n.............................w............#",
    "#.......................................................#",
    "##################################################......#",
    "#...........#...........................................#",
    "#...........#...........................................#",
    "#.......................................................#",
    "#........................B..............................#",
    "#.......................................................#",
    "#...........#...........................................#",
    "#...........#...........................................#",
    "#########################################################",
]


class CastleShooter(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, fullscreen=True, update_rate=1 / FPS)
        arcade.set_background_color(BLACK)
        self.state = "menu"
        self.current_level = 1
        self.player = None
        camera_cls = getattr(arcade, "Camera", arcade.camera.Camera)
        self.camera = camera_cls(self.width, self.height)
        self.all_sprites = arcade.SpriteList()
        self.walls = arcade.SpriteList()
        self.bullets = arcade.SpriteList()
        self.enemy_bullets = arcade.SpriteList()
        self.enemies = arcade.SpriteList()
        self.portals = arcade.SpriteList()
        self.corpses = arcade.SpriteList()
        self.level_width = 0
        self.level_height = 0
        self.keys = set()
        self.play_button = Button(self.width / 2, self.height / 2, 300, 70, "START GAME", DARK_RED)
        self.quit_button = Button(self.width / 2, self.height / 2 - 100, 300, 70, "LEAVE", (60, 30, 30))
        self.enemy_textures = {
            "weak": load_texture_safe("enemy_weak.png", (100, 150), RED),
            "norm": load_texture_safe("enemy_weak.png", (140, 200), PURPLE),
            "boss": load_texture_safe("enemy_boss.png", (250, 250), GOLD),
        }
        self.death_textures = {
            "weak": arcade.make_soft_square_texture(35, RED, 255, 0),
            "norm": arcade.make_soft_square_texture(40, RED, 255, 0),
            "boss": arcade.make_soft_square_texture(80, RED, 255, 0),
        }
        if music:
            arcade.play_sound(music, volume=0.2, looping=True)

    def setup_level(self, level_num):
        if teleport_sound:
            arcade.play_sound(teleport_sound, volume=0.5)
        self.all_sprites = arcade.SpriteList()
        self.walls = arcade.SpriteList()
        self.bullets = arcade.SpriteList()
        self.enemy_bullets = arcade.SpriteList()
        self.enemies = arcade.SpriteList()
        self.portals = arcade.SpriteList()
        self.corpses = arcade.SpriteList()
        current_map = MAP1 if level_num == 1 else MAP2
        self.level_width = len(current_map[0]) * TILE_SIZE
        self.level_height = len(current_map) * TILE_SIZE
        self.player = None

        for row_idx, row in enumerate(current_map):
            for col_idx, char in enumerate(row):
                x = col_idx * TILE_SIZE + TILE_SIZE / 2
                y = row_idx * TILE_SIZE + TILE_SIZE / 2
                if char == "#":
                    wall = Wall(col_idx, row_idx)
                    self.all_sprites.append(wall)
                    self.walls.append(wall)
                elif char == "P":
                    self.player = Player(x, y)
                    self.all_sprites.append(self.player)
                elif char in {"w", "n", "B"}:
                    kind = "weak" if char == "w" else "norm" if char == "n" else "boss"
                    enemy = Enemy(x, y, None, kind, self.enemy_textures, self.walls)
                    self.all_sprites.append(enemy)
                    self.enemies.append(enemy)
                elif char == "N":
                    portal = Portal(col_idx, row_idx)
                    self.all_sprites.append(portal)
                    self.portals.append(portal)

        for enemy in self.enemies:
            enemy.player = self.player

    def on_draw(self):
        arcade.start_render()
        if self.state == "menu":
            self.draw_menu()
            return

        self.camera.use()
        arcade.draw_rectangle_filled(
            self.level_width / 2,
            self.level_height / 2,
            self.level_width,
            self.level_height,
            FLOOR_COLOR,
        )
        self.all_sprites.draw()
        self.draw_fog_of_war()

        self.camera.use()
        self.draw_hud()

    def draw_menu(self):
        self.draw_medieval_background()
        arcade.draw_text(
            "CASTLE SHOOTERS",
            self.width / 2,
            self.height / 2 + 200,
            GOLD,
            font_size=48,
            font_name="Georgia",
            anchor_x="center",
        )
        self.play_button.draw()
        self.quit_button.draw()

    def draw_medieval_background(self):
        arcade.draw_rectangle_filled(self.width / 2, self.height / 2, self.width, self.height, (20, 15, 10))
        for _ in range(50):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            size = random.randint(30, 100)
            arcade.draw_circle_filled(x, y, size, STONE)
        frame_thickness = 30
        arcade.draw_rectangle_filled(self.width / 2, frame_thickness / 2, self.width, frame_thickness, STONE)
        arcade.draw_rectangle_filled(
            self.width / 2, self.height - frame_thickness / 2, self.width, frame_thickness, STONE
        )
        arcade.draw_rectangle_filled(frame_thickness / 2, self.height / 2, frame_thickness, self.height, STONE)
        arcade.draw_rectangle_filled(
            self.width - frame_thickness / 2, self.height / 2, frame_thickness, self.height, STONE
        )

    def draw_fog_of_war(self):
        if not self.player:
            return
        arcade.draw_rectangle_filled(
            self.player.center_x,
            self.player.center_y,
            self.level_width,
            self.level_height,
            (0, 0, 0, 170),
        )
        arcade.draw_circle_filled(self.player.center_x, self.player.center_y, 220, (0, 0, 0, 60))

    def draw_hud(self):
        arcade.set_viewport(0, self.width, 0, self.height)
        hp_ratio = max(0, self.player.hp / self.player.max_hp) if self.player else 0
        fill = int(200 * hp_ratio)
        color = GREEN if hp_ratio > 0.6 else YELLOW if hp_ratio > 0.3 else RED
        arcade.draw_rectangle_filled(10 + fill / 2, self.height - 20, fill, 20, color)
        arcade.draw_rectangle_outline(110, self.height - 20, 200, 20, WHITE, 2)
        arcade.draw_text(f"HP: {self.player.hp}/{self.player.max_hp}", 10, self.height - 45, WHITE, 14)
        arcade.draw_text(f"Enemies lefts: {len(self.enemies)}", 10, self.height - 70, WHITE, 14)
        arcade.draw_text(f"Current level: {self.current_level}", 10, self.height - 95, WHITE, 14)
        if self.state == "game_over":
            arcade.draw_text(
                "DEFEAT",
                self.width / 2,
                self.height / 2 + 20,
                RED,
                48,
                anchor_x="center",
            )
            arcade.draw_text("Press SPACE", self.width / 2, self.height / 2 - 20, WHITE, 20, anchor_x="center")
        if self.state == "victory":
            arcade.draw_text(
                "VICTORY!",
                self.width / 2,
                self.height / 2 + 20,
                GOLD,
                48,
                anchor_x="center",
            )
            arcade.draw_text("Press SPACE", self.width / 2, self.height / 2 - 20, WHITE, 20, anchor_x="center")

    def on_update(self, delta_time: float):
        if self.state != "game":
            return

        self.handle_player_movement()
        self.player.update_direction()
        self.enemies.update()
        self.bullets.update()
        self.enemy_bullets.update()
        self.corpses.update()

        for bullet in list(self.bullets):
            if arcade.check_for_collision_with_list(bullet, self.walls):
                bullet.remove_from_sprite_lists()

        for bullet in list(self.enemy_bullets):
            if arcade.check_for_collision_with_list(bullet, self.walls):
                bullet.remove_from_sprite_lists()

        hits = arcade.check_for_collision_with_list(self.player, self.enemy_bullets)
        for hit_bullet in hits:
            self.player.hp -= hit_bullet.damage
            hit_bullet.remove_from_sprite_lists()
            if self.player.hp < 0:
                self.player.hp = 0

        hits = arcade.check_for_collision_with_list(self.player, self.portals)
        if hits and self.current_level == 1 and len(self.enemies) == 0:
            self.current_level = 2
            self.setup_level(self.current_level)

        for enemy in list(self.enemies):
            if enemy.hp <= 0:
                if death_sound:
                    arcade.play_sound(death_sound, volume=0.5)
                corpse = Corpse(enemy.center_x, enemy.center_y, self.death_textures[enemy.kind])
                self.corpses.append(corpse)
                self.all_sprites.append(corpse)
                enemy.remove_from_sprite_lists()
            else:
                self.handle_enemy_shoot(enemy)

        for enemy in list(self.enemies):
            hits = arcade.check_for_collision_with_list(enemy, self.bullets)
            for bullet in hits:
                enemy.hp -= 10
                enemy.aggro = True
                bullet.remove_from_sprite_lists()

        if self.player.hp <= 0 and self.state == "game":
            if lose_sound:
                arcade.play_sound(lose_sound, volume=0.3)
            self.state = "game_over"

        if self.current_level == 2 and len(self.enemies) == 0 and self.state == "game":
            if win_sound:
                arcade.play_sound(win_sound, volume=0.7)
            self.state = "victory"

        self.center_camera_to_player()

    def handle_enemy_shoot(self, enemy):
        if not self.player:
            return
        dx = self.player.center_x - enemy.center_x
        dy = self.player.center_y - enemy.center_y
        dist = math.hypot(dx, dy)
        if dist < 500:
            now = arcade.get_time()
            delay = 1.2 if enemy.kind != "boss" else 0.6
            if now - enemy.last_shot > delay:
                enemy.last_shot = now
                angle = math.atan2(dy, dx)
                bullet = Bullet(enemy.center_x, enemy.center_y, angle, is_player=False)
                self.enemy_bullets.append(bullet)
                self.all_sprites.append(bullet)

    def center_camera_to_player(self):
        if not self.player:
            return
        screen_center_x = self.player.center_x - self.width / 2
        screen_center_y = self.player.center_y - self.height / 2
        screen_center_x = max(0, min(screen_center_x, self.level_width - self.width))
        screen_center_y = max(0, min(screen_center_y, self.level_height - self.height))
        self.camera.move_to((screen_center_x, screen_center_y), 0.15)

    def handle_player_movement(self):
        if not self.player:
            return
        dx = 0
        dy = 0
        if arcade.key.W in self.keys or arcade.key.UP in self.keys:
            dy += self.player.speed
        if arcade.key.S in self.keys or arcade.key.DOWN in self.keys:
            dy -= self.player.speed
        if arcade.key.A in self.keys or arcade.key.LEFT in self.keys:
            dx -= self.player.speed
        if arcade.key.D in self.keys or arcade.key.RIGHT in self.keys:
            dx += self.player.speed
        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707

        self.player.change_x = dx
        self.player.change_y = dy
        self.player.center_x += dx
        if arcade.check_for_collision_with_list(self.player, self.walls):
            self.player.center_x -= dx

        self.player.center_y += dy
        if arcade.check_for_collision_with_list(self.player, self.walls):
            self.player.center_y -= dy

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            if self.state == "menu":
                arcade.close_window()
            else:
                self.state = "menu"
            return
        if key == arcade.key.SPACE and self.state in {"game_over", "victory"}:
            self.state = "menu"
            return
        if self.state == "game":
            self.keys.add(key)

    def on_key_release(self, key, modifiers):
        self.keys.discard(key)

    def on_mouse_motion(self, x, y, dx, dy):
        if self.state == "menu":
            self.play_button.check_hover((x, y))
            self.quit_button.check_hover((x, y))

    def on_mouse_press(self, x, y, button, modifiers):
        if self.state == "menu":
            if self.play_button.is_clicked((x, y)):
                self.state = "game"
                self.current_level = 1
                self.setup_level(self.current_level)
            elif self.quit_button.is_clicked((x, y)):
                arcade.close_window()
            return

        if self.state != "game" or button != arcade.MOUSE_BUTTON_LEFT:
            return
        now = arcade.get_time()
        if now - self.player.last_shot > 0.75:
            self.player.last_shot = now
            world_x = x + self.camera.position[0]
            world_y = y + self.camera.position[1]
            angle = math.atan2(world_y - self.player.center_y, world_x - self.player.center_x)
            bullet = Bullet(self.player.center_x, self.player.center_y, angle, is_player=True)
            self.bullets.append(bullet)
            self.all_sprites.append(bullet)


def main():
    window = CastleShooter()
    arcade.run()


if __name__ == "__main__":
    main()
