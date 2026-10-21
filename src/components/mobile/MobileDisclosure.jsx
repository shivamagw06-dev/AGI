import usePhone from './usePhone';
/** Keeps the desktop content intact; mobile readers can open supporting detail. */
export default function MobileDisclosure({title, children, className = ''}) {
  const phone = usePhone();
  return phone ? <details className={`mobile-disclosure ${className}`}><summary>{title}</summary><div>{children}</div></details> : <>{children}</>;
}
