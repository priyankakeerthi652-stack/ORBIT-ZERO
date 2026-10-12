"""Player ship movement, Gravity Resonance dash, and laser control."""

import math

import pygame

from projectiles import Projectile


class Player:
	"""Keyboard-controlled ship compatible with the current game loop."""

	def __init__(self, width=960, height=640):
		self.width = width
		self.height = height
		self.rect = pygame.Rect(width // 2 - 18, height - 84, 36, 42)
		self.rect.clamp_ip(pygame.Rect(0, 0, width, height))
		self.position = pygame.Vector2(self.rect.topleft)
		self.projectiles = []
		self.speed = 270
		self.shot_timer = 0.0
		self.resonance = 100.0
		self.dash_timer = 0.0
		self.dash_cooldown = 0.0
		self.dash_direction = pygame.Vector2(0, -1)

	def activate_dash(self):
		"""Spend resonance to begin a short dash, if the cooldown permits."""
		if self.resonance < 35 or self.dash_cooldown > 0:
			return False
		self.resonance -= 35
		self.dash_timer = 0.18
		self.dash_cooldown = 0.55
		return True

	def update(self, keys, dt):
		"""Move, fire while Space is held, and update owned projectiles."""
		horizontal = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(
			keys[pygame.K_a] or keys[pygame.K_LEFT]
		)
		vertical = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(
			keys[pygame.K_w] or keys[pygame.K_UP]
		)
		direction = pygame.Vector2(horizontal, vertical)
		if direction.length_squared() > 0:
			direction = direction.normalize()
			self.dash_direction = direction

		self.dash_timer = max(0.0, self.dash_timer - dt)
		self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
		self.resonance = min(100.0, self.resonance + 13 * dt)
		movement = self.dash_direction if self.dash_timer > 0 else direction
		speed = self.speed * (3.2 if self.dash_timer > 0 else 1.0)
		self.position += movement * speed * dt
		self.rect.topleft = (round(self.position.x), round(self.position.y))
		self.rect.clamp_ip(pygame.Rect(0, 0, self.width, self.height))
		self.position.update(self.rect.topleft)

		self.shot_timer = max(0.0, self.shot_timer - dt)
		if keys[pygame.K_SPACE] and self.shot_timer <= 0:
			self.projectiles.append(
				Projectile(
					self.rect.centerx,
					self.rect.top,
					bounds=(self.width, self.height),
				)
			)
			self.shot_timer = 0.24

		for projectile in self.projectiles:
			projectile.update(dt)
		self.projectiles = [
			projectile for projectile in self.projectiles
			if projectile.alive and projectile.rect.bottom > 0
		]

	def draw(self, screen, visible=True):
		"""Draw the layered ship, animated engine glow, and its lasers.

		``visible`` is controlled by the game loop for damage blinking.
		"""
		if not visible:
			return

		center_x = self.rect.centerx
		engine_y = self.rect.bottom - 2
		pulse = 0.75 + 0.25 * math.sin(pygame.time.get_ticks() * 0.025)
		glow = pygame.Surface((44, 34), pygame.SRCALPHA)
		pygame.draw.ellipse(
			glow,
			(22, 150, 255, 85),
			(5, 2, 34, 28),
		)
		screen.blit(glow, (center_x - 22, engine_y - 8))
		flame_length = round(10 + 7 * pulse)
		pygame.draw.polygon(
			screen,
			(42, 155, 255),
			((center_x - 8, engine_y), (center_x + 8, engine_y),
			 (center_x, engine_y + flame_length)),
		)
		pygame.draw.polygon(
			screen,
			(170, 250, 255),
			((center_x - 3, engine_y), (center_x + 3, engine_y),
			 (center_x, engine_y + round(flame_length * 0.58))),
		)

		points = (
			(center_x, self.rect.top),
			(center_x + 8, self.rect.top + 12),
			(self.rect.right, self.rect.bottom - 5),
			(center_x + 7, self.rect.bottom - 9),
			(center_x, self.rect.bottom - 4),
			(center_x - 7, self.rect.bottom - 9),
			(self.rect.left, self.rect.bottom - 5),
			(center_x - 8, self.rect.top + 12),
		)
		pygame.draw.polygon(screen, (17, 43, 78), points)
		pygame.draw.polygon(screen, (54, 132, 190), points, 2)
		pygame.draw.polygon(
			screen,
			(88, 183, 225),
			((center_x, self.rect.top + 5),
			 (center_x + 5, self.rect.top + 15),
			 (center_x + 3, self.rect.bottom - 12),
			 (center_x, self.rect.bottom - 8),
			 (center_x - 3, self.rect.bottom - 12),
			 (center_x - 5, self.rect.top + 15)),
		)
		pygame.draw.ellipse(
			screen,
			(104, 240, 255),
			(center_x - 4, self.rect.top + 13, 8, 13),
		)
		pygame.draw.ellipse(
			screen,
			(215, 255, 255),
			(center_x - 2, self.rect.top + 15, 3, 6),
		)
		pygame.draw.line(
			screen,
			(135, 224, 255),
			(self.rect.left + 4, self.rect.bottom - 8),
			(center_x - 7, self.rect.bottom - 12),
			1,
		)
		pygame.draw.line(
			screen,
			(135, 224, 255),
			(self.rect.right - 4, self.rect.bottom - 8),
			(center_x + 7, self.rect.bottom - 12),
			1,
		)

		for projectile in self.projectiles:
			projectile.draw(screen)
