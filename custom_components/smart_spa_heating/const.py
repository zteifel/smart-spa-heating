"""Constants for Smart Spa Heating integration."""
from typing import Final

DOMAIN: Final = "smart_spa_heating"

# Configuration keys
CONF_NORDPOOL_ENTITY: Final = "nordpool_entity"
CONF_CLIMATE_ENTITY: Final = "climate_entity"
CONF_HEATING_FREQUENCY: Final = "heating_frequency"
CONF_HEATING_DURATION: Final = "heating_duration"
CONF_PRICE_THRESHOLD: Final = "price_threshold"
CONF_HIGH_PRICE_THRESHOLD: Final = "high_price_threshold"
CONF_HEATING_TEMPERATURE: Final = "heating_temperature"
CONF_IDLE_TEMPERATURE: Final = "idle_temperature"
CONF_MANUAL_OVERRIDE_DURATION: Final = "manual_override_duration"
CONF_NUM_PEAKS: Final = "num_peaks"
CONF_PEAK_COOLING_TIME: Final = "peak_cooling_time"
CONF_SCHEDULING_ALGORITHM: Final = "scheduling_algorithm"
CONF_PP_MAX_TEMPERATURE: Final = "pp_max_temperature"
CONF_PP_MIN_TEMPERATURE: Final = "pp_min_temperature"
CONF_LOOKAHEAD_HOURS: Final = "lookahead_hours"

# Default values
DEFAULT_HEATING_FREQUENCY: Final = 3  # hours
DEFAULT_HEATING_DURATION: Final = 45  # minutes
DEFAULT_PRICE_THRESHOLD: Final = 1.5  # currency agnostic - always heat below this
DEFAULT_HIGH_PRICE_THRESHOLD: Final = 3.0  # currency agnostic - never heat above this
DEFAULT_HEATING_TEMPERATURE: Final = 37.5  # °C
DEFAULT_IDLE_TEMPERATURE: Final = 35.0  # °C
DEFAULT_MANUAL_OVERRIDE_DURATION: Final = 3  # hours
DEFAULT_NUM_PEAKS: Final = 3
DEFAULT_PEAK_COOLING_TIME: Final = 60  # minutes
DEFAULT_SCHEDULING_ALGORITHM: Final = "interval"
DEFAULT_PP_MAX_TEMPERATURE: Final = 40.0  # °C
DEFAULT_PP_MIN_TEMPERATURE: Final = 34.0  # °C
DEFAULT_LOOKAHEAD_HOURS: Final = 3  # hours

# Algorithm choices
ALGORITHM_INTERVAL: Final = "interval"
ALGORITHM_PEAK_AVOIDANCE: Final = "peak_avoidance"
ALGORITHM_PRICE_PROPORTIONAL: Final = "price_proportional"

# Limits
MIN_HEATING_FREQUENCY: Final = 1
MAX_HEATING_FREQUENCY: Final = 48
MIN_HEATING_DURATION: Final = 15
MAX_HEATING_DURATION: Final = 240
MIN_PRICE_THRESHOLD: Final = -1000.0
MAX_PRICE_THRESHOLD: Final = 1000.0
MIN_HIGH_PRICE_THRESHOLD: Final = -1000.0
MAX_HIGH_PRICE_THRESHOLD: Final = 1000.0
MIN_HEATING_TEMPERATURE: Final = 20.0
MAX_HEATING_TEMPERATURE: Final = 42.0
MIN_IDLE_TEMPERATURE: Final = 5.0
MAX_IDLE_TEMPERATURE: Final = 42.0  # No upper limit restriction
MIN_MANUAL_OVERRIDE_DURATION: Final = 1
MAX_MANUAL_OVERRIDE_DURATION: Final = 12
MIN_NUM_PEAKS: Final = 1
MAX_NUM_PEAKS: Final = 20
MIN_PEAK_COOLING_TIME: Final = 15
MAX_PEAK_COOLING_TIME: Final = 480
MIN_PP_MAX_TEMPERATURE: Final = 20.0
MAX_PP_MAX_TEMPERATURE: Final = 42.0
MIN_PP_MIN_TEMPERATURE: Final = 5.0
MAX_PP_MIN_TEMPERATURE: Final = 42.0
MIN_LOOKAHEAD_HOURS: Final = 1
MAX_LOOKAHEAD_HOURS: Final = 12

# Platforms
PLATFORMS: Final = ["switch", "sensor", "binary_sensor", "number", "button", "select"]

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
