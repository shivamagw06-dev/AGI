// Convert copied HTML tables to quoted TSV, preserving cell boundaries and safe links.
export function tableClipboard(html) {
 const doc=new DOMParser().parseFromString(html,'text/html');
 const table=doc.querySelector('table');if(!table)return null;
 function content(node){
  if(node.nodeType===3)return node.textContent;
  if(node.nodeType!==1)return '';
  if(['SCRIPT','STYLE','SVG','IMG'].includes(node.tagName.toUpperCase()))return '';
  if(node.tagName==='BR')return '\n';
  const text=[...node.childNodes].map(content).join('');
  if(node.tagName==='A'){
   try{const url=new URL(node.getAttribute('href'));if(url.protocol==='https:'&&!url.username)return `[${text.trim()}](${url.href})`;}catch{}
  }
  return ['DIV','P','LI'].includes(node.tagName)?`${text}\n`:text;
 }
 return [...table.rows].map(row=>[...row.cells].map(cell=>`"${content(cell).trim().replaceAll('"','""')}"`).join('\t')).join('\n');
}
