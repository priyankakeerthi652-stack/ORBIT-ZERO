"""Timed, non-overlapping world events for ORBIT ZERO.

This module schedules events and returns requests/state only. Gameplay modules
remain responsible for creating objects, applying forces, drawing, collision,
and reward collection.
"""

from dataclasses import dataclass
from enum import Enum
import math
import random
from typing import Optional


class EventType(str, Enum):
	"""The available event kinds."""

	ASTEROID_STORM = "asteroid_storm"
	GRAVITY_ANOMALY = "gravity_anomaly"
	FRAGMENT_SHOWER = "fragment_shower"


class EventState(str, Enum):
	"""Current event lifecycle state."""

	IDLE = "idle"
	WARNING = "warning"
	ACTIVE = "active"


@dataclass(frozen=True)
class AsteroidSpawn:
	"""Request for gameplay code to create an asteroid at screen position."""

	x: float
	y: float

	@property
	def position(self):
		return (self.x, self.y)


@dataclass(frozen=True)
class FragmentSpawn:
	"""Request for a collectible with a stability reward; no collection logic."""

	x: float
	y: float
	stability_reward: float = 5.0

	@property
	def position(self):
		return (self.x, self.y)


@dataclass(frozen=True)
class GravityForceRequest:
	"""Bounded force request for one asteroid index in the supplied positions.

	The vector is a game-defined acceleration/force value. Apply it according
	to the game's movement units; this manager never moves the asteroid.
	"""

	asteroid_index: int
	force_x: float
	force_y: float

	@property
	def vector(self):
		return (self.force_x, self.force_y)

	@property
	def magnitude(self):
		return math.hypot(self.force_x, self.force_y)


@dataclass(frozen=True)
class EventResult:
	"""Snapshot returned by :meth:`EventManager.update`.

	``event`` is the current event, or ``None`` when idle. ``ended_event`` is
	set for the update in which an event expires. ``warning_text`` is populated
	only during an Asteroid Storm warning. Spawn and force fields contain
	requests for gameplay code, never live game objects.
	"""

	event: Optional[EventType]
	state: EventState
	warning_text: Optional[str]
	elapsed: float
	duration: float
	asteroid_spawns: tuple[AsteroidSpawn, ...] = ()
	fragment_spawns: tuple[FragmentSpawn, ...] = ()
	gravity_forces: tuple[GravityForceRequest, ...] = ()
	gravity_center: Optional[tuple[float, float]] = None
	gravity_radius: float = 0.0
	gravity_strength: float = 0.0
	ended_event: Optional[EventType] = None

	@property
	def is_active(self):
		"""Whether an event is active in this snapshot."""
		return self.state is EventState.ACTIVE


