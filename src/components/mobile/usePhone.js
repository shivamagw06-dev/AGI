import { useEffect, useState } from 'react';
export default function usePhone() {
  const [phone, setPhone] = useState(() => typeof window !== 'undefined' && window.matchMedia('(max-width: 700px)').matches);
  useEffect(() => {
    const media = window.matchMedia('(max-width: 700px)');
    const update = () => setPhone(media.matches);
    update(); media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  return phone;
}
