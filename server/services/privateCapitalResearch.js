import fs from 'node:fs';
const snapshot=JSON.parse(fs.readFileSync(new URL('../data/private-capital-watchlist.json',import.meta.url),'utf8'));
export function getPrivateCapitalResearch(){return snapshot;}
