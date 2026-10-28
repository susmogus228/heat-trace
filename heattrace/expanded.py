"""Independent expansion of the frozen Wuhan experiment without retraining."""
from pathlib import Path
import json,urllib.parse
import joblib
import numpy as np
from affine import Affine
from PIL import Image
from rasterio.enums import Resampling
from rasterio.transform import from_bounds as grid_from_bounds
from rasterio.warp import transform_bounds,reproject
from rasterio.windows import from_bounds
import rasterio
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from heattrace.acquire import SCENES,BANDS,get_json,validate_scene
from heattrace.model import load,split_masks,regression_metrics,heat_image,chart_sample
from heattrace.science import features,temperature_c,valid_pixels

EXPANDED_BBOX=(114.0,30.30,114.65,30.84)
EXPANDED_SHAPE=(216,260)
ORIGINAL_BBOX=(114.15,30.42,114.50,30.72)
BUFFER_DEGREES=.03
ROOT=Path(__file__).resolve().parent.parent
EXPANDED=ROOT/'data'/'expanded'


def outside_original_mask():
    rows,cols=EXPANDED_SHAPE; west,south,east,north=EXPANDED_BBOX
    lat=north-(np.arange(rows)+.5)*(north-south)/rows
    lon=west+(np.arange(cols)+.5)*(east-west)/cols
    w,s,e,n=ORIGINAL_BBOX; b=BUFFER_DEGREES
    return ~((lat[:,None]>=s-b)&(lat[:,None]<=n+b)&(lon[None,:]>=w-b)&(lon[None,:]<=e+b))


def acquire():
    EXPANDED.mkdir(parents=True,exist_ok=True)
    target=EXPANDED/'scene.npz';meta=EXPANDED/'scene.json'
    if target.exists() and meta.exists():
        print('Using prepared expanded scene',flush=True);return
    ident=SCENES[-1]
    scene=get_json('https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2/items/'+ident);validate_scene(scene)
    arrays={};access_query=None;rows,cols=EXPANDED_SHAPE
    for band in BANDS:
        href=scene['assets'][band]['href']
        if access_query is None:
            signed=get_json('https://planetarycomputer.microsoft.com/api/sas/v1/sign?'+urllib.parse.urlencode({'href':href}))['href']
            access_query=urllib.parse.urlsplit(signed).query
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',GDAL_HTTP_MAX_RETRY='3'):
            with rasterio.open(href+'?'+access_query) as src:
                bounds=transform_bounds('EPSG:4326',src.crs,*EXPANDED_BBOX,densify_pts=21)
                window=from_bounds(*bounds,transform=src.transform).round_offsets().round_lengths()
                sampled=src.read(1,window=window,out_shape=(rows,cols),resampling=Resampling.nearest,boundless=True)
                src_transform=src.window_transform(window)*Affine.scale(window.width/cols,window.height/rows)
                dest=np.zeros((rows,cols),dtype=sampled.dtype)
                reproject(sampled,dest,src_transform=src_transform,src_crs=src.crs,dst_transform=grid_from_bounds(*EXPANDED_BBOX,cols,rows),dst_crs='EPSG:4326',src_nodata=0,dst_nodata=0,resampling=Resampling.nearest)
                arrays[band]=dest
        print('Read',band,flush=True)
    np.savez_compressed(target,**arrays)
    metadata={'id':ident,'datetime':scene['properties']['datetime'],'cloud_cover_scene_percent':scene['properties'].get('eo:cloud_cover'),'bbox':EXPANDED_BBOX,'shape':EXPANDED_SHAPE,'source':'https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2/items/'+ident,'sampling':'nearest neighbour and geographic reprojection; not building-scale thermal resolution'}
    meta.write_text(json.dumps(metadata,indent=2),encoding='utf-8')


def build():
    with np.load(EXPANDED/'scene.npz') as d:
        q,t,r,n,s=[d[k] for k in ('qa_pixel','lwir11','red','nir08','swir16')]
        x=features(r,n,s);obs=temperature_c(t)
        valid=valid_pixels(q,t,r,n,s)&np.isfinite(x).all(axis=2)&(np.abs(x[:,:,3])<=1)&(np.abs(x[:,:,4])<=1)
    mask=valid & outside_original_mask()
    if mask.sum()<100:raise ValueError('Insufficient valid pixels in the expanded independent region')
    model=joblib.load(ROOT/'data'/'output'/'model.joblib')
    pred=np.zeros(obs.shape);pred[valid]=model.predict(x[valid])
    # Reconstruct the original baselines from original training data only.
    train_x=[];train_y=[]
    for ident in SCENES[:3]:
        tx,ty,tvalid=load(ident);training,_=split_masks(tvalid)
        train_x.append(tx[training]);train_y.append(ty[training])
    X=np.concatenate(train_x);Y=np.concatenate(train_y)
    linear=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(X,Y)
    mean=DummyRegressor(strategy='mean').fit(X,Y)
    result={'model':regression_metrics(obs[mask],pred[mask]),'linear':regression_metrics(obs[mask],linear.predict(x[mask])),'baseline':regression_metrics(obs[mask],mean.predict(x[mask]))}
    heat_image(obs,valid,EXPANDED/'observed.png',10,55);heat_image(pred,valid,EXPANDED/'predicted.png',10,55);heat_image(pred-obs,valid,EXPANDED/'difference.png',-10,10,True)
    np.savez_compressed(EXPANDED/'display.npz',observed=obs,predicted=pred,valid=valid,ndvi=x[:,:,3])
    res={'bbox':EXPANDED_BBOX,'original_bbox':ORIGINAL_BBOX,'shape':EXPANDED_SHAPE,'buffer_degrees':BUFFER_DEGREES,'display_scene':SCENES[-1],'results':result,'chart_sample':chart_sample(x[:,:,3],obs,pred,mask),'population':int(mask.sum()),'valid_total':int(valid.sum()),'definition':'New expanded area outside original study extent plus a 0.03 degree buffer, on the held-out 21 July 2024 scene. The frozen original forest is used without retraining; mean and linear baselines are refit on the original training data only.'}
    (EXPANDED/'report.json').write_text(json.dumps(res,indent=2),encoding='utf-8')
    print(json.dumps({'valid':res['valid_total'],'independent_test_pixels':res['population'],'results':result},indent=2),flush=True)


if __name__=='__main__':acquire();build()
