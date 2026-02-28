"""Constants for Smart Spa Heating integration."""
from typing import Final

DOMAIN: Final = "smart_spa_heating"

# Configuration keys
CONF_NORDPOOL_ENTITY: Final = "nordpool_entity"
CONF_CLIMATE_ENTITY: Final = "climate_entity"
CONF_MANUAL_OVERRIDE_DURATION: Final = "manual_override_duration"
CONF_PP_MAX_TEMPERATURE: Final = "pp_max_temperature"
CONF_PP_MIN_TEMPERATURE: Final = "pp_min_temperature"
CONF_LOOKAHEAD_HOURS: Final = "lookahead_hours"
CONF_PRICE_WINDOW_HOURS: Final = "price_window_hours"

# Default values
DEFAULT_MANUAL_OVERRIDE_DURATION: Final = 3  # hours
DEFAULT_PP_MAX_TEMPERATURE: Final = 40.0  # °C
DEFAULT_PP_MIN_TEMPERATURE: Final = 34.0  # °C
DEFAULT_LOOKAHEAD_HOURS: Final = 3  # hours
DEFAULT_PRICE_WINDOW_HOURS: Final = 0  # 0 = use all available prices

# Limits
MIN_MANUAL_OVERRIDE_DURATION: Final = 1
MAX_MANUAL_OVERRIDE_DURATION: Final = 12
MIN_PP_MAX_TEMPERATURE: Final = 20.0
MAX_PP_MAX_TEMPERATURE: Final = 42.0
MIN_PP_MIN_TEMPERATURE: Final = 5.0
MAX_PP_MIN_TEMPERATURE: Final = 42.0
MIN_LOOKAHEAD_HOURS: Final = 1
MAX_LOOKAHEAD_HOURS: Final = 12
MIN_PRICE_WINDOW_HOURS: Final = 0
MAX_PRICE_WINDOW_HOURS: Final = 48

# Platforms
PLATFORMS: Final = ["switch", "sensor", "binary_sensor", "number", "button"]

# Attributes
ATTR_SCHEDULE: Final = "schedule"
ATTR_NEXT_HEATING: Final = "next_heating"
ATTR_CURRENT_PRICE: Final = "current_price"
ATTR_MANUAL_OVERRIDE_END: Final = "manual_override_end"
ATTR_LAST_HEATING: Final = "last_heating"

# Services
SERVICE_FORCE_HEAT: Final = "force_heat"
SERVICE_SKIP_NEXT: Final = "skip_next"
SERVICE_RECALCULATE: Final = "recalculate"
