import cv2
import numpy as np


def calculate_necrosis(segmented_img, mask):
    """
    Menghitung persentase area nekrosis.
    """

    hsv = cv2.cvtColor(segmented_img, cv2.COLOR_BGR2HSV)

    lower_brown = np.array([0, 50, 0])
    upper_brown = np.array([20, 255, 70])

    brown = cv2.inRange(
        hsv,
        lower_brown,
        upper_brown
    )

    brown = cv2.bitwise_and(
        brown,
        brown,
        mask=mask
    )

    brown_pixels = np.count_nonzero(brown)
    total_pixels = np.count_nonzero(mask)

    if total_pixels == 0:
        return 0

    return round(
        brown_pixels / total_pixels * 100,
        2
    )