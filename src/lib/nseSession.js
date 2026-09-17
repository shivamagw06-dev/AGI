/**
 * NSE session state, from an absolute instant.
 *
 * One timezone path and no arithmetic. An earlier version of this carried
 *
 *   const ist = new Date(date.getTime() + (330 - -date.getTimezoneOffset()) * 0);
 *
 * which reads as a timezone conversion, is multiplied by zero, and did
 * nothing at all - the real conversion was happening in the Intl call two
 * lines below it. Manual offset arithmetic is the wrong tool regardless: it
 * has to know the host's offset, and it silently encodes an assumption about
 * where the process runs. `Intl.DateTimeFormat` with an explicit `timeZone`
 * converts an instant to IST the same way on every host.
 */

/** NSE continuous session, in IST minutes from midnight. */
export const OPEN_MINUTE = 9 * 60 + 15;    // 09:15
export const CLOSE_MINUTE = 15 * 60 + 30;  // 15:30
export const IST = 'Asia/Kolkata';

const FORMATTER = new Intl.DateTimeFormat('en-GB', {
  timeZone: IST, weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false,
});

/**
 * An instant, as IST wall-clock parts.
 *
 * Exported because the session test needs to prove the conversion itself is
 * host-independent, not only its boolean conclusion.
 */
export function istParts(date = new Date()) {
  const parts = FORMATTER.formatToParts(date);
  const at = (type) => parts.find((one) => one.type === type)?.value;
  const hour = Number(at('hour'));
  const minute = Number(at('minute'));
  return {
    weekday: at('weekday'),
    hour,
    minute,
    // 24:00 appears for midnight in some ICU versions; normalise so minute
    // arithmetic cannot land a day out.
    minuteOfDay: (hour % 24) * 60 + minute,
  };
}

/**
 * Whether the continuous session is on, by the clock alone.
 *
 * The clock only. Holidays are a separate question and the feed answers it:
 * on a trading holiday this returns true and no ticks arrive, which the page
 * already renders as "no ticks" rather than as an open market.
 *
 * There is deliberately no elapsed-fraction helper here. The server's
 * aiEnablersQuotes.sessionElapsedFraction already computes one, at second
 * rather than minute resolution, and a second implementation of the same
 * concept on the client is free to drift from it.
 */
export function nseOpen(date = new Date()) {
  const { weekday, minuteOfDay } = istParts(date);
  if (weekday === 'Sat' || weekday === 'Sun') return false;
  return minuteOfDay >= OPEN_MINUTE && minuteOfDay <= CLOSE_MINUTE;
}
