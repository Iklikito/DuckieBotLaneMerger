from enum import Enum

class AdjacentLane(Enum):
    north = 0
    east = 1
    south = 2
    west = 3

import cv2
import numpy as np


def main():
    IMAGE_PATH = "tasks/project/packages/images/simcal.png"

    image = cv2.imread(IMAGE_PATH)

    if image is None:
        raise FileNotFoundError(f"Could not load image: {IMAGE_PATH}")

    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    h_min, s_min, v_min = 179, 255, 255
    h_max, s_max, v_max = 0, 0, 0

    def mouse_callback(event, x, y, flags, param):
        nonlocal h_min, s_min, v_min, h_max, s_max, v_max

        if event == cv2.EVENT_LBUTTONDOWN:
            h, s, v = hsv_image[y, x]

            h_min = min(h_min, int(h))
            s_min = min(s_min, int(s))
            v_min = min(v_min, int(v))

            h_max = max(h_max, int(h))
            s_max = max(s_max, int(s))
            v_max = max(v_max, int(v))

            print(f"Clicked: ({x}, {y}) -> HSV = ({h}, {s}, {v})")
            print(
                f"Current Range:\n"
                f"  Lower = [{h_min}, {s_min}, {v_min}]\n"
                f"  Upper = [{h_max}, {s_max}, {v_max}]\n"
            )

            cv2.circle(image, (x, y), 4, (0, 0, 255), -1)
            cv2.imshow("Image", image)

    cv2.namedWindow("Image")
    cv2.setMouseCallback("Image", mouse_callback)

    print("Click on pixels to collect HSV values.")
    print("Press 'q' to finish.")

    while True:
        cv2.imshow("Image", image)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()

    print("\nFinal HSV Range:")
    print(f"Lower HSV = [{h_min}, {s_min}, {v_min}]")
    print(f"Upper HSV = [{h_max}, {s_max}, {v_max}]")

if __name__ == "__main__":
    main()