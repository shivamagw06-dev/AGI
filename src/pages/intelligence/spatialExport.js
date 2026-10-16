export function intelligenceGeoJSON(events,assets){
 return {type:'FeatureCollection',name:'AGI source observations and approximate company areas',features:[
  ...events.map(e=>({type:'Feature',geometry:{type:'Point',coordinates:[e.longitude,e.latitude]},properties:{layer:'source_event',id:e.id,title:e.title,category:e.category,observed_at:e.observed_at,source_url:e.source_url,limitation:'Reported point only; not an event footprint or operational-impact finding'}})),
  ...assets.map(a=>({type:'Feature',geometry:{type:'Point',coordinates:[a.longitude,a.latitude]},properties:{layer:'company_area',symbol:a.symbol,company:a.company,name:a.name,sector:a.sector,source_url:a.source_url,limitation:a.location_precision}})),
 ]};
}
export function downloadSpatialEvidence(events,assets){
 const blob=new Blob([JSON.stringify(intelligenceGeoJSON(events,assets),null,2)],{type:'application/geo+json'});
 const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='agi-intelligence.geojson';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
