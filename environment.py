"""Animated, score-driven space backgrounds for ORBIT ZERO.

Reality Stability is expected on a 0-100 scale: 100 is calm and 0 is
highly unstable. Values outside that range are safely clamped.
"""

import math
import random

import pygame


class Environment:
	"""Draw a changing space environment without managing game state."""

	PHASES = (
		(0, "Silent Expanse", (4, 10, 31), (31, 73, 132)),
		(1000, "Nebula Drift", (18, 8, 35), (147, 52, 125)),
		(2500, "Fracture Zone", (25, 7, 17), (174, 48, 47)),
		(5000, "Event Horizon", (3, 4, 13), (61, 119, 174)),
	)

	def __init__(self, width, height):
		self.width = max(1, int(width))
		self.height = max(1, int(height))
		self._rng = random.Random()
		self._frame = 0
		self._phase = 0
		self._stability = 100.0
		self._stars = []
		self._particles = []
		self._backgrounds = [self._make_background(i) for i in range(4)]

		star_count = max(45, min(220, self.width * self.height // 9000))
		for _ in range(star_count):
			self._stars.append(self._new_star(random_y=True))

	def phase_for_score(self, score):
		"""Return phase index 0-3 for the given score."""
		if score < 1000:
			return 0
		if score < 2500:
			return 1
		if score < 5000:
			return 2
		return 3

	def update(self, score, stability):
		"""Advance animation by one frame and apply current game inputs.

		``stability`` is expected from 0 to 100. It is clamped when outside
		that range; lower values increase subtle flicker and particle effects.
		"""
		self._frame += 1
		self._phase = self.phase_for_score(score)
		self._stability = max(0.0, min(100.0, float(stability)))
		instability = 1.0 - self._stability / 100.0

		for star in self._stars:
			star["y"] += star["speed"] * (0.65 + instability * 0.55)
			if star["y"] >= self.height:
				star.update(self._new_star(random_y=False))

		if instability > 0.12 and len(self._particles) < 24:
			if self._rng.random() < instability * 0.09:
				self._particles.append(self._new_particle())

		for particle in self._particles[:]:
			particle["x"] += particle["dx"]
			particle["y"] += particle["dy"]
			particle["life"] -= 1
			if particle["life"] <= 0:
				self._particles.remove(particle)

	def draw(self, screen):
		"""Draw the current environment onto a Pygame surface."""
		screen.blit(self._backgrounds[self._phase], (0, 0))
		instability = 1.0 - self._stability / 100.0

		if self._phase == 3:
			self._draw_vortex(screen, instability)

		for star in self._stars:
			twinkle = math.sin(self._frame * 0.045 + star["twinkle"]) * 12
			instability_flicker = (
				math.sin(self._frame * 0.31 + star["twinkle"] * 2)
				* instability
				* 28
			)
			brightness = max(65, min(255, int(star["brightness"] + twinkle + instability_flicker)))
			color = (brightness, min(255, brightness + 8), min(255, brightness + 22))
			x, y = int(star["x"]), int(star["y"])
			pygame.draw.circle(screen, color, (x, y), star["radius"])
			if star["layer"] == 2:
				trail = 4 + star["radius"]
				pygame.draw.line(screen, color, (x, y + 2), (x, y + trail), 1)
			elif star["layer"] == 1 and star["radius"] >= 2:
				pygame.draw.line(screen, color, (x, y + 2), (x, y + 4), 1)

		for particle in self._particles:
			fade = min(1.0, particle["life"] / 12)
			color = (int(255 * fade), int(105 * fade), int(125 * fade))
			pygame.draw.circle(
				screen,
				color,
				(int(particle["x"]), int(particle["y"])),
				particle["size"],
			)

		if instability > 0.35:
			self._draw_stability_distortion(screen, instability)

	def _new_star(self, random_y):
		layer = self._rng.choices((0, 1, 2), weights=(5, 3, 2))[0]
		layer_properties = (
			(0.2, 0.75, (1,), (75, 155)),
			(0.7, 1.6, (1, 2), (105, 195)),
			(1.5, 3.0, (1, 2, 3), (145, 235)),
		)
		speed_min, speed_max, radii, brightness_range = layer_properties[layer]
		return {
			"x": self._rng.uniform(0, self.width),
			"y": self._rng.uniform(0, self.height) if random_y else -2,
			"speed": self._rng.uniform(speed_min, speed_max),
			"radius": self._rng.choice(radii),
			"brightness": self._rng.randint(*brightness_range),
			"layer": layer,
			"twinkle": self._rng.uniform(0, math.tau),
		}

	def _new_particle(self):
		return {
			"x": self._rng.uniform(0, self.width),
			"y": self._rng.uniform(0, self.height),
			"dx": self._rng.uniform(-0.7, 0.7),
			"dy": self._rng.uniform(-1.1, 0.2),
			"life": self._rng.randint(12, 34),
			"size": self._rng.choice((1, 1, 2)),
		}

	def _make_background(self, phase):
		start = self.PHASES[phase][2]
		end = self.PHASES[phase][3]
		surface = pygame.Surface((self.width, self.height))

		for y in range(self.height):
			amount = y / max(1, self.height - 1)
			color = tuple(int(a + (b - a) * amount * 0.48) for a, b in zip(start, end))
			pygame.draw.line(surface, color, (0, y), (self.width, y))

		# Build atmospheric depth once; only the cached surface is blitted per frame.
		far_haze = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
		near_haze = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
		shadow = tuple(channel // 2 for channel in end)
		light = tuple(min(255, channel + (255 - channel) // 3) for channel in end)
		for index in range(8, 0, -1):
			width = int(self.width * (0.2 + index * 0.06))
			height = int(self.height * (0.1 + index * 0.045))
			x = int(self.width * (0.16 + (index % 4) * 0.22))
			y = int(self.height * (0.18 + (index % 3) * 0.3))
			pygame.draw.ellipse(
				far_haze,
				(*shadow, 4 + (8 - index)),
				(x - width // 2, y - height // 2, width, height),
			)
			inner_width = int(width * 0.68)
			inner_height = int(height * 0.62)
			pygame.draw.ellipse(
				near_haze,
				(*light, 3 + (8 - index)),
				(x - inner_width // 2, y - inner_height // 2,
				 inner_width, inner_height),
			)
		surface.blit(far_haze, (0, 0))
		surface.blit(near_haze, (0, 0))
		return surface

	def _draw_vortex(self, screen, instability):
		center_x = int(self.width * 0.69)
		center_y = int(self.height * 0.49)
		radius = max(28, int(min(self.width, self.height) * 0.24))
		pulse = 1.0 + math.sin(self._frame * 0.035) * 0.035

		for ring in range(5, 0, -1):
			ring_radius = int(radius * ring / 5 * pulse)
			color = (12 + ring * 4, 20 + ring * 8, 42 + ring * 12)
			pygame.draw.ellipse(
				screen,
				color,
				(center_x - ring_radius, center_y - ring_radius // 2,
				 ring_radius * 2, ring_radius),
				max(1, radius // 32),
			)

		arm_color = (99, 159, 218)
		glow_color = (62, 111, 179)
		rotation = self._frame * 0.012
		for arm in range(3):
			points = []
			arm_offset = arm * math.tau / 3 + rotation
			for step in range(1, 33):
				distance = radius * step / 32
				angle = arm_offset + distance / radius * 2.6
				points.append((
					int(center_x + math.cos(angle) * distance),
					int(center_y + math.sin(angle) * distance * 0.54),
				))
			pygame.draw.lines(screen, glow_color, False, points, max(2, radius // 13))
			pygame.draw.lines(screen, arm_color, False, points, max(1, radius // 35))

		pygame.draw.circle(screen, (1, 2, 8), (center_x, center_y), max(12, radius // 5))
		pygame.draw.circle(screen, (113, 170, 226), (center_x, center_y), max(13, radius // 5), 1)

		if instability > 0.45 and self._frame % 11 == 0:
			flicker = int(10 * instability)
			pygame.draw.circle(
				screen,
				(25 + flicker, 38, 72),
				(center_x, center_y),
				max(15, radius // 4),
			)

	def _draw_stability_distortion(self, screen, instability):
		count = min(5, 1 + int(instability * 5))
		for _ in range(count):
			y = self._rng.randrange(self.height)
			x = self._rng.randrange(self.width)
			line_width = self._rng.randint(max(8, self.width // 24), max(9, self.width // 8))
			end_x = min(self.width - 1, x + line_width)
			pygame.draw.line(screen, (115, 44, 83), (x, y), (end_x, y), 1)
