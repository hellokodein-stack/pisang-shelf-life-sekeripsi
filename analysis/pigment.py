import cv2
import numpy as np


def calculate_pigment(segmented_img, mask):
    """
    Menghitung persentase pigmentasi kuning.
    """

    hsv = cv2.cvtColor(segmented_img, cv2.COLOR_BGR2HSV)

    lower_yellow = np.array([15, 40, 40])
    upper_yellow = np.array([40, 255, 255])

    yellow = cv2.inRange(
        hsv,
        lower_yellow,
        upper_yellow
    )

    yellow = cv2.bitwise_and(
        yellow,
        yellow,
        mask=mask
    )

    yellow_pixels = np.count_nonzero(yellow)
    total_pixels = np.count_nonzero(mask)

    if total_pixels == 0:
        return 0

    return round(
        yellow_pixels / total_pixels * 100,
        2
    )