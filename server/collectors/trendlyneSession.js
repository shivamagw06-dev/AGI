// Run interactively on a trusted workstation. No passwords are accepted by this script.
import {chromium} from 'playwright';
import {mkdir,writeFile} from 'node:fs/promises';
import {dirname,resolve} from 'node:path';
import {createInterface} from 'node:readline/promises';
const destination=process.env.TRENDLYNE_BROWSER_STATE_PATH;
if(!destination)throw Error('Set TRENDLYNE_BROWSER_STATE_PATH to a private file outside the web root');
const browser=await chromium.launch({headless:false});
const terminal=createInterface({input:process.stdin,output:process.stdout});
try {
 const context=await browser.newContext();const page=await context.newPage();
 await page.goto('https://trendlyne.com/');
 await terminal.question('Sign in directly in this dedicated browser, complete any OTP yourself, then press Enter here to save the session. ');
 const state=await context.storageState();
 state.cookies=state.cookies.filter(c=>['trendlyne.com','www.trendlyne.com','us.trendlyne.com'].includes(c.domain.replace(/^\./,'')));
 state.origins=state.origins.filter(o=>['trendlyne.com','www.trendlyne.com','us.trendlyne.com'].includes(new URL(o.origin).hostname));
 if(!state.cookies.length)throw Error('No Trendlyne session found; nothing saved');
 await mkdir(dirname(resolve(destination)),{recursive:true,mode:0o700});
 // Refuse accidental overwrite or symlink traversal; remove an expired file explicitly first.
 await writeFile(destination,JSON.stringify(state),{flag:'wx',mode:0o600});
 console.log('Session saved privately. Collection must still verify authenticated pages.');
}finally{terminal.close();await browser.close();}
