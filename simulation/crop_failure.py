def crop_failure_effect(original_supply, loss_percentage):

    remaining_supply = original_supply * (
        1 - loss_percentage / 100
    )

    return remaining_supply