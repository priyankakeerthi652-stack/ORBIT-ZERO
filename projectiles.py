"""Player and enemy laser bolts for ORBIT ZERO."""

import pygame


class Projectile:
	"""A drawable laser with a Pygame collision rectangle.

	The default constructor and update signature match the projectile currently
	used by ``main.py``. Optional ownership and direction support enemy shots
	when the game loop adds an enemy-projectile collection.
	"""

	def __init__(
		self,
		x,
		y,
		owner="player",
		direction=(0, -1),
		speed=560,
		bounds=(960, 640),
	):
		self.owner = owner
		self.speed = speed
		self.bounds = bounds
		self.lifetime = 3.0
		self.alive = True
		self.direction = pygame.Vector2(direction)
		if self.direction.length_squared() == 0:
			self.direction.update(0, -1 if owner == "player" else 1)
		else:
			self.direction = self.direction.normalize()

		if owner == "player":
			self.rect = pygame.Rect(x - 3, y - 13, 6, 16)
			self.color = (100, 235, 255)
			self.glow_color = (28, 112, 180)
		else:
			self.rect = pygame.Rect(x - 4, y - 6, 8, 12)
			self.color = (255, 126, 92)
			self.glow_color = (164, 50, 72)
		self.position = pygame.Vector2(self.rect.topleft)

	def update(self, dt):
		"""Move the bolt and mark it dead after expiry or leaving the screen."""
		if not self.alive:
			return
		self.position += self.direction * self.speed * dt
		self.rect.topleft = (round(self.position.x), round(self.position.y))
		self.lifetime -= dt
		width, height = self.bounds
		if (
			self.lifetime <= 0
			or self.rect.right < -24
			or self.rect.left > width + 24
			or self.rect.bottom < -24
			or self.rect.top > height + 24
		):
			self.alive = False

	def draw(self, screen):
		"""Draw a bright core, soft glow, and directional trail."""
		if not self.alive:
			return
		padding = 8
		glow = pygame.Surface(
			(self.rect.width + padding * 2, self.rect.height + padding * 2),
			pygame.SRCALPHA,
		)
		pygame.draw.rect(
			glow,
			(*self.glow_color, 48),
			glow.get_rect(),
			border_radius=8,
		)
		pygame.draw.rect(
			glow,
			(*self.glow_color, 90),
			glow.get_rect().inflate(-6, -6),
			border_radius=5,
		)
		screen.blit(glow, (self.rect.x - padding, self.rect.y - padding))
		trail_end = (
			self.rect.centerx - round(self.direction.x * 14),
			self.rect.centery - round(self.direction.y * 14),
		)
		pygame.draw.line(screen, self.glow_color, self.rect.center, trail_end, 4)
		pygame.draw.rect(screen, self.color, self.rect, border_radius=3)
		pygame.draw.line(
			screen,
			(245, 255, 255),
			self.rect.midtop,
			self.rect.midbottom,
			1,
		)
