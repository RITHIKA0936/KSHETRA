def increase_festival_demand(current_demand, crop):
    
    festival_crops = {
        "Marigold": 2.0,
        "Tomato": 1.25,
        "Carrot": 1.15
    }

    factor = festival_crops.get(crop, 1)

    new_demand = current_demand * factor

    return new_demand