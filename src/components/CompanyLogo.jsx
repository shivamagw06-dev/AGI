import {useState} from 'react';
import logos from '@/data/indiaCompanyLogos.json';
export default function CompanyLogo({symbol,name,size=36}) {
 const [failed,setFailed]=useState('');const logo=logos[symbol];
 return <span className="company-logo" style={{width:size,height:size}} title={name||symbol}>{logo&&failed!==symbol?<img src={logo.src} alt="" loading="lazy" width={size} height={size} onError={()=>setFailed(symbol)}/>:<span aria-hidden="true">{(symbol||name||'?').slice(0,2)}</span>}</span>;
}
export function HoldingLogos({holdings=[],limit=5}) {return <div className="holding-logos">{holdings.slice(0,limit).map(h=><CompanyLogo key={h.symbol} symbol={h.symbol} name={h.name}/>)}{holdings.length>limit&&<span className="holding-more">+{holdings.length-limit}</span>}</div>;}
