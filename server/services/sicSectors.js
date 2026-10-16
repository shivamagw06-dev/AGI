/**
 * SIC codes to sectors.
 *
 * The map this replaces had eighteen ranges and no technology in it. SIC
 * 3000-3999 all became "Industrials", which put Apple (3571), Nvidia (3674)
 * and Microsoft's hardware peers in with truck manufacturers; 7000-7999 all
 * became "Consumer Discretionary", which did the same to every software
 * company, since packaged software is 7372. A rotation chart built on it
 * reported industrials as the largest sector in a book whose largest holdings
 * are technology.
 *
 * There is no official mapping from SIC to sectors. SIC is a public standard
 * published by the US government and used by EDGAR; the eleven-sector scheme
 * in common use is GICS, which belongs to MSCI and S&P and is not reproduced
 * here. The sector names below are ordinary English and the assignments are
 * ours, derived from the SIC definitions themselves. Where a code could
 * reasonably sit in two sectors the choice is noted rather than left implicit.
 *
 * Ranges are matched narrowest-first, not in file order. That is what lets a
 * broad division sit next to the exceptions carved out of it without the two
 * depending on which was written first - 3600-3699 is electrical equipment,
 * 3670-3679 within it is semiconductors, and the narrower range wins wherever
 * both apply. `noOverlappingPeers` proves no two ranges of equal width can
 * both match, which is the one way this scheme could still be ambiguous.
 */

