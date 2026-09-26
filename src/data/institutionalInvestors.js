// Transcribed from the owner's screenshot supplied 26 September 2026.
// No valuation date, detailed share quantities or quarterly history was supplied.
const entries=labels=>labels.map(label=>({label}));
const row=(name,value,change,stocks,sectors,holdings,bought=[],sold=[])=>({name,value,change,stocks,sectors:entries(sectors),holdings:entries(holdings),bought:entries(bought),sold:entries(sold),quarterlyNetWorth:null});
export const indiaInstitutionalInvestors=[
 row('President of India',4058855.02,1.98,77,['Banking and Finance (48.52%)','General Industrials (14.69%)','Utilities (10.68%)'],['SBI (499,341.91 Cr)','Life Insurance Corp (499,337.38 Cr)','Hindustan Aeronautics (229,969.16 Cr)'],['HMT +93.68%','HUDCO +54.27%'],['Central Bank -8.08%','NHPC -6.01%','General Insurance -5.0%']),
 row('SBI Group',1172260.45,0.46,374,['Banking and Finance (39.17%)','Automobiles & Auto Components (6.71%)','Software & Services (5.38%)'],['SBI Life Insurance (98,545.47 Cr)','HDFC Bank (73,452.43 Cr)','ICICI Bank (73,308.34 Cr)'],['Vidhi Specialty Food +26.03%','ARCL Organics +9.96%','Gokaldas Exports +8.42%'],['Ganesha Ecosphere -2.91%','Stanley Lifestyles -2.74%','Happiest Minds -2.63%']),
 row('TATA Sons',1145202.19,0.39,17,['Software & Services (47.91%)','Banking and Finance (9.91%)','Automobiles & Auto Components (9.45%)'],['TCS (540,382.98 Cr)','Tata Capital (113,447.85 Cr)','Titan Company (90,382.77 Cr)'])
];
