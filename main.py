
"""Main game loop for ORBIT ZERO."""

import asyncio
import math
import random

import pygame

from enemies import Enemy
from environment import Environment
from player import Player
from ui import (
    draw_game_over_screen,
    draw_hud,
    draw_phase_transition,
    draw_start_screen,
)

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
FPS = 60
MAX_ENEMY_PROJECTILES = 12


class _Asteroid:
    """A drifting, shape-drawn asteroid hazard."""

    def __init__(self, x, y, target, speed):
        self.position = pygame.Vector2(x, y)
        self.radius = random.randint(17, 27)
        self.rect = pygame.Rect(
            0, 0, self.radius * 2, self.radius * 2
        )
        self.rect.center = (round(x), round(y))

        direction = pygame.Vector2(target) - self.position
        if direction.length_squared():
            self.velocity = direction.normalize() * speed
        else:
            self.velocity = pygame.Vector2(0, speed)

        self.rotation = random.uniform(0, math.tau)
        self.rotation_speed = random.uniform(-1.2, 1.2)
        self.vertices = [
            random.uniform(0.78, 1.12) for _ in range(9)
        ]

    def update(self, dt):
        self.position += self.velocity * dt
        self.rotation += self.rotation_speed * dt
        self.rect.center = (
            round(self.position.x),
            round(self.position.y),
        )

    def draw(self, screen):
        points = []

        for index, scale in enumerate(self.vertices):
            angle = self.rotation + math.tau * index / len(self.vertices)
            points.append((
                round(
                    self.position.x
                    + math.cos(angle) * self.radius * scale
                ),
                round(
                    self.position.y
                    + math.sin(angle) * self.radius * scale
                ),
            ))

        pygame.draw.polygon(screen, (150, 139, 145), points)
        pygame.draw.polygon(screen, (221, 190, 165), points, 2)


class _Fragment:
    """A collectible that restores Reality Stability."""

    def __init__(self, x, y):
        self.rect = pygame.Rect(x - 9, y - 9, 18, 18)
        self.life = 9.0
        self.phase = random.uniform(0, math.tau)

    def update(self, dt):
        self.life -= dt
        self.phase += dt * 3
        self.rect.y -= round(17 * dt)

    def draw(self, screen):
        pygame.draw.circle(
            screen, (177, 120, 255), self.rect.center, 10, 2
        )
        pygame.draw.circle(
            screen, (220, 198, 255), self.rect.center, 4
        )


