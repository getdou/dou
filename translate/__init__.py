"""dòu translate — deepseek-powered chinese-to-english translation.

Uses DeepSeek's language model for high-quality translation of Chinese
social media content, with a custom slang dictionary and Redis caching.
"""

from .engine import TranslationEngine

__all__ = ["TranslationEngine"]
