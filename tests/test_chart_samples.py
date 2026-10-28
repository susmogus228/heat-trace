import pytest
from fastapi.testclient import TestClient
from heattrace.api import app
from heattrace.chart_samples import build_chart_samples


def test_each_scope_uses_only_its_actual_holdout_regions_and_dates():
    sets=build_chart_samples(limit=12)
    assert set(sets)=={'spatial_holdout','temporal_holdout','spatiotemporal_holdout'}
    for scope, group in sets.items():
        assert len(group['points'])==12
        for p in group['points']:
            assert (p['column'] >= 105) == (scope!='temporal_holdout')
            assert (p['scene'].endswith('20240721_02_T1')) == (scope!='spatial_holdout')


def test_unavailable_reason_prioritizes_water_and_clouds():
    from heattrace.api import unavailable_reason
    assert unavailable_reason(1<<7)=='water'
    assert unavailable_reason(1<<3)=='cloud'
    assert unavailable_reason(1<<4)=='shadow'
    assert unavailable_reason(0)=='other'


def test_chart_samples_api_exposes_three_scopes():
    r=TestClient(app).get('/api/chart-samples')
    assert r.status_code==200 and set(r.json())=={'spatial_holdout','temporal_holdout','spatiotemporal_holdout'}
