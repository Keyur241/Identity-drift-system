import { useEffect, useState } from 'react';
import { getData } from './api';

export function usePoll(path, fallback, ms = 3000) {
  const [s, setS] = useState({ data: fallback, error: null });
  useEffect(() => {
    if (!path) return undefined;
    let live = true;
    const go = async () => { const r = await getData(path, fallback); if (live) setS((p) => ({ data: r.error ? p.data : r.data, error: r.error })); };
    go(); const t = setInterval(go, ms);
    return () => { live = false; clearInterval(t); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ms]);
  return s;
}
