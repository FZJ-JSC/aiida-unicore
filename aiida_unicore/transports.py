"""
Transports provided by aiida_unicore.

Register transports via the "aiida.transports" entry point in setup.json.
"""
from aiida.transports import Transport


class UnicoreTransport(Transport):
    """
    AiiDA transport plugin for unicore
    """


