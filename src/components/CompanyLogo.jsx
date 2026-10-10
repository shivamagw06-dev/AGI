import {useState} from 'react';
import logos from '@/data/indiaCompanyLogos.json';
import usLogos from '@/data/usCompanyLogos.json';
const usAssets=import.meta.glob('../assets/us-company-logos/*',{eager:true,query:'?url',import:'default'});
const assets=import.meta.glob('../assets/company-logos/*',{eager:true,query:'?url',import:'default'});
export default function CompanyLogo({symbol,name,size=36,market='india'}) {
 const [failed,setFailed]=useState('');const key=market==='usa'?(symbol||usLogos.names[name]):symbol;const logo=market==='usa'?usLogos.logos[key]:logos[key];const src=logo?(market==='usa'?usAssets[`../assets/us-company-logos/${logo.src}`]:assets[`../assets/company-logos/${logo.src.split('/').pop()}`]):null;
 return <span className="company-logo" style={{width:size,height:size}} title={name||symbol}>{src&&failed!==src?<img src={src} alt={`${name||symbol} logo`} loading="lazy" width={size} height={size} onError={()=>setFailed(src)}/>:<span aria-hidden="true">{(symbol||name||'?').slice(0,2)}</span>}</span>;
}
export function HoldingLogos({holdings=[],limit=5,market='india'}) {return <div className="holding-logos">{holdings.slice(0,limit).map(h=><CompanyLogo key={h.symbol||h.name} symbol={h.symbol} name={h.name} market={market}/>)}{holdings.length>limit&&<span className="holding-more">+{holdings.length-limit}</span>}</div>;}
