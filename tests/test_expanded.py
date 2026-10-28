import numpy as np
from heattrace.expanded import outside_original_mask, EXPANDED_BBOX, EXPANDED_SHAPE


def test_new_region_excludes_all_original_area_and_buffer():
    mask=outside_original_mask()
    rows,cols=EXPANDED_SHAPE
    west,south,east,north=EXPANDED_BBOX
    lat=north-(np.arange(rows)+.5)*(north-south)/rows
    lon=west+(np.arange(cols)+.5)*(east-west)/cols
    old_and_buffer=(lat[:,None]>=30.39)&(lat[:,None]<=30.75)&(lon[None,:]>=114.12)&(lon[None,:]<=114.53)
    assert not np.any(mask & old_and_buffer)
    assert mask.any()


def test_grid_retains_nominal_sampling_step():
    rows,cols=EXPANDED_SHAPE
    west,south,east,north=EXPANDED_BBOX
    assert abs((east-west)/cols-.0025)<1e-9
    assert abs((north-south)/rows-.0025)<1e-9


def test_expanded_api_uses_its_own_bounds_and_test_results():
    from fastapi.testclient import TestClient
    from heattrace.api import app
    client=TestClient(app)
    report=client.get('/api/expanded/report')
    assert report.status_code==200
    payload=report.json()
    assert payload['bbox']==list(EXPANDED_BBOX)
    assert payload['results']['model']['count']==payload['population']
    assert payload['population']>0
    assert client.get('/api/expanded/layers/observed.png').status_code==200
    assert client.get('/api/expanded/pixel',params={'lat':0,'lon':0}).status_code==422


def test_expanded_metrics_and_chart_points_match_frozen_model_and_source():
    import json
    import joblib
    from sklearn.metrics import mean_absolute_error
    from heattrace.expanded import EXPANDED
    from heattrace.science import valid_pixels,features,temperature_c
    report=json.loads((EXPANDED/'report.json').read_text())
    with np.load(EXPANDED/'scene.npz') as d:
        q,t,r,n,s=[d[k] for k in ('qa_pixel','lwir11','red','nir08','swir16')]
        x=features(r,n,s); y=temperature_c(t)
        valid=valid_pixels(q,t,r,n,s)&np.isfinite(x).all(axis=2)&(np.abs(x[:,:,3])<=1)&(np.abs(x[:,:,4])<=1)
    mask=valid&outside_original_mask()
    m=joblib.load('data/output/model.joblib');pred=m.predict(x[mask])
    assert int(mask.sum())==report['population']
    assert abs(mean_absolute_error(y[mask],pred)-report['results']['model']['mae_c'])<.0001
    source_points=set(zip(np.round(x[:,:,3][mask],4),np.round(y[mask],2),np.round(pred,2)))
    assert len(report['chart_sample'])==240
    assert all((p['ndvi'],p['observed'],p['predicted']) in source_points for p in report['chart_sample'])
