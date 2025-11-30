# puck_build/utils/config_loader.py
#
# Puck - Build Manager for Modular C++-Projects
#
# Copyright (c) 2025 Florian Giesemann
# This file is distributed under the terms of the MIT License

"""
Load config from dictionaries into the model classes.
"""

from dacite import from_dict, Config
from typing import TypeVar, Type, Any, Dict
from puck_build.utils.logger import logger

T = TypeVar("T")

DACITE_CONFIG = Config(type_hooks={})


def deserialize_config(data: Dict[str, Any], data_class: Type[T]) -> T:
    """
    Deserializes a given JSON dict into the given data class.
    """
    try:
        return from_dict(data_class=data_class, data=data, config=DACITE_CONFIG)
    except Exception as e:
        logger.error(f"Error deserializing {data_class.__name__}: {e}")
        raise ValueError(f"Invalid configuration file: {e}")
