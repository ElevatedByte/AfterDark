"""Effects consume normalized people and BGR arrays, independent of the sensor."""

from abc import ABC, abstractmethod


class Effect(ABC):
    name = ""

    def __init__(self):
        self.enabled = False
        self.settings = {}
        self.people = []
        self.time = 0.0
        self.initialize()

    def initialize(self):
        pass

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False
        self.reset()

    def reset(self):
        self.people = []
        self.time = 0.0

    def trigger(self, people=None):
        pass

    @property
    def alive(self):
        return False

    def update(self, frame, tracking_data, delta_time):
        self.people = tracking_data
        self.time += delta_time

    @abstractmethod
    def render(self, frame): ...
