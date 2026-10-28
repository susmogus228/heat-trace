"""Read-only API for the frozen Wuhan experiment."""
from pathlib import Path
import json
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

ROOT=Path(__file__).resolve().parent.parent
OUTPUT=ROOT/'data'/'output'
app=FastAPI(title='HeatTrace API', version='0.1.0', description='Observed and modelled Landsat surface temperature, not air temperature.')
app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:5173','http://localhost:5173'],allow_methods=['GET'],allow_headers=['*'])

@app.get('/api/report')
def report():
    path=OUTPUT/'report.json'
    if not path.is_file(): raise HTTPException(503,'Experiment data not prepared. Run the acquisition and model commands.')
    return json.loads(path.read_text(encoding='utf-8'))

@app.get('/api/chart-samples')
def chart_samples():
    path=OUTPUT/'chart_samples.json'
    if not path.is_file(): raise HTTPException(503,'Chart samples not prepared. Run the chart-samples command.')
    return json.loads(path.read_text(encoding='utf-8'))

def unavailable_reason(qa):
    if qa & 1: return 'missing'
    if qa & (1<<7): return 'water'
    if qa & (1<<4): return 'shadow'
    if qa & ((1<<1)|(1<<2)|(1<<3)): return 'cloud'
    if qa & (1<<5): return 'snow'
    return 'other'

@app.get('/api/layers/{filename}')
def layer(filename:str):
    if filename not in {'observed.png','predicted.png','difference.png'}: raise HTTPException(404,'Unknown layer')
    path=OUTPUT/filename
    if not path.is_file(): raise HTTPException(503,'Layer not prepared')
    return FileResponse(path,media_type='image/png')

def read_pixel(lat, lon, dataset_report, display, source):
    west,south,east,north=dataset_report['bbox']
    if not (west<=lon<east and south<lat<=north): raise HTTPException(422,'Point outside study area')
    if not display.is_file(): raise HTTPException(503,'Display grid not prepared. Run the model command.')
    with np.load(display) as d:
        rows,cols=d['valid'].shape; col=min(cols-1,int((lon-west)/(east-west)*cols)); row=min(rows-1,int((north-lat)/(north-south)*rows))
        if not d['valid'][row,col]:
            reason='other'
            if source.is_file():
                with np.load(source) as original:
                    reason=unavailable_reason(int(original['qa_pixel'][row,col]))
            return {'valid':False,'reason':reason,'message':'No valid satellite value for this location.'}
        obs=float(d['observed'][row,col]); pred=float(d['predicted'][row,col])
        return {'valid':True,'observed_c':round(obs,2),'predicted_c':round(pred,2),'difference_c':round(pred-obs,2),'ndvi':round(float(d['ndvi'][row,col]),3),'row':row,'column':col}

@app.get('/api/pixel')
def pixel(lat:float,lon:float):
    info=report();scene=info.get('display_scene','')
    return read_pixel(lat,lon,info,OUTPUT/'display.npz',ROOT/'data'/'scenes'/(Path(scene).name+'.npz'))

EXPANDED=ROOT/'data'/'expanded'

@app.get('/api/expanded/report')
def expanded_report():
    path=EXPANDED/'report.json'
    if not path.is_file(): raise HTTPException(503,'Expanded study data is not prepared.')
    return json.loads(path.read_text(encoding='utf-8'))

@app.get('/api/expanded/layers/{filename}')
def expanded_layer(filename:str):
    if filename not in {'observed.png','predicted.png','difference.png'}: raise HTTPException(404,'Unknown layer')
    path=EXPANDED/filename
    if not path.is_file(): raise HTTPException(503,'Expanded layer not prepared')
    return FileResponse(path,media_type='image/png')

@app.get('/api/expanded/pixel')
def expanded_pixel(lat:float,lon:float):
    return read_pixel(lat,lon,expanded_report(),EXPANDED/'display.npz',EXPANDED/'scene.npz')

web=ROOT/'web'/'dist'
if web.exists(): app.mount('/',StaticFiles(directory=web,html=True),name='web')
