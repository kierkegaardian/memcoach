# Routes package __init__.py - re-exports routers for main.py convenience
from .kids import router as kids_router
from .decks import router as decks_router
from .cards import router as cards_router
from .review import router as review_router
from .stats import router as stats_router
from .plan import router as plan_router

__all__ = ['kids_router', 'decks_router', 'cards_router', 'review_router', 'stats_router', 'plan_router']
