import { tradingCalendar } from './tradingCalendarService.js';

export function indiaTradingDayAfterClose(now=new Date()) {
  const parts=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Kolkata',weekday:'short',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(now).filter((part)=>part.type!=='literal').map((part)=>[part.type,part.value]));
  const date=`${parts.year}-${parts.month}-${parts.day}`;
  if(parts.weekday==='Sat'||parts.weekday==='Sun'||!tradingCalendar.isTradingDay(date,'NSE')||Number(parts.hour)*60+Number(parts.minute)<15*60+40)return null;
  return date;
}
