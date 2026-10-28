import numpy as np
import pytest
from heattrace.science import temperature_c, reflectance, valid_pixels, features, spatial_split


def test_temperature_and_reflectance_scaling():
    assert temperature_c(np.array([44947]))[0] == pytest.approx(29.476, abs=.01)
    assert reflectance(np.array([18639]))[0] == pytest.approx(.3125725)


def test_cloud_shadow_snow_water_and_fill_are_excluded():
    qa = np.array([0, 1, 1<<1, 1<<2, 1<<3, 1<<4, 1<<5, 1<<7], dtype='uint16')
    mask = valid_pixels(qa, np.ones(8), np.ones(8), np.ones(8), np.ones(8))
    assert mask.tolist() == [True, False, False, False, False, False, False, False]


def test_missing_or_degenerate_optical_values_are_invalid():
    qa = np.zeros(3, dtype='uint16')
    assert valid_pixels(qa, np.array([1,0,1]), np.array([1,1,0]), np.ones(3), np.ones(3)).tolist() == [True,False,False]


def test_features_ndvi_uses_scaled_values():
    x = features(np.array([18639]), np.array([24000]), np.array([19000]))
    red=18639*.0000275-.2; nir=24000*.0000275-.2
    assert x[0,3] == pytest.approx((nir-red)/(nir+red))


def test_spatial_split_has_gap_and_disjoint_test():
    train, held = spatial_split(100)
    assert train.sum() > 0 and held.sum() > 0 and not np.any(train & held)
    assert np.flatnonzero(held)[0] - np.flatnonzero(train)[-1] >= 2