/** @type {[number, number, string, string][]} from, to, sector, industry */
export const SECTOR_RANGES = [
  // Agriculture, forestry, fishing
  [100, 999, 'Consumer Staples', 'Agriculture & Fishing'],

  // Mining. Split by what is mined: fuels are energy, everything else is a
  // material.
  [1000, 1119, 'Materials', 'Metal Mining'],
  [1200, 1299, 'Energy', 'Coal'],
  [1300, 1399, 'Energy', 'Oil & Gas Extraction'],
  [1400, 1499, 'Materials', 'Nonmetallic Minerals'],

  // Construction
  [1500, 1799, 'Industrials', 'Construction & Engineering'],

  // Manufacturing, 20-39. The largest division and the one the old map
  // flattened hardest.
  [2000, 2141, 'Consumer Staples', 'Food, Beverage & Tobacco'],
  [2200, 2299, 'Consumer Discretionary', 'Textiles'],
  [2300, 2399, 'Consumer Discretionary', 'Apparel'],
  [2400, 2499, 'Materials', 'Lumber & Wood'],
  [2500, 2599, 'Consumer Discretionary', 'Furniture'],
  [2600, 2699, 'Materials', 'Paper & Packaging'],
  // Printing and publishing sits with media rather than with paper: the
  // product is the content, and the newspaper and book publishers here are the
  // same companies that appear under broadcasting.
  [2700, 2799, 'Communication Services', 'Publishing & Printing'],
  [2800, 2829, 'Materials', 'Industrial Chemicals'],
  // 2830-2836 is pharmaceutical preparations, in-vitro diagnostics and
  // biological products - the drug makers. The old map put all of 2800-2899
  // in health care, which swept industrial chemicals in with them.
  [2830, 2836, 'Health Care', 'Pharmaceuticals & Biotechnology'],
  [2840, 2844, 'Consumer Staples', 'Household & Personal Products'],
  [2850, 2899, 'Materials', 'Specialty Chemicals'],
  [2900, 2999, 'Energy', 'Petroleum Refining'],
  [3000, 3099, 'Materials', 'Rubber & Plastics'],
  [3100, 3199, 'Consumer Discretionary', 'Leather & Footwear'],
  [3200, 3299, 'Materials', 'Stone, Clay & Glass'],
  [3300, 3399, 'Materials', 'Primary Metals'],
  [3400, 3499, 'Industrials', 'Fabricated Metal'],
  [3500, 3599, 'Industrials', 'Industrial Machinery'],
  // Carved out of industrial machinery: 3570-3579 is computer and office
  // equipment, which is Apple's code.
  [3570, 3579, 'Information Technology', 'Computers & Office Equipment'],
  [3600, 3699, 'Industrials', 'Electrical Equipment'],
  [3650, 3652, 'Consumer Discretionary', 'Household Audio & Video'],
  [3660, 3669, 'Information Technology', 'Communications Equipment'],
  // 3674 is semiconductors. The single most consequential correction here.
  [3670, 3679, 'Information Technology', 'Semiconductors & Components'],
  [3680, 3689, 'Information Technology', 'Computer Hardware'],
  [3700, 3799, 'Industrials', 'Transportation Equipment'],
  [3710, 3716, 'Consumer Discretionary', 'Automobiles'],
  [3720, 3729, 'Industrials', 'Aerospace'],
  [3751, 3751, 'Consumer Discretionary', 'Motorcycles & Bicycles'],
  [3760, 3769, 'Industrials', 'Aerospace & Defence'],
  [3790, 3799, 'Consumer Discretionary', 'Recreational Vehicles'],
  [3800, 3899, 'Industrials', 'Instruments & Controls'],
  // Laboratory analytical instruments - Thermo Fisher is 3826 - are read as
  // health care, which is the market they serve.
  [3821, 3827, 'Health Care', 'Life Sciences Tools'],
  [3841, 3851, 'Health Care', 'Medical Devices'],
  [3860, 3873, 'Consumer Discretionary', 'Photographic & Watches'],
  [3900, 3999, 'Consumer Discretionary', 'Miscellaneous Manufacturing'],

  // Transportation, communications, utilities, 40-49.
  [4000, 4099, 'Industrials', 'Railroads'],
  [4100, 4199, 'Industrials', 'Passenger Transit'],
  [4200, 4299, 'Industrials', 'Trucking & Logistics'],
  [4400, 4499, 'Industrials', 'Marine Transport'],
  [4500, 4599, 'Industrials', 'Airlines'],
  // Pipelines carry hydrocarbons and trade with energy, not with railroads.
  [4600, 4699, 'Energy', 'Pipelines'],
  [4700, 4799, 'Industrials', 'Transportation Services'],
  [4800, 4899, 'Communication Services', 'Telecommunications & Media'],
  [4900, 4949, 'Utilities', 'Utilities'],
  // Sanitary services is waste management, which is an industrial service
  // rather than a regulated utility.
  [4950, 4999, 'Industrials', 'Waste & Environmental Services'],

  // Wholesale and retail, 50-59.
  [5000, 5099, 'Industrials', 'Wholesale Distribution'],
  [5100, 5199, 'Consumer Discretionary', 'Wholesale Trade'],
  [5140, 5149, 'Consumer Staples', 'Food Wholesale'],
  [5200, 5399, 'Consumer Discretionary', 'Retail'],
  [5400, 5499, 'Consumer Staples', 'Food Retail'],
  [5500, 5899, 'Consumer Discretionary', 'Retail & Restaurants'],
  [5900, 5999, 'Consumer Discretionary', 'Specialty Retail'],
  [5912, 5912, 'Consumer Staples', 'Drug Retail'],

  // Finance, insurance, real estate, 60-67.
  [6000, 6199, 'Financials', 'Banking & Credit'],
  [6200, 6299, 'Financials', 'Capital Markets'],
  [6300, 6411, 'Financials', 'Insurance'],
  [6500, 6599, 'Real Estate', 'Real Estate'],
  [6700, 6799, 'Financials', 'Holding & Investment Offices'],
  // 6798 is the REIT code, and REITs are the substance of the real estate
  // sector however their holding company is filed.
  [6798, 6798, 'Real Estate', 'REITs'],

  // Services, 70-89.
  [7000, 7099, 'Consumer Discretionary', 'Hotels & Lodging'],
  [7200, 7299, 'Consumer Discretionary', 'Personal Services'],
  [7300, 7399, 'Industrials', 'Business Services'],
  // 7370-7379 is computer programming, data processing and packaged software.
  // The old map read this range as consumer discretionary.
  [7370, 7379, 'Information Technology', 'Software & IT Services'],
  [7500, 7599, 'Consumer Discretionary', 'Automotive Services'],
  [7600, 7699, 'Consumer Discretionary', 'Repair Services'],
  [7800, 7849, 'Communication Services', 'Motion Pictures'],
  [7900, 7999, 'Consumer Discretionary', 'Leisure & Entertainment'],
  [8000, 8099, 'Health Care', 'Health Care Providers'],
  [8100, 8199, 'Industrials', 'Legal Services'],
  [8200, 8299, 'Consumer Discretionary', 'Education'],
  [8300, 8399, 'Health Care', 'Social Services'],
  [8400, 8499, 'Consumer Discretionary', 'Museums & Cultural'],
  [8600, 8699, 'Industrials', 'Membership Organisations'],
  [8700, 8799, 'Industrials', 'Professional & Technical Services'],
  // 8731 is commercial physical and biological research, and on EDGAR it is
  // predominantly biotechnology - a clinical-stage company with no product
  // files here rather than under 2836. Read as health care for that reason.
  [8731, 8731, 'Health Care', 'Biotechnology Research'],
  [8800, 8899, 'Industrials', 'Private Households'],

  // Public administration and the codes EDGAR uses for funds and shells.
  [9100, 9999, 'Financials', 'Government & Non-classifiable'],
];

