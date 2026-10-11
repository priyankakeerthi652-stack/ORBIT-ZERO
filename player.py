"""Player movement, dash, and laser controls for ORBIT ZERO."""

import math

import pygame

from projectiles import Projectile


class Player:
	"""A keyboard-controlled ship kept within the game window."""

	COLOR = (95, 220, 255)

	def __init__(self, width, height):
		self.width = width
		self.height = height
		self.rect = pygame.Rect(width // 2 - 18, height - 82, 36, 42)
		self.rect.clamp_ip(pygame.Rect(0, 0, width, height))
		self.speed = 5
		self.projectiles = []
		self._last_direction = (0, -1)
		self._dash_direction = (0, -1)
		self._dash_duration = 180
		self._dash_cooldown = 1200
		self._dash_until = 0
		self._dash_ready_at = 0
		self._shot_cooldown = 240
		self._next_shot_at = 0

	def activate_dash(self):
		"""Start a brief speed burst if the dash cooldown has expired."""
		now = pygame.time.get_ticks()
		if now < self._dash_ready_at:
			return False

		self._dash_direction = self._last_direction
		self._dash_until = now + self._dash_duration
		self._dash_ready_at = now + self._dash_cooldown
		return True

	def update(self, keys=None):
		"""Read movement/shooting input and update the ship and its lasers.

		Pass a Pygame key-state object in ``keys`` to control input explicitly;
		when omitted, the current keyboard state is used.
		"""
		if keys is None:
			try:
				keys = pygame.key.get_pressed()
			except pygame.error:
				keys = ()

		horizontal = 0
		vertical = 0
		if keys:
			horizontal = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(
				keys[pygame.K_a] or keys[pygame.K_LEFT]
			)
			vertical = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(
				keys[pygame.K_w] or keys[pygame.K_UP]
			)

		if horizontal or vertical:
			magnitude = math.hypot(horizontal, vertical)
			self._last_direction = (horizontal / magnitude, vertical / magnitude)

		now = pygame.time.get_ticks()
		if now < self._dash_until:
			move_x, move_y = self._dash_direction
			movement_speed = self.speed * 3
		else:
			magnitude = max(1, math.hypot(horizontal, vertical))
			move_x, move_y = horizontal / magnitude, vertical / magnitude
			movement_speed = self.speed
		self.rect.x += round(move_x * movement_speed)
		self.rect.y += round(move_y * movement_speed)
		self.rect.clamp_ip(pygame.Rect(0, 0, self.width, self.height))

		if keys and keys[pygame.K_SPACE] and now >= self._next_shot_at:
			self.projectiles.append(Projectile(self.rect.centerx, self.rect.top))
			self._next_shot_at = now + self._shot_cooldown

		for projectile in self.projectiles:
			projectile.update()
		self.projectiles = [
			projectile for projectile in self.projectiles
			if projectile.rect.bottom > 0
		]

	def draw(self, screen):
		"""Draw the ship and all active lasers."""
		points = [
			(self.rect.centerx, self.rect.top),
			(self.rect.right, self.rect.bottom),
			(self.rect.centerx, self.rect.bottom - 9),
			(self.rect.left, self.rect.bottom),
		]
		pygame.draw.polygon(screen, self.COLOR, points)
		pygame.draw.polygon(screen, (225, 250, 255), points, 2)
		for projectile in self.projectiles:
			projectile.draw(screen)
