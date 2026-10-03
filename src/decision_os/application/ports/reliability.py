"""Reliability boundary failures that are safe to expose as stable contracts."""


class ConcurrencyConflict(Exception):
    """The write was rejected because the entity changed concurrently."""
