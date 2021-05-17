from enum import Enum


class Unit(Enum):
    MINUTES = 'minutes'
    METERS = 'meters'


class Profile(Enum):
    WALKING = 'foot'
    HIKING = 'hike'
    CYCLING = 'bike'
    DRIVING = 'car'
