"""A2A service entrypoints for containerized agents.

Each module creates a Starlette app wrapping one or more agents
via the A2A protocol. These serve as the CMD entrypoints for
their respective Containerfiles.
"""
