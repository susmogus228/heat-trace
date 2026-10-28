import {test} from 'node:test';
import assert from 'node:assert/strict';
import {pointInBounds, normalizePoint, missingMessage} from '../src/selection.mjs';

test('selection is normalized once for form, marker and request',()=>{
 assert.deepEqual(normalizePoint({lat:30.5687514,lng:114.2512494}),{lat:30.568751,lng:114.251249});
});
test('invalid or outside points are not treated as valid coverage',()=>{
 const b=[114.15,30.42,114.5,30.72];
 assert.equal(pointInBounds({lat:75,lng:114.25},b),false);
 assert.equal(pointInBounds({lat:NaN,lng:114.25},b),false);
 assert.equal(pointInBounds({lat:30.57,lng:114.25},b),true);
});
test('missing value guidance distinguishes water, cloud and fallback',()=>{
 assert.match(missingMessage('water'),/water/i);
 assert.match(missingMessage('cloud'),/cloud/i);
 assert.match(missingMessage('other'),/another/i);
});