class EventManager:
	"""Schedule timed events and return bounded requests for game systems.

	``dt`` is elapsed seconds. Optional ``rng`` must provide ``uniform`` and
	``choice`` (for example, ``random.Random(seed)``). Public timing and count
	attributes may be adjusted before or during play. The count arguments to
	``update`` must report currently alive event-created objects so this manager
	can enforce population limits.
	"""

	WARNING_TEXT = "WARNING: ASTEROID STORM INCOMING!"
	MAX_UPDATE_DT = 60.0
	MAX_GRAVITY_FORCE = 30.0

	def __init__(self, width, height, rng=None):
		self.width = self._positive_dimension("width", width)
		self.height = self._positive_dimension("height", height)
		self.rng = rng if rng is not None else random.Random()
		if not callable(getattr(self.rng, "uniform", None)) or not callable(
			getattr(self.rng, "choice", None)
		):
			raise TypeError("rng must provide callable uniform() and choice() methods")

		self.minimum_event_interval = 18.0
		self.maximum_event_interval = 30.0
		self.storm_warning_duration = 3.0
		self.storm_duration_range = (6.0, 10.0)
		self.gravity_duration_range = (8.0, 12.0)
		self.fragment_duration_range = (7.0, 10.0)
		self.storm_spawn_interval_range = (0.55, 0.95)
		self.fragment_spawn_interval_range = (0.6, 1.0)
		self.asteroid_safe_radius = 140.0
		self.max_active_event_asteroids = 8
		self.max_storm_asteroid_requests = 8
		self.max_active_event_fragments = 12
		self.max_fragment_requests = 12
		self.fragment_stability_reward = 5.0
		self.gravity_strength = 24.0
		self._validate_limits()

		self._event = None
		self._state = EventState.IDLE
		self._warning_elapsed = 0.0
		self._elapsed = 0.0
		self._duration = 0.0
		self._time_to_next_event = self._sample_range(
			self.minimum_event_interval,
			self.maximum_event_interval,
			"event interval",
		)
		self._storm_spawn_elapsed = 0.0
		self._next_storm_spawn = 0.0
		self._storm_requests = 0
		self._fragment_spawn_elapsed = 0.0
		self._next_fragment_spawn = 0.0
		self._fragment_requests = 0
		self._gravity_center = (self.width / 2.0, self.height / 2.0)
		self._gravity_radius = max(
			1.0,
			min(260.0, math.hypot(self.width, self.height) * 0.32),
		)

	def update(
		self,
		dt,
		*,
		player_position=None,
		asteroid_positions=(),
		active_event_asteroid_count=0,
		active_event_fragment_count=0,
	):
		"""Advance event scheduling and return state/spawn/force requests.

		``player_position`` is an optional ``(x, y)`` pair. Asteroid positions
		are materialized into a tuple; gravity force request indices refer to
		that tuple. The active-object counts should include all currently alive
		objects created by these events. ``dt`` must be finite seconds in the
		inclusive range 0 through ``MAX_UPDATE_DT``.
		"""
		elapsed_input = self._finite_number("dt", dt)
		if not 0.0 <= elapsed_input <= self.MAX_UPDATE_DT:
			raise ValueError(f"dt must be between 0 and {self.MAX_UPDATE_DT} seconds")
		player_position = self._optional_position("player_position", player_position)
		asteroid_positions = self._positions(asteroid_positions)
		active_event_asteroid_count = self._nonnegative_count(
			"active_event_asteroid_count", active_event_asteroid_count
		)
		active_event_fragment_count = self._nonnegative_count(
			"active_event_fragment_count", active_event_fragment_count
		)
		self._validate_limits()

		asteroid_spawns = []
		fragment_spawns = []
		ended_event = None
		active_dt = 0.0

		if self._state is EventState.IDLE:
			self._time_to_next_event -= elapsed_input
			if self._time_to_next_event <= 0.0:
				overdue = -self._time_to_next_event
				self._time_to_next_event = 0.0
				self._start_event()
				if self._state is EventState.WARNING:
					# Return the warning for at least one update before spawning.
					self._warning_elapsed = 0.0
					return self._result(warning_text=self.WARNING_TEXT)
				active_dt = overdue
			else:
				return self._result()
		elif self._state is EventState.WARNING:
			warning_remaining = self.storm_warning_duration - self._warning_elapsed
			if elapsed_input + 1e-9 < warning_remaining:
				self._warning_elapsed += elapsed_input
				return self._result(warning_text=self.WARNING_TEXT)
			active_dt = max(0.0, elapsed_input - warning_remaining)
			self._activate_storm()
		else:
			active_dt = elapsed_input

		if self._state is EventState.ACTIVE:
			active_duration = min(active_dt, max(0.0, self._duration - self._elapsed))
			if self._event is EventType.ASTEROID_STORM:
				self._advance_storm(
					active_duration,
					player_position,
					active_event_asteroid_count,
					asteroid_spawns,
				)
			elif self._event is EventType.FRAGMENT_SHOWER:
				self._advance_fragments(
					active_duration,
					active_event_fragment_count,
					fragment_spawns,
				)

			self._elapsed += active_duration
			if self._elapsed >= self._duration:
				ended_event = self._event
				self._end_event()

		gravity_forces = ()
		gravity_center = None
		gravity_radius = 0.0
		gravity_strength = 0.0
		if self._state is EventState.ACTIVE and self._event is EventType.GRAVITY_ANOMALY:
			gravity_center = self._gravity_center
			gravity_radius = self._gravity_radius
			gravity_strength = min(self.gravity_strength, self.MAX_GRAVITY_FORCE)
			gravity_forces = self._gravity_force_requests(
				asteroid_positions,
				gravity_center,
				gravity_radius,
				gravity_strength,
			)

		return self._result(
			asteroid_spawns=tuple(asteroid_spawns),
			fragment_spawns=tuple(fragment_spawns),
			gravity_forces=gravity_forces,
			gravity_center=gravity_center,
			gravity_radius=gravity_radius,
			gravity_strength=gravity_strength,
			ended_event=ended_event,
		)

	def _start_event(self):
		choices = tuple(EventType)
		selected = self.rng.choice(choices)
		if selected not in choices:
			raise ValueError("rng.choice() returned an event outside the choices")

		self._event = selected
		self._elapsed = 0.0
		if selected is EventType.ASTEROID_STORM:
			self._state = EventState.WARNING
			self._warning_elapsed = 0.0
			self._duration = 0.0
			self._storm_requests = 0
			self._storm_spawn_elapsed = 0.0
			self._next_storm_spawn = self._sample_range(
				*self.storm_spawn_interval_range,
				"storm spawn interval",
			)
		elif selected is EventType.GRAVITY_ANOMALY:
			self._state = EventState.ACTIVE
			self._duration = self._sample_range(
				*self.gravity_duration_range,
				"gravity event duration",
			)
		else:
			self._state = EventState.ACTIVE
			self._duration = self._sample_range(
				*self.fragment_duration_range,
				"fragment event duration",
			)
			self._fragment_requests = 0
			self._fragment_spawn_elapsed = 0.0
			self._next_fragment_spawn = self._sample_range(
				*self.fragment_spawn_interval_range,
				"fragment spawn interval",
			)

	def _activate_storm(self):
		self._state = EventState.ACTIVE
		self._elapsed = 0.0
		self._duration = self._sample_range(
			*self.storm_duration_range,
			"storm duration",
		)

	def _end_event(self):
		self._event = None
		self._state = EventState.IDLE
		self._warning_elapsed = 0.0
		self._elapsed = 0.0
		self._duration = 0.0
		self._storm_spawn_elapsed = 0.0
		self._fragment_spawn_elapsed = 0.0
		self._time_to_next_event = self._sample_range(
			self.minimum_event_interval,
			self.maximum_event_interval,
			"event interval",
		)

	def _advance_storm(self, dt, player_position, active_count, output):
		self._storm_spawn_elapsed += dt
		while self._storm_spawn_elapsed >= self._next_storm_spawn:
			self._storm_spawn_elapsed -= self._next_storm_spawn
			self._next_storm_spawn = self._sample_range(
				*self.storm_spawn_interval_range,
				"storm spawn interval",
			)
			available = min(
				self.max_storm_asteroid_requests - self._storm_requests,
				self.max_active_event_asteroids - active_count - len(output),
			)
			if available <= 0:
				break
			position = self._spawn_position(player_position)
			if position is not None:
				output.append(AsteroidSpawn(*position))
				self._storm_requests += 1

	def _advance_fragments(self, dt, active_count, output):
		self._fragment_spawn_elapsed += dt
		while self._fragment_spawn_elapsed >= self._next_fragment_spawn:
			self._fragment_spawn_elapsed -= self._next_fragment_spawn
			self._next_fragment_spawn = self._sample_range(
				*self.fragment_spawn_interval_range,
				"fragment spawn interval",
			)
			available = min(
				self.max_fragment_requests - self._fragment_requests,
				self.max_active_event_fragments - active_count - len(output),
			)
			if available <= 0:
				break
			position = self._spawn_position(None)
			if position is not None:
				output.append(
					FragmentSpawn(*position, stability_reward=self.fragment_stability_reward)
				)
				self._fragment_requests += 1

	def _spawn_position(self, player_position):
		margin = min(24.0, (self.width - 1) / 2.0, (self.height - 1) / 2.0)
		low_x = margin
		high_x = self.width - 1.0 - margin
		low_y = margin
		high_y = self.height - 1.0 - margin

		for _ in range(24):
			x = self._sample_range(low_x, high_x, "spawn x")
			y = self._sample_range(low_y, high_y, "spawn y")
			if self._outside_safe_radius(x, y, player_position):
				return (x, y)

		if player_position is None:
			return None
		corners = (
			(low_x, low_y),
			(low_x, high_y),
			(high_x, low_y),
			(high_x, high_y),
		)
		farthest = max(
			corners,
			key=lambda point: math.dist(point, player_position),
		)
		if self._outside_safe_radius(*farthest, player_position):
			return farthest
		return None

	def _outside_safe_radius(self, x, y, player_position):
		if player_position is None:
			return True
		return math.dist((x, y), player_position) >= self.asteroid_safe_radius

	def _gravity_force_requests(self, asteroid_positions, center, radius, strength):
		requests = []
		for index, position in enumerate(asteroid_positions):
			dx = center[0] - position[0]
			dy = center[1] - position[1]
			distance = math.hypot(dx, dy)
			if distance == 0.0 or distance >= radius:
				continue
			magnitude = min(
				self.MAX_GRAVITY_FORCE,
				strength * (1.0 - distance / radius),
			)
			requests.append(
				GravityForceRequest(
					asteroid_index=index,
					force_x=dx / distance * magnitude,
					force_y=dy / distance * magnitude,
				)
			)
		return tuple(requests)

	def _result(
		self,
		*,
		warning_text=None,
		asteroid_spawns=(),
		fragment_spawns=(),
		gravity_forces=(),
		gravity_center=None,
		gravity_radius=0.0,
		gravity_strength=0.0,
		ended_event=None,
	):
		return EventResult(
			event=self._event,
			state=self._state,
			warning_text=warning_text,
			elapsed=self._warning_elapsed if self._state is EventState.WARNING else self._elapsed,
			duration=self._duration,
			asteroid_spawns=asteroid_spawns,
			fragment_spawns=fragment_spawns,
			gravity_forces=gravity_forces,
			gravity_center=gravity_center,
			gravity_radius=gravity_radius,
			gravity_strength=gravity_strength,
			ended_event=ended_event,
		)

	def _sample_range(self, low, high, name):
		low = self._finite_number(f"{name} minimum", low)
		high = self._finite_number(f"{name} maximum", high)
		if low > high:
			raise ValueError(f"{name} minimum must not exceed maximum")
		value = self._finite_number(name, self.rng.uniform(low, high))
		if not low <= value <= high:
			raise ValueError(f"rng.uniform() returned {value} outside [{low}, {high}]")
		return value

	def _validate_limits(self):
		self._validated_range(
			"event interval",
			(self.minimum_event_interval, self.maximum_event_interval),
			minimum=0.0,
			strict_minimum=True,
		)
		self._validated_range(
			"storm warning duration",
			(self.storm_warning_duration, self.storm_warning_duration),
			minimum=0.0,
			strict_minimum=True,
		)
		self._validated_range("storm duration", self.storm_duration_range, minimum=6.0, maximum=10.0)
		self._validated_range("gravity duration", self.gravity_duration_range, minimum=0.0, strict_minimum=True)
		self._validated_range("fragment duration", self.fragment_duration_range, minimum=0.0, strict_minimum=True)
		self._validated_range("storm spawn interval", self.storm_spawn_interval_range, minimum=0.0, strict_minimum=True)
		self._validated_range("fragment spawn interval", self.fragment_spawn_interval_range, minimum=0.0, strict_minimum=True)
		for name in (
			"max_active_event_asteroids",
			"max_storm_asteroid_requests",
			"max_active_event_fragments",
			"max_fragment_requests",
		):
			value = getattr(self, name)
			if isinstance(value, bool) or not isinstance(value, int) or value < 0:
				raise ValueError(f"{name} must be a non-negative integer")
		for name in ("asteroid_safe_radius", "gravity_strength", "fragment_stability_reward"):
			value = self._finite_number(name, getattr(self, name))
			if value < 0:
				raise ValueError(f"{name} must be non-negative")
		if self.gravity_strength > self.MAX_GRAVITY_FORCE:
			raise ValueError(f"gravity_strength cannot exceed {self.MAX_GRAVITY_FORCE}")

	@classmethod
	def _validated_range(
		cls,
		name,
		bounds,
		*,
		minimum=None,
		maximum=None,
		strict_minimum=False,
	):
		if isinstance(bounds, (str, bytes)):
			raise TypeError(f"{name} must be a pair of numbers")
		try:
			values = tuple(bounds)
		except TypeError as error:
			raise TypeError(f"{name} must be a pair of numbers") from error
		if len(values) != 2:
			raise ValueError(f"{name} must contain exactly two values")
		low = cls._finite_number(f"{name} minimum", values[0])
		high = cls._finite_number(f"{name} maximum", values[1])
		if low > high:
			raise ValueError(f"{name} minimum must not exceed maximum")
		if minimum is not None:
			invalid_minimum = low <= minimum if strict_minimum else low < minimum
			if invalid_minimum:
				operator = "exceed" if strict_minimum else "be at least"
				raise ValueError(f"{name} minimum must {operator} {minimum}")
		if maximum is not None and high > maximum:
			raise ValueError(f"{name} maximum must not exceed {maximum}")
		return (low, high)

	@staticmethod
	def _positive_dimension(name, value):
		value = EventManager._finite_number(name, value)
		if value <= 0 or not value.is_integer():
			raise ValueError(f"{name} must be a positive integer")
		return int(value)

	@staticmethod
	def _finite_number(name, value):
		if isinstance(value, bool):
			raise TypeError(f"{name} must be a finite number")
		try:
			number = float(value)
		except (TypeError, ValueError, OverflowError) as error:
			raise TypeError(f"{name} must be a finite number") from error
		if not math.isfinite(number):
			raise ValueError(f"{name} must be finite")
		return number

	@classmethod
	def _optional_position(cls, name, value):
		if value is None:
			return None
		return cls._position(name, value)

	@classmethod
	def _position(cls, name, value):
		if isinstance(value, (str, bytes)):
			raise TypeError(f"{name} must be an (x, y) pair")
		try:
			values = tuple(value)
		except TypeError as error:
			raise TypeError(f"{name} must be an (x, y) pair") from error
		if len(values) != 2:
			raise ValueError(f"{name} must contain exactly two coordinates")
		return (
			cls._finite_number(f"{name} x", values[0]),
			cls._finite_number(f"{name} y", values[1]),
		)

	@classmethod
	def _positions(cls, values):
		if values is None:
			return ()
		if isinstance(values, (str, bytes)):
			raise TypeError("asteroid_positions must be an iterable of (x, y) pairs")
		try:
			return tuple(cls._position("asteroid position", value) for value in values)
		except TypeError as error:
			raise TypeError("asteroid_positions must be an iterable of (x, y) pairs") from error

	@staticmethod
	def _nonnegative_count(name, value):
		if isinstance(value, bool):
			raise TypeError(f"{name} must be a non-negative integer")
		try:
			count = int(value)
		except (TypeError, ValueError, OverflowError) as error:
			raise TypeError(f"{name} must be a non-negative integer") from error
		if count != value or count < 0:
			raise ValueError(f"{name} must be a non-negative integer")
		return count
