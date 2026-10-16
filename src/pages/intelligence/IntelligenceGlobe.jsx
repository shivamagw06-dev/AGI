import { useEffect, useRef, useState } from 'react';
export default function IntelligenceGlobe({events,assets,onEvent,onCompany}) {
  const host=useRef(null),callbacks=useRef({onEvent,onCompany});callbacks.current={onEvent,onCompany};
  const [error,setError]=useState('');
  useEffect(()=>{
    let destroyed=false,globe,observer;
    Promise.all([import('globe.gl'),import('topojson-client'),import('world-atlas/countries-110m.json')]).then(([{default:Globe},{feature},{default:world}])=>{
      if(destroyed)return;
      globe=new Globe(host.current,{animateIn:false,rendererConfig:{antialias:true,alpha:true}})
        .width(host.current.clientWidth).height(480).backgroundColor('#0b202d')
        .showAtmosphere(true).atmosphereColor('#729bab').atmosphereAltitude(.13)
        .polygonsData(feature(world,world.objects.countries).features).polygonCapColor(()=>'#203e4c').polygonSideColor(()=>'#18303d').polygonStrokeColor(()=>'#53707a').polygonAltitude(.004)
        .pointsData([...events.map(e=>({...e,kind:'event'})),...assets.map(a=>({...a,kind:'asset'}))])
        .pointLat('latitude').pointLng('longitude').pointColor(d=>d.kind==='asset'?'#71e1c4':'#ffb76b').pointRadius(d=>d.kind==='asset'?.26:.35).pointAltitude(.015)
        .pointLabel(d=>{const el=document.createElement('div');el.style.cssText='background:#fff;color:#142c3a;padding:10px;border-radius:4px';el.textContent=d.kind==='event'?d.title:`${d.company} · ${d.name}`;return el;})
        .onPointClick(d=>d.kind==='event'?callbacks.current.onEvent(d.id):callbacks.current.onCompany(d.symbol));
      globe.globeMaterial().color.set('#0e2735');globe.pointOfView({lat:23,lng:77,altitude:2.2});
      globe.controls().autoRotate=false;globe.controls().enableZoom=true;
      observer=new ResizeObserver(()=>globe?.width(host.current?.clientWidth||600));observer.observe(host.current);
    }).catch(()=>{if(!destroyed)setError('The 3D view is unavailable on this device. All events and company records remain available in the list.');});
    return()=>{destroyed=true;observer?.disconnect();globe?._destructor();};
  },[events,assets]);
  return <div className="gi-map"><div ref={host} role="img" aria-label="Interactive globe of reported events and approximate company asset locations"/>{error&&<p role="status">{error}</p>}<div className="gi-map-key"><span>● Reported event</span><span>● Company area</span><small>Drag to rotate · scroll to zoom · select a marker</small></div></div>;
}
