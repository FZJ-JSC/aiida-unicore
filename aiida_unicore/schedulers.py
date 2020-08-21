"""
Schedulers provided by aiida_unicore.

Register schedulers via the "aiida.schedulers" entry point in setup.json.
"""
from aiida.schedulers import Scheduler

DiffParameters = DataFactory('unicore')


class Unicore(Scheduler):
    """
    AiiDA scheduler plugin for unicore
    """


