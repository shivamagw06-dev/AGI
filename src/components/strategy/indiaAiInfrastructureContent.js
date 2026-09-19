/**
 * The India AI Infrastructure strategy: the portfolio owner's basket, the
 * ratings and statuses they assign, and their reading of it.
 *
 * Editorial columns (layer, AI materiality rating, key evidence, status) are
 * the owner's judgments, with each evidence line checked against the
 * company's own documents in AGI's record. Every financial column on the page
 * is AGI arithmetic on filed results and AGI's market value; no broker or
 * consensus figure is used, so none appears here.
 */

export const STRATEGY_ASOF = '2026-09-19';

export const STRATEGY_FACTORS = [
  'direct AI revenue', 'AI order book', 'contracted capacity', 'customer quality', 'earnings growth', 'FCF',
  'capex intensity', 'ROIC/ROCE potential', 'valuation', 'execution visibility', 'expectation load',
];

// rating: the owner's AI materiality rating. status: the basket status.
//
// Which rows form the basket is not set here: the page places a row in the
// basket only if it passes AGI's materiality test (Material, or Material on
// AGI estimate), and on the watch list otherwise, so a status can never
// contradict the test. Status vocabulary: Core for a pass on filed figures,
// Emerging Core for a pass on AGI's estimate, with the owner's qualifiers
// (Execution, High Risk) kept. Watch-list rows carry the status they would
// take on passing.
export const STRATEGY_ROWS = [
  { symbol: 'NETWEB', name: 'Netweb Technologies', layer: 'AI compute', rating: 'Very High', evidence: 'AI about 62% of Q1 revenue; AI "maybe" 40–45% of the order book', status: 'Core' },
  { symbol: 'STLTECH', name: 'Sterlite Technologies', layer: 'Optical connectivity', rating: 'Very High', evidence: '$1.11 bn (₹10,000+ cr) hyperscaler AI data-centre award, FY27–FY29', status: 'Core' },
  { symbol: 'BLUESTARCO', name: 'Blue Star', layer: 'DC MEP / cooling', rating: 'High', evidence: 'About ₹1,000 cr DC MEP revenue a year; DC MEP order book about ₹1,500 cr at any given point', status: 'Core' },
  { symbol: 'LT', name: 'Larsen & Toubro', layer: 'AI factory / EPC / cloud', rating: 'High', evidence: '10,000-GPU NVIDIA B300 AI factory for Together AI (L&T\'s "Mega" band, ₹10,000–15,000 cr)', status: 'Core' },
  { symbol: 'BHARTIARTL', name: 'Bharti Airtel', layer: 'Nxtra DC', rating: 'High', evidence: 'Nxtra FY26 revenue ₹2,434 cr; about 300 MW (annual report: about 250 MW), targeting 1 GW; valued about $3.1 bn in the March 2026 funding', status: 'Core' },
  { symbol: 'ANANTRAJ', name: 'Anant Raj', layer: 'DC / cloud', rating: 'High', evidence: 'DC turnover ₹145.9 cr in FY26 (9% of turnover); roadmap to 357 MW', status: 'Core / Execution' },
  { symbol: 'ABB', name: 'ABB India', layer: 'Switchgear / electrical', rating: 'High', evidence: 'Direct DC switchgear and RMU orders; DC "almost 15% to 17%" of Q2 orders (analyst call, filed 7 Aug 2026)', status: 'Core' },
  { symbol: 'SCHNEIDER', name: 'Schneider Electric Infrastructure', layer: 'Switchgear / electrical', rating: 'Medium-High', evidence: 'Data centres and semiconductors together more than a fifth of the ₹2,169 cr order bank', status: 'Core' },
  { symbol: 'CUMMINSIND', name: 'Cummins India', layer: 'Backup power', rating: 'High', evidence: 'DC 30–35% of domestic power-generation revenue in FY26; 40% in Q1 FY27', status: 'Core' },
  { symbol: 'CRAFTSMAN', name: 'Craftsman Automation', layer: 'DC engine components', rating: 'Medium', evidence: 'German foundry: 90% of revenue is power-generation engine parts, a majority for data centres (at least ₹71 cr in H1 FY26)', status: 'Emerging Core' },
  { symbol: 'HFCL', name: 'HFCL', layer: 'AI/DC connectivity', rating: 'High', evidence: '₹495.8 cr DC export order; ₹215 cr DC connectivity plant approved', status: 'Core' },
  { symbol: 'DIACABS', name: 'Diamond Power Infrastructure', layer: 'DC cabling', rating: 'Medium-High', evidence: '₹435 cr DC order book (11.8% of ₹3,688 cr); letter of intent for a Hyderabad DC campus', status: 'Core' },
  { symbol: 'CLEANMAX', name: 'CleanMax', layer: 'DC renewable power', rating: 'Very High', evidence: 'Data & AI is 42% of contracted capacity, over 2.5 GW: 0.63 GW serves Indian DC load, 1.87 GW are emission-offset deals', status: 'Core / High Risk' },
  { symbol: 'CGPOWER', name: 'CG Power and Industrial Solutions', layer: 'Semiconductor packaging (OSAT)', rating: 'Medium', evidence: '₹502.77 cr FY26 semiconductor segment revenue (audited); OSAT at 0.5 m units a day, G2 to take it to 14.5 m', status: 'Core' },
  { symbol: 'SANSERA', name: 'Sansera Engineering', layer: 'Semiconductor-equipment parts', rating: 'Medium', evidence: 'About ₹1,250 cr semiconductor-equipment order over five years; regular production begun', status: 'Core' },
  { symbol: 'MTARTECH', name: 'MTAR Technologies', layer: 'AI/DC assemblies', rating: 'Medium-High', evidence: 'About ₹81 cr of DC orders (SLB and one other); potential scale-up', status: 'Emerging Core' },

  // Watch list today: each fails the materiality test, for the reason shown on the page.
  { symbol: 'RELIANCE', name: 'Reliance Industries', layer: 'AI DC / power / network', rating: 'Medium-High', evidence: '168 MW AI data centre for Meta, due within two years', status: 'Core' },
  { symbol: 'ADANIENT', name: 'Adani Enterprises', layer: 'AdaniConneX', rating: 'High', evidence: '65.4 MW operating against 960+ MW tied up', status: 'Core / Execution' },
  { symbol: 'POWERINDIA', name: 'Hitachi Energy India', layer: 'Transformers / grid', rating: 'High', evidence: '₹32,222 cr backlog; data centres named the major segment contributor', status: 'Core' },
  { symbol: 'GVT&D', name: 'GE Vernova T&D India', layer: 'Transformers / grid', rating: 'Medium-High', evidence: '₹20,930 cr backlog; 220 kV GIS bays commissioned for NTT Data Center', status: 'Core' },
  { symbol: 'POLYCAB', name: 'Polycab India', layer: 'DC cabling', rating: 'Medium-High', evidence: 'Management estimates about ₹3.5 cr of cable content per MW', status: 'Core' },
  { symbol: 'TATAPOWER', name: 'Tata Power', layer: 'Power / grid / storage', rating: 'Medium', evidence: 'One 25-year renewable power agreement for Princeton Digital Group\'s Mumbai DC; grid, FDRE and storage are not DC evidence', status: 'Threshold Exception' },
  { symbol: 'KEC', name: 'KEC International', layer: 'Transmission', rating: 'Medium', evidence: 'First transmission-line order to evacuate power to a data centre; value not split out of a ₹1,180 cr batch', status: 'Core / Optionality', member: false, watchReason: 'Held candidate: no value disclosed for any data-centre order' },
  { symbol: 'NTPCGREEN', name: 'NTPC Green Energy', layer: 'RTC DC power', rating: 'Medium-High', evidence: 'MoUs with Nxtra (up to 500 MW) and CtrlS (up to 2 GW); not yet power purchase agreements', status: 'Emerging Core', member: false, watchReason: 'Held candidate: memoranda of understanding, not contracted capacity' },
];

