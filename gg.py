import pygame
import math
import random

pygame.mixer.init()
pygame.init()

info = pygame.display.Info()
SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Castle Shooter")

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

try:
    player_shoot_sound = pygame.mixer.Sound('shoot.wav')
    player_shoot_sound.set_volume(0.3)
except:
    pass

try:
    enemy_shoot_sound = pygame.mixer.Sound('enemy_shot.wav')
    enemy_shoot_sound.set_volume(0.3)
except:
    pass

try:
    teleport_sound = pygame.mixer.Sound('teleport.wav')
    teleport_sound.set_volume(0.5)
except:
    pass
try:
    death_sound = pygame.mixer.Sound('death.wav')
    death_sound.set_volume(0.5)
except:
    pass

try:
    pygame.mixer.music.load('music.mp3')
    pygame.mixer.music.set_volume(0.2)
    pygame.mixer.music.play(-1)
except:
    pass

clock = pygame.time.Clock()
font = pygame.font.SysFont("Georgia", 26)
title_font = pygame.font.SysFont("Georgia", 72, bold=True)
menu_font = pygame.font.SysFont("Georgia", 32, bold=True)

all_sprites = pygame.sprite.Group()
walls = pygame.sprite.Group()
bullets = pygame.sprite.Group()
enemy_bullets = pygame.sprite.Group()
enemies = pygame.sprite.Group()
portals = pygame.sprite.Group()
corpses = pygame.sprite.Group()


def create_player_image():
    img = pygame.image.load('player.png').convert_alpha()
    img = pygame.transform.scale(img, (75, 75))
    return img


def create_enemy_image(kind):
    if kind == "weak":
        img = pygame.image.load('enemy_weak.png').convert_alpha()
        img = pygame.transform.scale(img, (100, 150))
    elif kind == "norm":
        img = pygame.image.load('enemy_weak.png').convert_alpha()
        img = pygame.transform.scale(img, (140, 200))
    else:
        img = pygame.image.load('enemy_boss.png').convert_alpha()
        img = pygame.transform.scale(img, (250, 250))
    return img


def create_death_image(kind):
    if kind == "weak":
        size = (35, 35)
    elif kind == "norm":
        size = (40, 40)
    else:
        size = (80, 80)

    img = pygame.Surface(size, pygame.SRCALPHA)
    center_x, center_y = size[0] // 2, size[1] // 2
    pygame.draw.line(img, RED, (5, 5), (size[0] - 5, size[1] - 5), 4)
    pygame.draw.line(img, RED, (size[0] - 5, 5), (5, size[1] - 5), 4)
    return img


player_img = create_player_image()
enemy_imgs = {
    "weak": create_enemy_image("weak"),
    "norm": create_enemy_image("norm"),
    "boss": create_enemy_image("boss")
}
death_imgs = {
    "weak": create_death_image("weak"),
    "norm": create_death_image("norm"),
    "boss": create_death_image("boss")
}


class Corpse(pygame.sprite.Sprite):
    def __init__(self, x, y, kind):
        super().__init__(all_sprites, corpses)
        self.image = death_imgs[kind].copy()
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.lifetime = 300

    def update(self):
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()
        if self.lifetime < 60:
            alpha = int((self.lifetime / 60) * 255)
            self.image.set_alpha(alpha)


