# Reproducibility and results

## Source scenes

The experiment uses Landsat Collection 2 Level-2 surface-temperature scenes distributed by Microsoft Planetary Computer. Scene-level cloud percentages describe the entire scene, not the Wuhan crop.

| Scene | Date (UTC) | Scene cloud cover | Source | SHA-256 of prepared grid |
|---|---|---:|---|---|
| LC08_L2SP_123039_20230609_02_T1 | 2023-06-09 | 2.0% | [STAC item](https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2/items/LC08_L2SP_123039_20230609_02_T1) | `43303fe1f7d38d6c9afcbc1b03dcdbb7d2021116f7be96cec328099191916098` |
| LC09_L2SP_123039_20230804_02_T1 | 2023-08-04 | 6.5% | [STAC item](https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2/items/LC09_L2SP_123039_20230804_02_T1) | `6e5cdebf977a9d62242f15423da8cc2076e748d6cf034e8851f97e109eb181e1` |
| LC09_L2SP_123039_20240705_02_T1 | 2024-07-05 | 1.74% | [STAC item](https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2/items/LC09_L2SP_123039_20240705_02_T1) | `d25b8d9a50b319c1e87ab3f797d1297a053a10b1b1ad58a3ebb355cfb9722cdc` |
| LC09_L2SP_123039_20240721_02_T1 | 2024-07-21 | 0.38% | [STAC item](https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2/items/LC09_L2SP_123039_20240721_02_T1) | `680d07adbe2979c0b1e0002bbbdc943ad25d01664a5efaad863c2bc20575b7f5` |

## Test design

- Training: western 65% of columns for three scenes, 22,911 valid sampled pixels.
- Spatial holdout: eastern 25% for those training dates, 9,179 valid sampled pixels.
- Temporal holdout: western area on 2024-07-21, 8,649 valid sampled pixels.
- Spatial plus temporal holdout: eastern area on 2024-07-21, 3,636 valid sampled pixels.
- The middle 10% of columns is an unused spatial buffer.
- Charts show a deterministic random sample of up to 240 pixels from the selected holdout. The spatial holdout sample draws from all three training dates, while the other two samples use the held-out date. Chart samples can be regenerated with `python -m heattrace.chart_samples` without retraining the model.

This tests generalisation to one held-out area and date. It does not prove performance on other cities, sensors, seasons, or on ground thermometers. Nearby pixels remain correlated, and random forest performance should not be interpreted as proof of causality. The radiometric saturation QA band is not used.

## Metrics

| Split | Forest MAE (°C) | Linear MAE (°C) | Mean predictor MAE (°C) | Forest R² |
|---|---:|---:|---:|---:|
| New area | 2.1911 | 2.3242 | 3.5799 | 0.5791 |
| New date | 3.3888 | 3.4032 | 4.5815 | 0.2825 |
| New area + date | 4.2494 | 3.8833 | 4.9398 | 0.0027 |

The linear baseline is better on the most demanding split; this is an observed result, not a guarantee it will remain better on other data. The mean predictor is fitted on training targets only. See `README.md` for execution instructions.

## Separate expanded-area evaluation

The display region is [114.00, 30.30, 114.65, 30.84] (west, south, east, north) on the same held-out Landsat scene. Its 260 × 216 geographic grid maintains the original 0.0025° sampling step and spans approximately 3.34 times the original rectangle's geographic area. This sampling grid does not increase the thermal instrument's actual resolution.

The test excludes the original rectangle and a further 0.03° rectangular buffer. This limits overlap with the original training data but does not prove independence from all spatial correlation. It is one scene and one date, not a test on other cities or conditions.

- Valid pixels over the wider display: 46,317.
- Valid pixels in the new-area test: 27,174.
- Frozen random forest MAE: 2.2543 °C; RMSE: 2.8593 °C; R²: 0.6228.
- Linear baseline MAE: 1.8294 °C; mean baseline MAE: 3.9442 °C. Both baselines are reconstructed using only the original training samples.
- The lower error here compared with the old area is measured on a different test set and does not prove the model improved.
- Wider source: [LC09_L2SP_123039_20240721_02_T1](https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2/items/LC09_L2SP_123039_20240721_02_T1). Prepared scene SHA-256: `612e018299f00658bca28a008eda1a300db7794940326ef34564da916b2f92b5`.

The new map and report live separately under `data/expanded/`; the previous model and report are retained. The 240 chart points are a deterministic sample from the new-area test and do not replace population-wide metrics.
