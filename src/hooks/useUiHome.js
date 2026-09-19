import { useEffect, useState } from 'react';
import { getUiHome } from '@/lib/uiApi';

export default function useUiHome() {
  const [state, setState] = useState({ loading: true, data: null, error: null });

  useEffect(() => {
    let active = true;
    getUiHome()
      .then((data) => active && setState({ loading: false, data, error: null }))
      .catch((error) => active && setState({ loading: false, data: null, error }));
    return () => {
      active = false;
    };
  }, []);

  return state;
}