class Button:
    def __init__(self, x, y, width, height, text, color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover = False

    def draw(self, surface):
        if self.hover:
            pygame.draw.rect(surface, GOLD, self.rect.inflate(10, 10), border_radius=5)

        pygame.draw.rect(surface, self.color, self.rect, border_radius=5)
        pygame.draw.rect(surface, GOLD, self.rect, 4, border_radius=5)

        text_surf = menu_font.render(self.text, True, GOLD if not self.hover else WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def check_hover(self, pos):
        self.hover = self.rect.collidepoint(pos)
        return self.hover

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def update(self, target):
        x = -target.rect.centerx + int(SCREEN_WIDTH / 2)
        y = -target.rect.centery + int(SCREEN_HEIGHT / 2)

        x = min(0, x)
        y = min(0, y)
        x = max(-(self.width - SCREEN_WIDTH), x)
        y = max(-(self.height - SCREEN_HEIGHT), y)

        self.camera.x += (x - self.camera.x) * 0.15
        self.camera.y += (y - self.camera.y) * 0.15


class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__(all_sprites, walls)
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image.fill(WALL_COLOR)
        pygame.draw.rect(self.image, (60, 40, 40), (2, 2, 46, 46), 2)
        self.rect = self.image.get_rect()
        self.rect.x = x * TILE_SIZE
        self.rect.y = y * TILE_SIZE


class Portal(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__(all_sprites, portals)
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        self.rect = self.image.get_rect()
        self.rect.x = x * TILE_SIZE
        self.rect.y = y * TILE_SIZE
        self.flag = 0

    def update(self):
        if not self.flag:
            self.image = pygame.image.load('portal.png')
            self.image = pygame.transform.scale(self.image, (150, 150))
            self.flag = 1


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, is_player=True):
        if is_player:
            super().__init__(all_sprites, bullets)
            self.speed = 10
            self.damage = 25
            self.bullet_sound = 'player'
            self.image = pygame.image.load('player_bullet.png').convert_alpha()
            self.image = pygame.transform.scale(self.image,(30, 30))
        else:
            super().__init__(all_sprites, enemy_bullets)
            self.speed = 6
            self.color = RED
            self.damage = 15
            self.bullet_sound = 'enemy'
            self.image = pygame.Surface((20, 20), pygame.SRCALPHA)
            pygame.draw.circle(self.image, self.color, (10, 10), 35)

        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.lifetime = 50

    def update(self):
        if self.bullet_sound == 'player':
            player_shoot_sound.play()
        elif self.bullet_sound == 'enemy':
            enemy_shoot_sound.play()
        self.bullet_sound = 0

        self.rect.x += self.vx
        self.rect.y += self.vy

        if pygame.sprite.spritecollideany(self, walls):
            self.kill()

        self.lifetime -= 1
        if self.lifetime <= 0:
            self.kill()


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__(all_sprites)
        self.image = player_img.copy()
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = 5
        self.hp = 100
        self.max_hp = 100
        self.last_shot = 0
        self.vert_flag = 0

    def update(self):
        keys = pygame.key.get_pressed()
        dx, dy = 0, 0

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy = -self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy = self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            if self.vert_flag:
                self.image = pygame.transform.flip(self.image, True, False)
                self.vert_flag = 0
            dx = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            if not self.vert_flag:
                self.image = pygame.transform.flip(self.image, True, False)
                self.vert_flag = 1
            dx = self.speed

        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707

        self.rect.x += dx
        if pygame.sprite.spritecollide(self, walls, False):
            self.rect.x -= dx

        self.rect.y += dy
        if pygame.sprite.spritecollide(self, walls, False):
            self.rect.y -= dy

    def shoot(self, camera):
        now = pygame.time.get_ticks()
        if now - self.last_shot > 750:
            self.last_shot = now

            mx, my = pygame.mouse.get_pos()
            cx, cy = camera.camera.topleft
            angle = math.atan2((my - cy) - self.rect.centery, (mx - cx) - self.rect.centerx)
            Bullet(self.rect.centerx, self.rect.centery, angle, is_player=True)


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, player, kind):
        super().__init__(all_sprites, enemies)
        self.player = player
        self.kind = kind
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
        elif kind == "boss":
            self.hp = 300
            self.max_hp = 300
            self.speed = 2
            self.aggro_range = 350

        self.image = enemy_imgs[kind].copy()
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.last_shot = 0

    def update(self):
        if not self.player:
            return
        dx = self.player.rect.centerx - self.rect.centerx
        dy = self.player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)
        if dist < self.aggro_range:
            self.aggro = True

        if not self.aggro:
            return

        if dist != 0:
            dx, dy = dx / dist, dy / dist

        if dist > 50:
            self.rect.x += dx * self.speed
            if pygame.sprite.spritecollideany(self, walls):
                self.rect.x -= dx * self.speed

            self.rect.y += dy * self.speed
            if pygame.sprite.spritecollideany(self, walls):
                self.rect.y -= dy * self.speed

        if dist < 500:
            now = pygame.time.get_ticks()
            delay = 1200 if self.kind != "boss" else 600
            if now - self.last_shot > delay:
                self.last_shot = now
                angle = math.atan2(
                    self.player.rect.centery - self.rect.centery,
                    self.player.rect.centerx - self.rect.centerx
                )
                Bullet(self.rect.centerx, self.rect.centery, angle, is_player=False)

        if self.hp <= 0:
            if death_sound:
                death_sound.play()
            Corpse(self.rect.centerx, self.rect.centery, self.kind)
            self.kill()

    def draw_health_bar(self, surface, camera):
        if self.hp < self.max_hp:
            bar_width = self.rect.width
            bar_height = 5
            bar_x = self.rect.x + camera.camera.x
            bar_y = self.rect.y + camera.camera.y - 10

            bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
            pygame.draw.rect(surface, (50, 50, 50), bg_rect)

            hp_ratio = max(0, self.hp / self.max_hp)
            fill_width = int(bar_width * hp_ratio)
            fill_rect = pygame.Rect(bar_x, bar_y, fill_width, bar_height)

            color = GREEN if hp_ratio > 0.6 else YELLOW if hp_ratio > 0.3 else RED
            pygame.draw.rect(surface, color, fill_rect)
            pygame.draw.rect(surface, WHITE, bg_rect, 1)


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
    "#########################################################"
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
    "#########################################################"
]


