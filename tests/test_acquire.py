from heattrace.acquire import validate_scene
import pytest

def test_scene_requires_surface_temperature_and_all_bands():
    with pytest.raises(ValueError):
        validate_scene({'id':'LC08_L2SP_example','assets':{'red':{}}})


def test_rejects_scene_without_surface_temperature_product():
    with pytest.raises(ValueError):
        validate_scene({'id':'LC08_L2SR_example','assets':{k:{} for k in ['lwir11','red','nir08','swir16','qa_pixel']}})
