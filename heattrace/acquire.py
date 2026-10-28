"""Acquire bounded Landsat source windows from Microsoft Planetary Computer STAC."""
import json
import urllib.parse
import urllib.request
import urllib.error
import time
from pathlib import Path

BANDS = ('lwir11', 'red', 'nir08', 'swir16', 'qa_pixel')
BBOX = (114.15, 30.42, 114.5, 30.72)
SCENES = [
 'LC08_L2SP_123039_20230609_02_T1',
 'LC09_L2SP_123039_20230804_02_T1',
 'LC09_L2SP_123039_20240705_02_T1',
 'LC09_L2SP_123039_20240721_02_T1',
]


def validate_scene(scene):
    if '_L2SP_' not in scene.get('id','') or not set(BANDS) <= scene.get('assets',{}).keys():
        raise ValueError('Scene requires L2SP surface temperature and five bands')


def get_json(url):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 4:
                raise
            time.sleep(5 * (attempt + 1))


def acquire():
    import numpy as np
    import rasterio
    from rasterio.windows import from_bounds
    from rasterio.warp import transform_bounds
    from rasterio.warp import reproject
    from rasterio.transform import from_bounds as grid_from_bounds
    from affine import Affine
    from rasterio.enums import Resampling
    output = Path('data/scenes'); output.mkdir(parents=True, exist_ok=True)
    access_query = None
    for ident in SCENES:
        target = output / (ident + '.npz')
        if target.exists():
            print('Cached:', ident, flush=True); continue
        scene = get_json('https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2/items/' + ident)
        validate_scene(scene)
        arrays = {}
        print('Downloading:', ident, flush=True)
        for band in BANDS:
            href = scene['assets'][band]['href']
            if access_query is None:
                signed_url = get_json('https://planetarycomputer.microsoft.com/api/sas/v1/sign?' + urllib.parse.urlencode({'href':href}))['href']
                access_query = urllib.parse.urlsplit(signed_url).query
            signed = href + '?' + access_query
            with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif', GDAL_HTTP_MAX_RETRY='3'):
                with rasterio.open(signed) as src:
                    bounds = transform_bounds('EPSG:4326', src.crs, *BBOX, densify_pts=21)
                    window = from_bounds(*bounds, transform=src.transform).round_offsets().round_lengths()
                    sample = src.read(1, window=window, out_shape=(120,140), resampling=Resampling.nearest, boundless=True)
                    source_transform = src.window_transform(window) * Affine.scale(window.width/140, window.height/120)
                    destination = np.zeros((120,140), dtype=sample.dtype)
                    reproject(sample, destination, src_transform=source_transform, src_crs=src.crs,
                              dst_transform=grid_from_bounds(*BBOX, 140, 120), dst_crs='EPSG:4326',
                              src_nodata=0, dst_nodata=0, resampling=Resampling.nearest)
                    arrays[band] = destination
            print('  read', band, flush=True)
        np.savez_compressed(target, **arrays)
        metadata={'id':ident, 'datetime':scene['properties']['datetime'], 'cloud_cover_scene_percent':scene['properties'].get('eo:cloud_cover'), 'bbox':BBOX, 'source':'https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2/items/'+ident, 'band_names':list(BANDS), 'shape':[120,140], 'sampling':'nearest neighbour from source pixels; output grid not a new thermal measurement resolution'}
        target.with_suffix('.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')


if __name__ == '__main__':
    acquire()