// Filed figures for basket names that are not index members, so AGI's
// member data does not carry them. Filled from the companies' own results.
export const NON_MEMBER_FILED = {
  // Audited FY26 consolidated results (16 May 2026) and Q1 FY27 results (10 Aug 2026), kecrpg.com.
  // Capex is one combined line (PPE and intangibles, net of CWIP and capital advances).
  KEC: {
    revenueFY26: 23505.54, patFY26: 605.59, cfoFY26: -414.13, capexFY26: 328.68, capexIntangiblesFY26: 0,
    revenueQ1FY27: 5023.54, revenueQ1FY26: 5022.88,
  },
  // Audited FY26 consolidated results and Q1 FY27 results, ngel.in. The PDFs are scans:
  // each figure was read against the page image, not only the OCR text.
  NTPCGREEN: {
    revenueFY26: 2858.42, patFY26: 522.6, cfoFY26: 2386.2, capexFY26: 15264.46, capexIntangiblesFY26: 1.38,
    revenueQ1FY27: 1106.86, revenueQ1FY26: 680.21,
  },
};

export const STRUCTURES = [
  {
    title: 'Direct AI earnings',
    names: ['NETWEB', 'STLTECH', 'BLUESTARCO', 'HFCL', 'CUMMINSIND'],
    text: 'Netweb, STL, Blue Star, HFCL and Cummins already have measurable AI/data-centre revenue or orders. These deserve the highest AI-evidence confidence.',
  },
  {
    title: 'Data-centre asset owners',
    names: ['BHARTIARTL', 'ANANTRAJ', 'LT'],
    text: 'Bharti/Nxtra, Anant Raj and L&T. For these, the most important variables are commissioned MW, contracted MW, billed MW, utilisation and revenue/EBITDA per MW. Nxtra\'s March 2026 funding round valued the business at around US$3.1 billion post-closing (Airtel release, 30 March 2026). Adani Enterprises (AdaniConneX) and Reliance belong here too, and sit on the watch list until they pass the materiality test.',
  },
  {
    title: 'Electrical picks-and-shovels',
    names: ['ABB', 'SCHNEIDER', 'DIACABS'],
    text: 'ABB, Schneider and Diamond Power. Their thesis depends primarily on converting India\'s DC capacity build-out into switchgear and cable orders rather than having "AI revenue" in the traditional sense. Hitachi, GE Vernova, KEC and Polycab share the thesis and wait on the watch list for a disclosed data-centre figure.',
  },
  {
    title: 'AI electricity',
    names: ['CLEANMAX'],
    text: 'CleanMax. Here contracted DC-linked GW, PPA economics, storage, incremental ROIC and FCF matter much more than headline earnings growth. Its named customers already include the hyperscalers and data-centre operators, though most of its Data & AI capacity is emission-offset deals rather than power delivered to data centres. NTPC Green and Tata Power are on the watch list.',
  },
  {
    title: 'Components and semiconductors',
    names: ['CGPOWER', 'SANSERA', 'MTARTECH', 'CRAFTSMAN'],
    text: 'CG Power, Sansera, MTAR and Craftsman. Packaging, precision parts and engine components whose AI/data-centre business is real but small against the whole company, so earnings momentum and the conversion of orders to revenue matter most.',
  },
];

export const OUTSIDE = [
  { name: 'Kaynes Technology', text: 'The semiconductor packaging ramp is real; AI/HPC economics still need customer and utilisation evidence.' },
  { name: 'Waaree Energies', text: 'BESS/DC optionality, but actual DC orders need to emerge: data centres are named only as target customers for its battery plant.' },
  { name: 'Adani Energy Solutions', text: 'Excellent DC-grid logic, but direct DC project economics need to become visible; management calls DC volume "very negligible" today.' },
  { name: 'Gujarat Fluorochemicals / Navin Fluorine', text: 'Semiconductor-material exposure exists, but revenue attribution is weak.' },
  { name: 'Power Grid', text: 'A very credible structural transmission beneficiary, but too diffuse to call AI earnings material today.' },
];

export const FIVE_METRICS = [
  ['AI Materiality', 'how much consolidated earnings AI can actually move.'],
  ['Evidence Confidence', 'disclosed / derived / AGI estimate.'],
  ['Capital Quality', 'ROIC, FCF and capex efficiency.'],
  ['Earnings Momentum', 'growth plus backlog and order conversion (revisions from filed figures; AGI has no consensus source).'],
  ['Expectation Load', 'how demanding today\'s valuation already is.'],
];
