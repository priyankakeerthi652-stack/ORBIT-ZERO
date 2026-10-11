"""Edge-spawning enemies that steer toward the player."""

import random

import pygame


class Enemy:
	"""A single pursuing enemy represented by a colored shape."""

	def __init__(self, x, y, target_x, target_y, speed):
		self.rect = pygame.Rect(x - 14, y - 14, 28, 28)
		self.speed = speed
		self.color = (255, 105, 125)
		self._set_direction(target_x, target_y)

	def _set_direction(self, target_x, target_y):
		dx = target_x - self.rect.centerx
		dy = target_y - self.rect.centery
		distance = max(1, (dx * dx + dy * dy) ** 0.5)
		self.direction = (dx / distance, dy / distance)

	def update(self, target_x, target_y):
		"""Move toward the current target position."""
		self._set_direction(target_x, target_y)
		self.rect.x += round(self.direction[0] * self.speed)
		self.rect.y += round(self.direction[1] * self.speed)

	def draw(self, screen):
		"""Draw the enemy as a diamond with a small center detail."""
		points = [
			(self.rect.centerx, self.rect.top),
			(self.rect.right, self.rect.centery),
			(self.rect.centerx, self.rect.bottom),
			(self.rect.left, self.rect.centery),
		]
		pygame.draw.polygon(screen, self.color, points)
		pygame.draw.circle(screen, (255, 220, 180), self.rect.center, 4)


class EnemyManager:
	"""Spawn, update, and draw a bounded number of pursuing enemies.

	Set ``player`` or call ``set_player`` to make enemies chase the player.
	Without a player reference they head toward the center of the screen.
	"""

	def __init__(self, width, height, player=None):
		self.width = width
		self.height = height
		self.player = player
		self.enemies = []
		self.max_enemies = 18
		self._last_spawn_at = pygame.time.get_ticks()

	def set_player(self, player):
		"""Set the player target used by subsequent updates."""
		self.player = player

	def update(self, score):
		"""Spawn and move enemies; higher scores raise speed and spawn rate."""
		now = pygame.time.get_ticks()
		difficulty = max(0, score) / 500
		spawn_interval = max(450, 1400 - int(difficulty * 80))

		if len(self.enemies) < self.max_enemies and now - self._last_spawn_at >= spawn_interval:
			target_x, target_y = self._target_position()
			side = random.randrange(4)
			if side == 0:
				x, y = random.randrange(self.width), -16
			elif side == 1:
				x, y = self.width + 16, random.randrange(self.height)
			elif side == 2:
				x, y = random.randrange(self.width), self.height + 16
			else:
				x, y = -16, random.randrange(self.height)

			enemy_speed = min(3.8, 1.4 + difficulty * 0.12)
			self.enemies.append(Enemy(x, y, target_x, target_y, enemy_speed))
			self._last_spawn_at = now

		target_x, target_y = self._target_position()
		for enemy in self.enemies:
			enemy.update(target_x, target_y)

	def draw(self, screen):
		"""Draw every active enemy."""
		for enemy in self.enemies:
			enemy.draw(screen)

	def _target_position(self):
		if self.player is not None:
			return self.player.rect.center
		return self.width // 2, self.height // 2
