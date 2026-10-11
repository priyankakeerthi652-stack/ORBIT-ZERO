"""Simple shape-based projectiles for ORBIT ZERO."""

import pygame


class Projectile:
	"""A small laser bolt that travels upward and exposes a collision rect."""

	def __init__(self, x, y, speed=10, color=(90, 235, 255)):
		self.rect = pygame.Rect(x - 3, y - 12, 6, 16)
		self.speed = speed
		self.color = color

	def update(self):
		"""Move the laser upward."""
		self.rect.y -= self.speed

	def draw(self, screen):
		"""Draw the laser as a bright rounded rectangle."""
		pygame.draw.rect(screen, self.color, self.rect, border_radius=3)
