"""Powertools logger setup. Sve Lambde importuju `from shared.logger import logger, tracer`."""
from __future__ import annotations

import os

from aws_lambda_powertools import Logger, Tracer

SERVICE_NAME = os.environ.get("POWERTOOLS_SERVICE_NAME", "konsultacije")

logger = Logger(service=SERVICE_NAME)
tracer = Tracer(service=SERVICE_NAME)
