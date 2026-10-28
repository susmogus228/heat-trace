export function normalizePoint(point) {
 return {lat:Number(Number(point.lat).toFixed(6)),lng:Number(Number(point.lng).toFixed(6))};
}
export function pointInBounds(point,[west,south,east,north]) {
 return Number.isFinite(point.lat)&&Number.isFinite(point.lng)&&point.lng>=west&&point.lng<east&&point.lat>south&&point.lat<=north;
}
export function missingMessage(reason) {
 const explanations={water:'The satellite quality data marks this pixel as water, which is excluded from this land-surface study.',cloud:'The satellite quality data marks this pixel as cloudy or close to a cloud.',shadow:'The satellite quality data marks this pixel as cloud shadow.',snow:'The satellite quality data marks this pixel as snow or ice.',missing:'The satellite did not provide a usable value for this pixel.',other:'This pixel has no usable satellite value.'};
 return `${explanations[reason]||explanations.other} Choose another coloured pixel on the map.`;
}
