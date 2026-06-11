def weather_effect(original_cost, severity):
    """
    severity:
    1 = Light Rain
    2 = Moderate Rain
    3 = Heavy Rain
    """

    factors = {
        1: 1.10,
        2: 1.25,
        3: 1.50
    }

    new_cost = original_cost * factors.get(severity, 1)

    return new_cost