export const UNCLASSIFIED = { sector: 'Unclassified', industry: 'Unclassified' };

/**
 * The sector and industry for a SIC code.
 *
 * Narrowest matching range wins, so the order of SECTOR_RANGES does not affect
 * the answer. A code outside every range, or absent entirely, is Unclassified -
 * never a nearest guess, since a wrong sector is worse than a missing one in
 * an aggregate that reports weights.
 */
export function classifySic(code, description) {
  const sic = Number(String(code ?? '').trim());
  // Finite, specifically. With NaN both of the range comparisons below are
  // false, so the `continue` never fires and an unparseable code would match
  // whichever range happens to be written first. Zero and negatives need no
  // guard of their own - they match no range and reach Unclassified anyway,
  // and a branch no test can distinguish is one nobody can trust.
  if (!Number.isFinite(sic)) return { ...UNCLASSIFIED, industry: description || 'Unclassified' };

  let best = null;
  for (const range of SECTOR_RANGES) {
    const [from, to] = range;
    if (sic < from || sic > to) continue;
    if (!best || (to - from) < (best[1] - best[0])) best = range;
  }
  if (!best) return { ...UNCLASSIFIED, industry: description || 'Unclassified' };
  // The filing's own description where EDGAR gives one: it is more specific
  // than our label and comes from the registrant.
  return { sector: best[2], industry: description || best[3] };
}

/**
 * Every pair of ranges that overlap without one containing the other, or that
 * overlap at equal width.
 *
 * Narrowest-match only resolves an overlap when one range is strictly narrower
 * than the other. Two ranges of the same width that both match, or a partial
 * overlap where neither contains the other, would make the answer depend on
 * file order - which is exactly the property this scheme claims not to have.
 * Exported so a test can assert the table has none.
 */
export function noOverlappingPeers(ranges = SECTOR_RANGES) {
  const bad = [];
  for (let i = 0; i < ranges.length; i += 1) {
    for (let j = i + 1; j < ranges.length; j += 1) {
      const [aFrom, aTo] = ranges[i];
      const [bFrom, bTo] = ranges[j];
      if (aTo < bFrom || bTo < aFrom) continue;
      const aContainsB = aFrom <= bFrom && bTo <= aTo;
      const bContainsA = bFrom <= aFrom && aTo <= bTo;
      if (!aContainsB && !bContainsA) { bad.push([ranges[i], ranges[j], 'partial overlap']); continue; }
      if ((aTo - aFrom) === (bTo - bFrom)) bad.push([ranges[i], ranges[j], 'equal width']);
    }
  }
  return bad;
}