def load_level(level_num):
    teleport_sound.play()
    all_sprites.empty()
    walls.empty()
    bullets.empty()
    enemy_bullets.empty()
    enemies.empty()
    portals.empty()
    corpses.empty()
    current_map = MAP1 if level_num == 1 else MAP2
    map_w = len(current_map[0]) * TILE_SIZE
    map_h = len(current_map) * TILE_SIZE
    player = None

    for row_idx, row in enumerate(current_map):
        for col_idx, char in enumerate(row):
            x = col_idx * TILE_SIZE
            y = row_idx * TILE_SIZE
            if char == "#":
                Wall(col_idx, row_idx)
            elif char == "P":
                player = Player(x + 25, y + 25)
            elif char == "w":
                Enemy(x + 25, y + 25, None, "weak")
            elif char == "n":
                Enemy(x + 25, y + 25, None, "norm")
            elif char == "B":
                Enemy(x + 25, y + 25, None, "boss")
            elif char == "N":
                Portal(col_idx, row_idx)

    for enemy in enemies:
        enemy.player = player

    return player, map_w, map_h


def draw_health_bar(surface, x, y, hp, max_hp, width=200):
    ratio = max(0, hp / max_hp)
    fill = int(width * ratio)
    outline_rect = pygame.Rect(x, y, width, 20)
    fill_rect = pygame.Rect(x, y, fill, 20)
    color = GREEN if ratio > 0.6 else YELLOW if ratio > 0.3 else RED
    pygame.draw.rect(surface, color, fill_rect)
    pygame.draw.rect(surface, WHITE, outline_rect, 2)


def draw_fog_of_war(surface, player_pos, camera):
    fog = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    fog.fill((0, 0, 0, 200))

    screen_x = player_pos[0] + camera.camera.x
    screen_y = player_pos[1] + camera.camera.y

    light_radius = 220
    light = pygame.Surface((light_radius * 2, light_radius * 2), pygame.SRCALPHA)

    for r in range(light_radius, 0, -4):
        alpha = int(255 * (1 - r / light_radius))
        color = (255, 180, 80, alpha)
        pygame.draw.circle(light, color, (light_radius, light_radius), r)
    fog.blit(light, (screen_x - light_radius, screen_y - light_radius),
             special_flags=pygame.BLEND_RGBA_SUB)
    surface.blit(fog, (0, 0))


def draw_medieval_background(surface):
    surface.fill((20, 15, 10))
    for i in range(50):
        x = random.randint(0, SCREEN_WIDTH)
        y = random.randint(0, SCREEN_HEIGHT)
        size = random.randint(30, 100)
        pygame.draw.circle(surface, STONE, (x, y), size)
    frame_thickness = 30
    pygame.draw.rect(surface, STONE, (0, 0, SCREEN_WIDTH, frame_thickness))
    pygame.draw.rect(surface, STONE, (0, SCREEN_HEIGHT - frame_thickness, SCREEN_WIDTH, frame_thickness))
    pygame.draw.rect(surface, STONE, (0, 0, frame_thickness, SCREEN_HEIGHT))
    pygame.draw.rect(surface, STONE, (SCREEN_WIDTH - frame_thickness, 0, frame_thickness, SCREEN_HEIGHT))


