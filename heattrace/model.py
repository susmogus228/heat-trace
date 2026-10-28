"""Frozen scene holdouts for the Landsat experiment."""
from pathlib import Path
import json
import joblib
import numpy as np
from PIL import Image
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from heattrace.acquire import SCENES, BBOX
from heattrace.science import valid_pixels, features, temperature_c, spatial_split


def regression_metrics(y, pred):
    return {'count':len(y), 'mae_c':round(float(mean_absolute_error(y,pred)),4), 'rmse_c':round(float(np.sqrt(mean_squared_error(y,pred))),4), 'r2':round(float(r2_score(y,pred)),4)}


def split_masks(valid):
    a,b=spatial_split(valid.shape[1]); return valid & a[None,:], valid & b[None,:]


def chart_sample(ndvi, observed, predicted, mask, limit=240):
    coordinates=np.argwhere(mask)
    if len(coordinates)>limit:
        coordinates=coordinates[np.random.default_rng(42).choice(len(coordinates),size=limit,replace=False)]
    return [{'ndvi':round(float(ndvi[r,c]),4), 'observed':round(float(observed[r,c]),2),
             'predicted':round(float(predicted[r,c]),2)} for r,c in coordinates]


def load(ident):
    with np.load(Path('data/scenes')/(ident+'.npz')) as scene:
        qa,t,r,n,s=[scene[k] for k in ('qa_pixel','lwir11','red','nir08','swir16')]
        x=features(r,n,s); valid=valid_pixels(qa,t,r,n,s) & np.isfinite(x).all(axis=2)
        valid &= (np.abs(x[:,:,3])<=1) & (np.abs(x[:,:,4])<=1)
        return x,temperature_c(t),valid


def heat_image(values, mask, path, low, high, difference=False):
    ratio=np.clip((values-low)/(high-low),0,1)
    if difference:
        stops=np.array([[38,112,170],[240,239,230],[204,65,43]],float)
    else:
        stops=np.array([[43,71,115],[63,130,150],[222,194,106],[237,115,41],[164,38,29]],float)
    idx=ratio*(len(stops)-1); lower=np.floor(idx).astype(int); upper=np.minimum(lower+1,len(stops)-1)
    colors=stops[lower]*(1-(idx-lower))[...,None]+stops[upper]*(idx-lower)[...,None]
    rgba=np.concatenate([colors,np.where(mask,200,0)[...,None]],axis=-1).astype('uint8')
    Image.fromarray(rgba,'RGBA').save(path)


def run():
    out=Path('data/output');out.mkdir(parents=True,exist_ok=True)
    scenes=[load(s) for s in SCENES]
    train_x=[];train_y=[]
    for x,y,valid in scenes[:3]:
        train,_=split_masks(valid); train_x.append(x[train]);train_y.append(y[train])
    X=np.concatenate(train_x);Y=np.concatenate(train_y)
    if len(Y)<500: raise RuntimeError('Insufficient valid training observations')
    print('Training pixels',len(Y),flush=True)
    model=RandomForestRegressor(n_estimators=80, max_depth=14, min_samples_leaf=5, random_state=42, n_jobs=-1).fit(X,Y)
    base=DummyRegressor(strategy='mean').fit(X,Y)
    linear=make_pipeline(StandardScaler(),Ridge(alpha=10)).fit(X,Y)
    results={}
    for name, indices, region in [('spatial_holdout',range(3),'test'),('temporal_holdout',[3],'train'),('spatiotemporal_holdout',[3],'test')]:
        xs=[];ys=[]
        for i in indices:
            x,y,valid=scenes[i]; a,b=split_masks(valid); m=a if region=='train' else b
            xs.append(x[m]);ys.append(y[m])
        x=np.concatenate(xs); y=np.concatenate(ys)
        if len(y)<100: raise RuntimeError('Insufficient held-out observations: '+name)
        results[name]={'model':regression_metrics(y,model.predict(x)),'baseline':regression_metrics(y,base.predict(x)),'linear':regression_metrics(y,linear.predict(x))}
    x,y,valid=scenes[3]; pred=np.zeros(y.shape); pred[valid]=model.predict(x[valid]); diff=pred-y
    heat_image(y,valid,out/'observed.png',10,55);heat_image(pred,valid,out/'predicted.png',10,55);heat_image(diff,valid,out/'difference.png',-10,10,True)
    np.savez_compressed(out/'display.npz', observed=y, predicted=pred, valid=valid, ndvi=x[:,:,3])
    joblib.dump(model,out/'model.joblib')
    _, chart_mask=split_masks(valid)
    report={'city':'Wuhan, China','bbox':BBOX,'display_scene':SCENES[3], 'train_scenes':SCENES[:3], 'training_pixels':len(Y),'results':results,'chart_sample':chart_sample(x[:,:,3],y,pred,chart_mask),'features':['red reflectance','near infrared reflectance','shortwave infrared reflectance','NDVI','NDBI'],'method':'Random forest trained on Landsat optical reflectance to estimate surface temperature for the same satellite scene, not a weather forecast.', 'limits':['Reflectance and the Landsat surface-temperature product are related satellite-derived measurements; this is not independent ground-truth validation.', 'Spatial holdout is the eastern sector with a gap; pixels remain spatially correlated.', 'Temporal holdout is one previously unseen scene; not a guarantee on other dates or cities.', 'Cloud, shadow, snow, water and missing data masked; pixels are sampled and do not represent building-scale temperatures.']}
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2),flush=True)

if __name__=='__main__': run()
