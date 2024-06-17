humidity_config = {
    'min_humidity': 30.0,
    'max_humidity': 75.0,
    'sensor_cooldown_period_watering': 10 * 1_000,
    'sensor_cooldown_period_draining': 60 * 1_000
}
pump_config = {
    'pump_duration': 5 * 1_000,
    'pump_cooldown': 0 * 1_000,
    'pump_cap_time': 15 * 1_000
}
sensor_config = {
    'min_reading': 42000,
    'max_reading': 65535,
}