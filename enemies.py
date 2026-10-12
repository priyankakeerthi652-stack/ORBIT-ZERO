"""Enemy behavior and shape-based spacecraft visuals for ORBIT ZERO."""

import math
import random

import pygame

from projectiles import Projectile


class Enemy:
	"""A one-hit enemy compatible with the current spawner and collisions.

	The current game passes only position, player target, and speed. Visual and
	movement variants are selected from that existing speed value, so no change
	to the spawner or collision rectangle is required.
	"""

	def __init__(self, x, y, target, speed, kind=None, bounds=(960, 640)):
		self.position = pygame.Vector2(x, y)
		self.rect = pygame.Rect(0, 0, 28, 28)
		self.rect.center = (round(x), round(y))
		self.speed = speed
		self.bounds = bounds
		self.elapsed = 0.0
		self.phase = (x * 0.017 + y * 0.031) % math.tau
		if kind is None:
			if speed < 86:
				kind = "scout"
			elif speed < 106:
				kind = "weaver"
			else:
				kind = "lancer"
		if kind not in ("scout", "weaver", "lancer"):
			raise ValueError(f"Unknown enemy kind: {kind}")
		self.kind = kind
		self.fire_cooldown = {
			"scout": 3.2,
			"weaver": 3.0,
			"lancer": 2.7,
		}[kind]
		self.fire_timer = 1.35 + (abs(int(x) + int(y)) % 40) / 100

	def update(self, target, dt):
		"""Move toward the player and return a shot when its cooldown expires."""
		self.elapsed += dt
		direction = pygame.Vector2(target) - self.position
		projectile = None
		if direction.length_squared() > 0:
			forward = direction.normalize()

			if self.kind == "scout":
				steering = forward
			else:
				perpendicular = pygame.Vector2(-forward.y, forward.x)
				if self.kind == "weaver":
					amplitude = 0.55
					frequency = 2.4
				else:
					amplitude = 0.28
					frequency = 4.0
				offset = math.sin(self.elapsed * frequency + self.phase) * amplitude
				steering = forward + perpendicular * offset

			if steering.length_squared() > 0:
				self.position += steering.normalize() * self.speed * dt
			self.rect.center = (round(self.position.x), round(self.position.y))

		self.fire_timer -= dt
		if self.fire_timer <= 0 and direction.length_squared() > 0:
			shot_speed = {"scout": 185, "weaver": 175, "lancer": 205}[self.kind]
			projectile = Projectile(
				self.rect.centerx,
				self.rect.centery,
				owner="enemy",
				direction=direction,
				speed=shot_speed,
				bounds=self.bounds,
			)
			self.fire_timer = self.fire_cooldown + random.uniform(-0.25, 0.25)

		return projectile

	def draw(self, screen):
		"""Draw a distinct red craft silhouette for this enemy flight class."""
		center_x = self.rect.centerx
		center_y = self.rect.centery
		if self.kind == "scout":
			points = (
				(center_x, self.rect.top),
				(self.rect.right, center_y),
				(center_x, self.rect.bottom),
				(self.rect.left, center_y),
			)
			main_color = (211, 62, 91)
		elif self.kind == "weaver":
			points = (
				(center_x - 5, self.rect.top),
				(center_x + 5, self.rect.top),
				(self.rect.right, center_y - 4),
				(center_x + 6, center_y + 2),
				(center_x, self.rect.bottom),
				(center_x - 6, center_y + 2),
				(self.rect.left, center_y - 4),
			)
			main_color = (224, 79, 105)
		else:
			points = (
				(center_x, self.rect.top),
				(self.rect.right, self.rect.bottom - 4),
				(center_x, self.rect.bottom - 9),
				(self.rect.left, self.rect.bottom - 4),
			)
			main_color = (242, 92, 77)

		pygame.draw.polygon(screen, (72, 28, 48), points)
		pygame.draw.polygon(screen, main_color, points, 0)
		pygame.draw.polygon(screen, (255, 158, 159), points, 1)
		pygame.draw.circle(screen, (255, 224, 190), self.rect.center, 3)
		pygame.draw.line(
			screen,
			(255, 147, 157),
			(center_x, self.rect.top + 5),
			(center_x, self.rect.bottom - 5),
			1,
		)
