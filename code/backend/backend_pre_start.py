"""Compatibility entry point for existing deployment scripts."""

from app.backend_pre_start import init, logger, main

__all__ = ["init", "logger", "main"]


if __name__ == "__main__":
    main()
