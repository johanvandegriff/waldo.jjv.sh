#!/usr/bin/env python3
import cv2
import numpy as np
import sys

def convert_to_black_white_red(image_path, output_path, any_hue=False):
    print("Reading the image...")
    image = cv2.imread(image_path)

    print("Converting to HSV...")
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    if any_hue:
        print("Processing any color hue, avoiding very dark and very bright colors...")
        # Mask for not too dark and not too bright colors
        saturation_mask = cv2.inRange(hsv, (0, 30, 30), (180, 255, 255))
    else:
        print("Isolating the red color in the original image...")
        t1 = 120
        t2 = 70
        lower_red1 = np.array([0, t1, t2])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, t1, t2])
        upper_red2 = np.array([180, 255, 255])
#        lower_red1 = np.array([0, 120, 70])
#        upper_red1 = np.array([10, 255, 255])
#        lower_red2 = np.array([170, 120, 70])
#        upper_red2 = np.array([180, 255, 255])
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        saturation_mask = mask1 | mask2

    print("Setting the target color to pure red...")
    target_color = np.zeros_like(image)
    target_color[:, :] = [0, 0, 255]  # BGR format for red

    print("Converting to grayscale for thresholding...")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    print("Applying Otsu's thresholding for black and white image...")
    _, black_and_white = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    print("Converting black and white image to 3-channel BGR format...")
    black_and_white_bgr = cv2.cvtColor(black_and_white, cv2.COLOR_GRAY2BGR)

    print("Creating a binary mask of non-target areas...")
    non_target_areas = cv2.bitwise_not(saturation_mask)

    print("Applying the non-target mask to the black and white image...")
    black_and_white_non_target = cv2.bitwise_and(black_and_white_bgr, black_and_white_bgr, mask=non_target_areas)

    print("Applying the saturation mask to the target color (pure red)...")
    red_image = cv2.bitwise_and(target_color, target_color, mask=saturation_mask)

    print("Combining black & white image with pure red color in target areas...")
    final_image = cv2.bitwise_or(black_and_white_non_target, red_image)

    print("Saving the output image...")
    cv2.imwrite(output_path, final_image)
    print("Image processing complete. Output saved at:", output_path)

# Using command line arguments for input and output paths
any_hue_flag = '--any-hue' in sys.argv
if any_hue_flag: sys.argv.remove('--any-hue')
if len(sys.argv) >= 2:
    i = sys.argv[1]
    o = '.'.join(i.split('.')[:-1]) + '_rbw.png'
    if i != o:
      sys.argv.append(o)
if len(sys.argv) < 3:
    print("Usage: python script.py input_image.jpg [output_image.png] [--any-hue]")
else:
    convert_to_black_white_red(sys.argv[1], sys.argv[2], any_hue=any_hue_flag)
