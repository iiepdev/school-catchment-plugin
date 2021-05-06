from enum import Enum


class Unit(Enum):
    MINUTES = 1
    METERS = 2


class Profile(Enum):
    WALKING = 1
    HIKING = 2
    CYCLING = 3
    DRIVING = 4
