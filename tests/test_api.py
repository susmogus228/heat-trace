from fastapi.testclient import TestClient
from heattrace.api import app

client=TestClient(app)

def test_report_exposes_real_holdouts():
    response=client.get('/api/report'); assert response.status_code==200
    assert 'spatiotemporal_holdout' in response.json()['results']

def test_out_of_bounds_point_is_rejected():
    assert client.get('/api/pixel',params={'lat':0,'lon':0}).status_code==422

def test_invalid_layer_returns_404():
    assert client.get('/api/layers/nonexistent.png').status_code==404
from fastapi.testclient import TestClient
from heattrace.api import app

client=TestClient(app)

def test_example_location_has_observed_and_predicted_values():
    r=client.get('/api/pixel',params={'lat':30.56875,'lon':114.25125})
    assert r.status_code == 200 and r.json()['valid']
    assert 'observed_c' in r.json() and 'predicted_c' in r.json()

def test_report_includes_linear_and_mean_baselines():
    data=client.get('/api/report').json()
    assert {'baseline','linear','model'} <= set(data['results']['spatiotemporal_holdout'])


def test_missing_display_grid_returns_service_unavailable(tmp_path, monkeypatch):
    import json
    import heattrace.api as api
    (tmp_path/'report.json').write_text(json.dumps({'bbox':[114.15,30.42,114.5,30.72]}))
    monkeypatch.setattr(api,'OUTPUT',tmp_path)
    response=client.get('/api/pixel',params={'lat':30.57,'lon':114.25})
    assert response.status_code == 503
    assert 'not prepared' in response.json()['detail'].lower()
