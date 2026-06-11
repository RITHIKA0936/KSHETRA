from optimization.crop_recommendation import recommend_crop


def main():

    print("========== KSHETRA ==========")

    # Farmer details
    location = "Kolar"
    land = 10

    # Crops the farmer can grow
    possible_crops = [
        "Tomato",
        "Carrot",
        "Marigold"
    ]

    # Get recommendation
    results, best_crop = recommend_crop(
        land,
        possible_crops
    )

    print("\nFarmer Location:", location)
    print("Land:", land, "acres")

    print("\nCrop Analysis:")
    print(results)

    print("\nBest Crop Recommendation:")
    print(best_crop)


if __name__ == "__main__":
    main()