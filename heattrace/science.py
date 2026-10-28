"""Landsat Collection 2 transformations and leakage-resistant spatial partitioning."""
import numpy as np


def temperature_c(raw):
    return np.asarray(raw, dtype=float) * .00341802 + 149.0 - 273.15


def reflectance(raw):
    return np.asarray(raw, dtype=float) * .0000275 - .2


def valid_pixels(qa, thermal, red, nir, swir):
    qa = np.asarray(qa, dtype=np.uint16)
    excluded = sum(1 << bit for bit in (0, 1, 2, 3, 4, 5, 7))
    result = (qa & excluded) == 0
    for band in (thermal, red, nir, swir):
        result &= np.asarray(band) > 0
    return result


def features(red, nir, swir):
    r, n, s = reflectance(red), reflectance(nir), reflectance(swir)
    ndvi = np.divide(n-r, n+r, out=np.zeros_like(n), where=np.abs(n+r)>1e-6)
    ndbi = np.divide(s-n, s+n, out=np.zeros_like(n), where=np.abs(s+n)>1e-6)
    return np.stack([r,n,s,ndvi,ndbi], axis=-1)


def spatial_split(width):
    x = np.arange(width)
    return x < int(width*.65), x >= int(width*.75)