def main_menu():
    background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    draw_medieval_background(background)

    play_button = Button(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 20, 300, 70, "START GAME", DARK_RED)
    quit_button = Button(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 80, 300, 70, "LEAVE", (60, 30, 30))

    while True:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if play_button.is_clicked(mouse_pos):
                    return True
                if quit_button.is_clicked(mouse_pos):
                    return False

        play_button.check_hover(mouse_pos)
        quit_button.check_hover(mouse_pos)

        screen.blit(background, (0, 0))

        title_text = title_font.render("CASTLE SHOOTERS", True, GOLD)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 200))
        screen.blit(title_text, title_rect)

        play_button.draw(screen)
        quit_button.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)


def game_loop():
    current_level = 1
    player, level_w, level_h = load_level(current_level)
    camera = Camera(level_w, level_h)

    running = True
    game_over = False
    victory = False

    lose_sound = pygame.mixer.Sound('lose_sound.mp3')
    lose_sound.set_volume(0.3)
    lose_flag = 0

    win_sound = pygame.mixer.Sound('win_sound.mp3')
    win_sound.set_volume(0.7)
    win_flag = 0

    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
                if (game_over or victory) and event.key == pygame.K_SPACE:
                    return True

        if not game_over and not victory:
            if pygame.mouse.get_pressed()[0]:
                player.shoot(camera)

            player.update()
            enemies.update()
            bullets.update()
            enemy_bullets.update()
            portals.update()
            corpses.update()
            camera.update(player)

            if current_level == 1 and pygame.sprite.spritecollide(player, portals, False):
                if len(enemies) == 0:
                    current_level = 2
                    player, level_w, level_h = load_level(current_level)
                    camera = Camera(level_w, level_h)

            hits = pygame.sprite.groupcollide(enemies, bullets, False, True)
            for hit_enemy in hits:
                hit_enemy.hp -= 10
                hit_enemy.aggro = True

            hits = pygame.sprite.spritecollide(player, enemy_bullets, True)
            for hit_bullet in hits:
                player.hp -= hit_bullet.damage
                if player.hp < 0:
                    player.hp = 0

            if player.hp <= 0:
                game_over = True
            if current_level == 2 and len(enemies) == 0:
                victory = True


        screen.fill(BLACK)

        game_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        game_surface.fill(FLOOR_COLOR)

        for sprite in all_sprites:
            game_surface.blit(sprite.image, camera.apply(sprite))

        for enemy in enemies:
            enemy.draw_health_bar(game_surface, camera)

        draw_fog_of_war(game_surface, player.rect.center, camera)
        screen.blit(game_surface, (0, 0))
        draw_health_bar(screen, 10, 10, player.hp, player.max_hp)
        hp_text = font.render(f"HP: {player.hp}/{player.max_hp}", True, WHITE)
        screen.blit(hp_text, (10, 35))
        enemies_text = font.render(f"Enemies lefts: {len(enemies)}", True, WHITE)
        screen.blit(enemies_text, (10, 60))
        level_text = font.render(f"Current level: {current_level}", True, WHITE)
        screen.blit(level_text, (10, 85))
        if game_over:
            if not lose_flag:
                lose_sound.play()
                lose_flag = 1
            game_over_text = title_font.render("DEFEAT", True, RED)
            restart_text = menu_font.render("Press SPACE", True, WHITE)
            screen.blit(game_over_text, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2 - 50))
            screen.blit(restart_text, (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 20))
        if victory:
            if not win_flag:
                win_sound.play()
                win_flag = 1
            victory_text = title_font.render("VICTORY!", True, GOLD)
            restart_text = menu_font.render("Press SPACE", True, WHITE)
            screen.blit(victory_text, (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 50))
            screen.blit(restart_text, (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 20))

        pygame.display.flip()

    return False


def main():
    while True:
        if not main_menu():
            break
        if not game_loop():
            break

    pygame.quit()


if __name__ == "__main__":
    main()