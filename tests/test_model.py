import numpy as np
from heattrace.model import regression_metrics, split_masks

def test_metrics_are_computed_against_truth():
    m=regression_metrics(np.array([10.,20.]), np.array([12.,16.]))
    assert m['mae_c'] == 3.0
    assert abs(m['rmse_c'] - np.sqrt(10)) < 1e-4

def test_spatial_masks_exclude_gap_and_dont_overlap():
    train, test = split_masks(np.ones((3,100), dtype=bool))
    assert not (train & test).any()
    assert not train[:,65:75].any() and not test[:,65:75].any()


def test_chart_sample_uses_only_held_out_cells():
    from heattrace.model import chart_sample
    ndvi=np.array([[.1,.2],[.3,.4]])
    obs=np.array([[20.,21.],[22.,23.]])
    pred=np.array([[20.,20.],[20.,20.]])
    mask=np.array([[False,False],[False,True]])
    points=chart_sample(ndvi,obs,pred,mask)
    assert points == [{'ndvi':.4,'observed':23.,'predicted':20.}]
