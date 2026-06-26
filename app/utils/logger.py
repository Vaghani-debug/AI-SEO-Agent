"""
Application Logger.

Configures a single shared logger instance used throughout
the application. Log records are written to logs/seo_agent.log
and include timestamp, severity level, and message.
"""

import logging
import os

# Create the logs directory if it does not already exist
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/seo_agent.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# Shared logger instance -- import this in every module that needs logging
logger = logging.getLogger("seo-agent")
