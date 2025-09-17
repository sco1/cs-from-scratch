import sys

import numpy as np
import pygame

from cs_from_scratch.KNN.digit import Digit
from cs_from_scratch.KNN.knn import KNN
from tests.KNN.test_knn import DIGITS_DATA_CSV

PIXEL_WIDTH = 8
PIXEL_HEIGHT = 8
P_TO_D = 16 / 255  # Pixel to digit scale factor
D_TO_P = 255 / 16  # Digit to pixel scale factor
DEFAULT_K = 9
WHITE = (255, 255, 255)


def recognizer() -> None:
    """
    Use your mouse to draw a digit & see how the classifier performs.

    Keyboard commands:
        * `C` - Classify the current drawing
        * `E` - Clear the drawing area
        * `P` - Predict what digit the current drawing should look like
    """
    digit_pixels = np.zeros((PIXEL_HEIGHT, PIXEL_WIDTH, 3), dtype=np.uint32)
    digits_knn = KNN(Digit, DIGITS_DATA_CSV, has_header=False)

    pygame.init()
    screen = pygame.display.set_mode(
        size=(PIXEL_WIDTH, PIXEL_HEIGHT), flags=pygame.SCALED | pygame.RESIZABLE
    )
    pygame.display.set_caption("Digit Recognizer")

    while True:
        pygame.surfarray.blit_array(screen, digit_pixels)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                key_name = pygame.key.name(event.key)
                if key_name == "c":  # Classify the drawing
                    pixels = digit_pixels.transpose((1, 0, 2))[:, :, 0].flatten() * P_TO_D
                    classified_digit = digits_knn.classify(DEFAULT_K, Digit("", pixels))

                    print(f"Classified as {classified_digit}")
                elif key_name == "e":  # Erase the drawing
                    digit_pixels.fill(0)

                elif key_name == "p":  # Predict what the digit should look like
                    pixels = digit_pixels.transpose((1, 0, 2))[:, :, 0].flatten() * P_TO_D
                    predicted_pixels = digits_knn.predict(DEFAULT_K, Digit("", pixels), "pixels")
                    predicted_pixels = (
                        predicted_pixels.reshape((PIXEL_HEIGHT, PIXEL_WIDTH)).transpose((1, 0))
                        * D_TO_P
                    )
                    digit_pixels = np.stack(
                        (predicted_pixels, predicted_pixels, predicted_pixels), axis=2
                    )
            elif (
                (event.type == pygame.MOUSEBUTTONDOWN)
                or event.type == pygame.MOUSEMOTION
                and pygame.mouse.get_pressed()[0]
            ):
                x, y = event.pos
                if (x < PIXEL_WIDTH) and (y < PIXEL_HEIGHT):
                    digit_pixels[x][y] = WHITE
            elif event.type == pygame.QUIT:
                sys.exit()


if __name__ == "__main__":
    recognizer()
