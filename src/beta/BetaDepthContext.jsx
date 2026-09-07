import { createContext, useContext, useMemo, useState } from 'react';

/** Layer 1 = 30s explain, Layer 2 = research report, Layer 3 = professional */
export const DEPTH = {
  explain: 'explain',
  research: 'research',
  professional: 'professional',
};

const BetaDepthContext = createContext({
  depth: DEPTH.research,
  setDepth: () => {},
  isExplain: false,
  isResearch: true,
  isProfessional: false,
});

export function BetaDepthProvider({ children }) {
  const [depth, setDepth] = useState(DEPTH.research);
  const value = useMemo(
    () => ({
      depth,
      setDepth,
      isExplain: depth === DEPTH.explain,
      isResearch: depth === DEPTH.research || depth === DEPTH.professional,
      isProfessional: depth === DEPTH.professional,
    }),
    [depth],
  );
  return <BetaDepthContext.Provider value={value}>{children}</BetaDepthContext.Provider>;
}

export function useBetaDepth() {
  return useContext(BetaDepthContext);
}
