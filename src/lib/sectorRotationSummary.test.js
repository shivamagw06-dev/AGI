import test from 'node:test';
import assert from 'node:assert/strict';
import {sectorRotationSummary} from './sectorRotationSummary.js';
test('explains relative leadership without implying absolute gains',()=>{
 const text=sectorRotationSummary([{sector:'NIFTYMEDIA',relative_20d:6.31,relative_60d:12.63,return_20d:-.32},{sector:'NIFTYIT',relative_20d:-3.99,relative_60d:8.7}]);
 assert.match(text,/Media.*6.31 percentage points ahead/); assert.match(text,/still fell 0.32%/); assert.match(text,/Weakening: IT/);
});
test('does not turn missing inputs into leading sectors',()=>{assert.match(sectorRotationSummary([{sector:'TEST',relative_20d:null,relative_60d:1}]),/No complete/);});
test('all-negative readings remain behind and a new snapshot changes the summary',()=>{
 assert.match(sectorRotationSummary([{sector:'NIFTYIT',relative_20d:-2,relative_60d:-1}]),/2.00 percentage points behind/);
 assert.match(sectorRotationSummary([{sector:'NIFTYBANK',relative_20d:3,relative_60d:1}]),/Banking.*3.00 percentage points ahead/);
});
