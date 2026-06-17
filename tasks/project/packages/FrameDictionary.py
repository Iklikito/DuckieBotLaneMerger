import cv2
import numpy as np


class FrameDictionary:
    def __init__(self, frame_bgr: np.ndarray):
        self._bgr = frame_bgr
        self._rgb = None
        self._hsv = None
        self._gray = None

    @property
    def bgr(self) -> np.ndarray:
        return self._bgr

    @property
    def rgb(self) -> np.ndarray:
        if self._bgr is None:
            return None
        if self._rgb is None:
            self._rgb = cv2.cvtColor(self._bgr, cv2.COLOR_BGR2RGB)
        return self._rgb

    @property
    def hsv(self) -> np.ndarray:
        if self._bgr is None:
            return None
        if self._hsv is None:
            self._hsv = cv2.cvtColor(self._bgr, cv2.COLOR_BGR2HSV)
        return self._hsv

    @property
    def gray(self) -> np.ndarray:
        if self._bgr is None:
            return None
        if self._gray is None:
            self._gray = cv2.cvtColor(self._bgr, cv2.COLOR_BGR2GRAY)
        return self._gray