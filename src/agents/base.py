"""Agent interface and a UI-free episode runner.

An :class:`Agent` maps an :class:`sim.environment.Observation` to an
:class:`sim.state.Action`. The human, the scripted baselines, and later an RL
policy all implement this one contract. :func:`run_episode` drives an agent
through a whole season without any UI, returning the per-day and total cost
breakdown so results can be checked and compared.

Agents depend only on the observation/action contract, never the other way
around.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sim.environment import InventoryRoutingEnv, Observation
from sim.scoring import CostBreakdown, episode_total
from sim.state import Action


class Agent(ABC):
    """Something that can choose a day's action from an observation."""

    @abstractmethod
    def act(self, observation: Observation) -> Action:
        """Return the action to play for the observed day."""


@dataclass(frozen=True)
class EpisodeResult:
    """The cost outcome of playing one full season."""

    total: CostBreakdown
    daily: tuple[CostBreakdown, ...]


def run_episode(
    env: InventoryRoutingEnv, agent: Agent, seed: int | None = None
) -> EpisodeResult:
    """Play an agent through a whole season and collect its cost breakdown."""
    observation = env.reset(seed)
    daily: list[CostBreakdown] = []
    done = False
    while not done:
        result = env.step(agent.act(observation))
        daily.append(result.info["cost"])
        observation = result.observation
        done = result.done
    return EpisodeResult(total=episode_total(daily), daily=tuple(daily))
