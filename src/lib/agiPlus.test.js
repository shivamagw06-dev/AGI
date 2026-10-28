import test from 'node:test';
import assert from 'node:assert/strict';
import { isPlusToolPath, upiPaymentUri, plusReturnPath } from './agiPlus.js';
test('articles stay free while every existing tool route requires Plus',()=>{
 for(const path of ['/','/research','/equity-research','/article/msft','/category/india','/updates/earnings','/pricing','/subscribe','/account/subscription','/login','/terms','/admin/plus-payments'])assert.equal(isPlusToolPath(path),false,path);
 for(const path of ['/institutions','/institutions/in/example','/portfolios/india','/live-alpha','/tools','/tools/valuation','/markets','/market-intelligence','/strategy','/india-ai','/research/stocks/INFY','/institutional-holdings','/agi/company','/valuation-terminal','/sections/deal-tracker','/updates/pre-market'])assert.equal(isPlusToolPath(path),true,path);
});
test('checkout fixes the amount, currency and payee; redirects cannot escape the site',()=>{
 const config={checkoutEnabled:true,upiId:'8859819548@ptaxis',payeeName:'Shivam Agarwal'};
 const uri=new URL(upiPaymentUri(config));assert.equal(uri.protocol,'upi:');assert.equal(uri.searchParams.get('pa'),config.upiId);assert.equal(uri.searchParams.get('pn'),config.payeeName);assert.equal(uri.searchParams.get('am'),'199.00');assert.equal(uri.searchParams.get('cu'),'INR');assert.equal(upiPaymentUri({...config,checkoutEnabled:false}),null);assert.equal(plusReturnPath('//evil.test'),'/tools');assert.equal(plusReturnPath('/\\evil.test'),'/tools');assert.equal(plusReturnPath('/institutions?country=IN'),'/institutions?country=IN');
});
