def check_road_block(source, destination):
    
    blocked_routes = [
        ("Bengaluru", "Mysuru"),
        ("Mysuru", "Bengaluru")
    ]

    if (source, destination) in blocked_routes:
        return True

    return False