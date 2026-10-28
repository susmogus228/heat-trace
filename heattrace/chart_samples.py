"""Build reproducible chart samples from the frozen model and held-out grids."""
from pathlib import Path
import json
import joblib
import numpy as np
from heattrace.acquire import SCENES
from heattrace.model import load, split_masks

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'data' / 'output'


def build_chart_samples(limit=240):
    model=joblib.load(OUTPUT/'model.joblib')
    datasets={s:load(s) for s in SCENES}
    definitions={
        'spatial_holdout':(SCENES[:3], 'test'),
        'temporal_holdout':(SCENES[3:], 'train'),
        'spatiotemporal_holdout':(SCENES[3:], 'test'),
    }
    result={}
    for scope,(scene_ids,region) in definitions.items():
        candidates=[]
        for scene in scene_ids:
            x,y,valid=datasets[scene]; train,test=split_masks(valid)
            coords=np.argwhere(train if region=='train' else test)
            candidates.extend((scene,int(row),int(col)) for row,col in coords)
        chosen=np.random.default_rng(42).choice(len(candidates),size=min(limit,len(candidates)),replace=False)
        selected=[candidates[i] for i in chosen]
        inputs=np.array([datasets[s][0][row,col] for s,row,col in selected])
        predictions=model.predict(inputs)
        points=[]
        for (scene,row,col), pred in zip(selected,predictions):
            x,y,_=datasets[scene]
            points.append({'scene':scene,'row':row,'column':col,'ndvi':round(float(x[row,col,3]),4),
                           'observed':round(float(y[row,col]),2),'predicted':round(float(pred),2)})
        result[scope]={'population':len(candidates),'points':points}
    return result


def main():
    data=build_chart_samples()
    report=json.loads((OUTPUT/'report.json').read_text(encoding='utf-8'))
    for scope,group in data.items():
        if group['population']!=report['results'][scope]['model']['count']:
            raise ValueError(f'Frozen report count mismatch for {scope}')
    (OUTPUT/'chart_samples.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print('Prepared sample for each holdout without retraining the model.')


if __name__=='__main__': main()
