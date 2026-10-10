import { useEffect, useId, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import usePhone from './usePhone';
export default function MobileFilters({children, title='Filter & sort'}) {
  const phone=usePhone(), [open,setOpen]=useState(false), ref=useRef(null), id=useId();
  useEffect(()=>{if(!phone||!ref.current)return;if(open)ref.current.showModal();else ref.current.close();},[phone,open]);
  if(!phone)return <>{children}</>;
  return <><button type="button" className="mobile-filter-button" aria-haspopup="dialog" onClick={()=>setOpen(true)}>{title} <span aria-hidden="true">☷</span></button>{createPortal(<dialog ref={ref} className="mobile-filter-sheet" aria-labelledby={id} onCancel={()=>setOpen(false)} onClose={()=>setOpen(false)}><header><h2 id={id}>{title}</h2><button type="button" aria-label="Close filters" onClick={()=>setOpen(false)}>×</button></header><div className="mobile-filter-content">{children}</div><button type="button" className="mobile-filter-done" onClick={()=>setOpen(false)}>Show results</button></dialog>,document.body)}</>;
}