class _GameSession:
    """Own one run's gameplay state and bounded hazard collections."""

    def __init__(self):
        self.environment = Environment(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.player = Player(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.enemies = []
        self.enemy_projectiles = []
        self.asteroids = []
        self.fragments = []

        self.score = 0
        self.stability = 100.0
        self.invulnerability = 0.0

        self.enemy_spawn_timer = 0.7
        self.enemy_spawn_count = 0
        self.asteroid_spawn_timer = 2.0
        self.fragment_counter = 0

        self.phase = self.environment.phase_for_score(self.score)
        self.phase_banner_timer = 0.0

    def activate_dash(self):
        return self.player.activate_dash()

    def update(self, keys, dt):
        self.player.update(keys, dt)
        self.invulnerability = max(0.0, self.invulnerability - dt)

        target = self.player.rect.center
        difficulty = max(0, self.score) / 1000

        self._spawn_enemies(dt, target, difficulty)
        self._spawn_asteroids(dt, target, difficulty)

        for enemy in self.enemies:
            projectile = enemy.update(target, dt)

            if (
                projectile is not None
                and len(self.enemy_projectiles) < MAX_ENEMY_PROJECTILES
            ):
                self.enemy_projectiles.append(projectile)

        for projectile in self.enemy_projectiles:
            projectile.update(dt)

        for asteroid in self.asteroids:
            asteroid.update(dt)

        for fragment in self.fragments:
            fragment.update(dt)

        self._resolve_projectile_hits()
        self._resolve_enemy_projectile_hits()
        self._resolve_player_hits()
        self._collect_fragments()

        self.enemy_projectiles = [
            projectile
            for projectile in self.enemy_projectiles
            if projectile.alive
        ]

        self.enemies = [
            enemy for enemy in self.enemies
            if enemy.rect.right > -40
            and enemy.rect.left < SCREEN_WIDTH + 40
            and enemy.rect.bottom > -40
            and enemy.rect.top < SCREEN_HEIGHT + 40
        ]

        self.asteroids = [
            asteroid for asteroid in self.asteroids
            if asteroid.rect.right > -60
            and asteroid.rect.left < SCREEN_WIDTH + 60
            and asteroid.rect.bottom > -60
            and asteroid.rect.top < SCREEN_HEIGHT + 60
        ]

        self.fragments = [
            fragment for fragment in self.fragments
            if fragment.life > 0
        ]

        new_phase = self.environment.phase_for_score(self.score)

        if new_phase != self.phase:
            self.phase = new_phase
            self.phase_banner_timer = 1.35

        self.phase_banner_timer = max(
            0.0, self.phase_banner_timer - dt
        )

        self.environment.update(self.score, self.stability)

    def _spawn_enemies(self, dt, target, difficulty):
        self.enemy_spawn_timer -= dt

        interval = max(
            0.42, 1.35 - min(difficulty, 5) * 0.15
        )

        if self.enemy_spawn_timer > 0 or len(self.enemies) >= 14:
            return

        side = random.randrange(4)

        if side == 0:
            x, y = random.randrange(SCREEN_WIDTH), -24
        elif side == 1:
            x, y = SCREEN_WIDTH + 24, random.randrange(SCREEN_HEIGHT)
        elif side == 2:
            x, y = random.randrange(SCREEN_WIDTH), SCREEN_HEIGHT + 24
        else:
            x, y = -24, random.randrange(SCREEN_HEIGHT)

        if self.score < 2500:
            kind = (
                "weaver" if self.enemy_spawn_count % 4 == 3
                else "scout"
            )
        else:
            kind = ("scout", "weaver", "lancer")[
                self.enemy_spawn_count % 3
            ]

        self.enemies.append(
            Enemy(
                x,
                y,
                target,
                72 + min(difficulty, 5) * 10,
                kind=kind,
                bounds=(SCREEN_WIDTH, SCREEN_HEIGHT),
            )
        )

        self.enemy_spawn_count += 1
        self.enemy_spawn_timer = interval * random.uniform(0.8, 1.2)

    def _spawn_asteroids(self, dt, target, difficulty):
        self.asteroid_spawn_timer -= dt

        interval = max(
            0.75, 2.4 - min(difficulty, 5) * 0.25
        )

        if self.asteroid_spawn_timer > 0 or len(self.asteroids) >= 8:
            return

        side = random.randrange(4)

        if side == 0:
            x, y = random.randrange(SCREEN_WIDTH), -32
        elif side == 1:
            x, y = SCREEN_WIDTH + 32, random.randrange(SCREEN_HEIGHT)
        elif side == 2:
            x, y = random.randrange(SCREEN_WIDTH), SCREEN_HEIGHT + 32
        else:
            x, y = -32, random.randrange(SCREEN_HEIGHT)

        aim = (
            random.randrange(SCREEN_WIDTH),
            random.randrange(SCREEN_HEIGHT),
        )

        self.asteroids.append(
            _Asteroid(
                x, y, aim,
                55 + min(difficulty, 5) * 9
            )
        )

        self.asteroid_spawn_timer = interval * random.uniform(0.8, 1.2)

    def _resolve_projectile_hits(self):
        for projectile in self.player.projectiles[:]:
            hit = next(
                (
                    enemy for enemy in self.enemies
                    if projectile.rect.colliderect(enemy.rect)
                ),
                None,
            )

            if hit is not None:
                self.player.projectiles.remove(projectile)
                self.enemies.remove(hit)
                self.score += 100
                self._maybe_drop_fragment(hit.rect.center)
                continue

            hit = next(
                (
                    rock for rock in self.asteroids
                    if projectile.rect.colliderect(rock.rect)
                ),
                None,
            )

            if hit is not None:
                self.player.projectiles.remove(projectile)
                self.asteroids.remove(hit)
                self.score += 50
                self._maybe_drop_fragment(hit.rect.center)

    def _resolve_enemy_projectile_hits(self):
        for projectile in self.enemy_projectiles[:]:
            if not projectile.rect.colliderect(self.player.rect):
                continue

            self.enemy_projectiles.remove(projectile)

            if self.invulnerability <= 0:
                self._damage_player()

            return

    def _damage_player(self):
        self.stability = max(0.0, self.stability - 18)
        self.invulnerability = 1.0

    def _resolve_player_hits(self):
        if self.invulnerability > 0:
            return

        for hazard in self.enemies + self.asteroids:
            if self.player.rect.colliderect(hazard.rect):
                self._damage_player()

                if hazard in self.enemies:
                    self.enemies.remove(hazard)
                else:
                    self.asteroids.remove(hazard)

                return

    def _maybe_drop_fragment(self, position):
        self.fragment_counter += 1

        if (
            self.fragment_counter % 3 == 0
            and len(self.fragments) < 10
        ):
            self.fragments.append(_Fragment(*position))

    def _collect_fragments(self):
        for fragment in self.fragments[:]:
            if self.player.rect.colliderect(fragment.rect):
                self.stability = min(100.0, self.stability + 18)
                self.fragments.remove(fragment)

    def draw(self, screen):
        self.environment.draw(screen)

        for fragment in self.fragments:
            fragment.draw(screen)

        for asteroid in self.asteroids:
            asteroid.draw(screen)

        for enemy in self.enemies:
            enemy.draw(screen)

        for projectile in self.enemy_projectiles:
            projectile.draw(screen)

        visible = (
            self.invulnerability <= 0
            or pygame.time.get_ticks() // 100 % 2 == 0
        )

        self.player.draw(screen, visible)

        phase_name = self.environment.PHASES[self.phase][1]

        draw_hud(
            screen,
            self.score,
            round(self.stability),
            round(self.player.resonance),
            f"{self.phase + 1} - {phase_name}",
            self.score // 600 + 1,
        )

        if self.phase_banner_timer > 0:
            draw_phase_transition(
                screen, f"{self.phase + 1} - {phase_name}"
            )


async def main():
    """Run the start, gameplay, and restart loop for Pygbag."""

    pygame.init()

    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT)
    )
    pygame.display.set_caption("ORBIT ZERO")

    clock = pygame.time.Clock()
    mode = "start"
    session = None
    running = True

    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif mode == "start":
                    session = _GameSession()
                    mode = "playing"

                elif (
                    mode == "playing"
                    and event.key in (
                        pygame.K_LSHIFT,
                        pygame.K_RSHIFT,
                    )
                ):
                    session.activate_dash()

                elif (
                    mode == "game_over"
                    and event.key in (
                        pygame.K_RETURN,
                        pygame.K_r,
                    )
                ):
                    session = _GameSession()
                    mode = "playing"

        if mode == "start":
            draw_start_screen(screen)

        elif mode == "playing":
            session.update(pygame.key.get_pressed(), dt)
            session.draw(screen)

            if session.stability <= 0:
                mode = "game_over"

        else:
            draw_game_over_screen(screen, session.score)

        pygame.display.flip()

        # Critical: yield control so the browser can process events
        # and render frames instead of treating the page as unresponsive.
        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
