/**
 * What a reader is asked for, and what is accepted back.
 *
 * The instruction matters more than the model. "Extract capex" produces one
 * number and loses two: Reliance states capital expenditure three times, under
 * three definitions, and a reader told to find capex picks whichever it saw
 * first. So the instruction is to find every distinct disclosed observation and
 * to reconcile nothing.
 *
 * Nothing is trusted on the way back. A fact is accepted only if its value
 * appears in the sentence it cites and that sentence appears in the document,
 * which is checkable without knowing anything about finance. A model that
 * invents ₹1,50,000 crore of capex cannot produce a sentence containing it.
 */
import { DEFINITIONS, ENTITY_SCOPE, MEASUREMENT, factKey } from './factOntology.js';

export const CONTRACT = [
  'You are reading one company filing and recording what it discloses.',
  '',
  'Extract every distinct disclosed observation of the concepts asked for.',
  '',
  'Rules, all of which are checked automatically:',
  '1. Do not reconcile. Do not choose a preferred figure. If the filing states',
  '   a concept twice under different definitions, emit two observations.',
  '2. Every value must appear in the sentence you cite, and that sentence must',
  '   appear verbatim in the filing. Do not paraphrase the sentence.',
  '3. Do not calculate. Record only figures the filing states. A total you',
  '   worked out from two disclosed components is not a disclosed observation.',
  '4. Keep the issuer\'s own words for the line in `as_reported_label`.',
  '5. Say which section the figure came from, and whether it is consolidated',
  '   or standalone, group or segment, cash or accrual.',
  '6. If a concept is not disclosed, emit nothing for it. An absent observation',
  '   is the correct answer and is more useful than an approximate one.',
  '',
  'Reply as JSON: {"facts": [...]} where each fact is',
  '{ "concept", "definition_id", "value", "period_end", "period_type",',
  '  "accounting_scope", "entity_scope", "measurement_basis", "segment",',
  '  "currency", "unit", "as_reported_label", "source_section", "source_sentence" }',
].join('\n');

/** The definitions a reader may use, described for the prompt. */
export function definitionsFor(concepts) {
  const wanted = new Set(concepts || []);
  const lines = [];
  for (const [id, entry] of DEFINITIONS) {
    if (wanted.size && !wanted.has(entry.concept)) continue;
    lines.push(`  ${id}  (${entry.concept}, ${entry.measurement}) - ${entry.label}`);
  }
  return lines.join('\n');
}

export function extractionPrompt({ concepts, text }) {
  return {
    system: CONTRACT,
    user: [
      `Concepts to look for: ${(concepts || []).join(', ')}`,
      '',
      'Definitions you may use. If a disclosure does not fit one of these,',
      'skip it rather than forcing it into the closest:',
      definitionsFor(concepts),
      '',
      'Filing:',
      text,
    ].join('\n'),
  };
}

/** Digits as a filing writes them, so 1,44,271 and 144271 compare equal. */
const bare = (text) => String(text ?? '').replace(/[,\s ]/g, '');

/**
 * Whether a sentence states a value.
 *
 * Compared as digits rather than as a number, because "1,22,916" appears in a
 * cash flow statement inside brackets and with a currency mark, and reading it
 * as a number first would mean deciding what the brackets meant.
 */
export function sentenceStates(sentence, value) {
  const digits = bare(sentence);
  const wanted = bare(value);
  if (!wanted) return false;
  if (digits.includes(wanted)) return true;
  // A filing writing 0.4 may be cited as 0.40, and 5,842 as 5842.0.
  const asNumber = Number(wanted);
  if (!Number.isFinite(asNumber)) return false;
  return digits.includes(String(asNumber));
}

const REQUIRED = ['concept', 'definition_id', 'value', 'period_end', 'currency',
  'unit', 'measurement_basis', 'as_reported_label', 'source_sentence'];

/**
 * Facts a reader returned, and the ones refused.
 *
 * Every refusal names the fact and the reason, because a reader that quietly
 * drops half its output looks the same as a filing that discloses half as much.
 */
export function readFacts({ payload, document, company, reportedInDocument }) {
  const text = bare(document || '');
  const facts = [];
  const rejected = [];
  const seen = new Map();

  for (const [at, raw] of (payload?.facts || []).entries()) {
    const where = `fact ${at + 1}`;
    const missing = REQUIRED.filter((name) => raw?.[name] === null
      || raw?.[name] === undefined || raw?.[name] === '');
    if (missing.length) { rejected.push({ where, reason: `missing ${missing.join(', ')}`, fact: raw }); continue; }

    const definition = DEFINITIONS.get(raw.definition_id);
    if (!definition) {
      rejected.push({ where, reason: `unknown definition ${raw.definition_id}`, fact: raw }); continue;
    }
    if (definition.concept !== raw.concept) {
      rejected.push({ where, reason: `${raw.definition_id} is a ${definition.concept}, not a ${raw.concept}`, fact: raw }); continue;
    }
    // The definition already says how it was measured. A reader disagreeing
    // with it has misunderstood one of the two.
    if (definition.measurement !== raw.measurement_basis) {
      rejected.push({ where, reason: `${raw.definition_id} is measured ${definition.measurement}, not ${raw.measurement_basis}`, fact: raw }); continue;
    }
    if (!Object.values(MEASUREMENT).includes(raw.measurement_basis)) {
      rejected.push({ where, reason: `unknown measurement basis ${raw.measurement_basis}`, fact: raw }); continue;
    }
    if (raw.entity_scope && !Object.values(ENTITY_SCOPE).includes(raw.entity_scope)) {
      rejected.push({ where, reason: `unknown entity scope ${raw.entity_scope}`, fact: raw }); continue;
    }
    if (!sentenceStates(raw.source_sentence, raw.value)) {
      rejected.push({ where, reason: `the cited sentence does not state ${raw.value}`, fact: raw }); continue;
    }
    if (text && !text.includes(bare(raw.source_sentence))) {
      rejected.push({ where, reason: 'the cited sentence is not in the filing', fact: raw }); continue;
    }

    const fact = {
      company,
      period_end: raw.period_end,
      period_type: raw.period_type || 'annual',
      concept: raw.concept,
      definition_id: raw.definition_id,
      accounting_scope: raw.accounting_scope || 'consolidated',
      entity_scope: raw.entity_scope || ENTITY_SCOPE.GROUP,
      measurement_basis: raw.measurement_basis,
      segment: raw.segment || null,
      geography: raw.geography || null,
      dimensions: raw.dimensions || {},
      currency: raw.currency,
      unit: Number(raw.unit),
      reported_in_document: reportedInDocument,
      original_or_restated: raw.original_or_restated || 'original',
      value: Number(raw.value),
      verdict: 'stated',
      as_reported_label: raw.as_reported_label,
      source_section: raw.source_section || null,
      source_sentence: raw.source_sentence,
    };

    // The same definition twice with different values is the contract broken:
    // either the reader reconciled two disclosures into one definition, or it
    // read one twice. Neither is safe to store, and picking one would be the
    // overwrite this store exists to prevent.
    const key = factKey(fact);
    const held = seen.get(key);
    if (held && held.value !== fact.value) {
      rejected.push({ where, reason: `${raw.definition_id} was already recorded as ${held.value}`, fact: raw });
      continue;
    }
    if (held) continue;
    seen.set(key, fact);
    facts.push(fact);
  }
  return { facts, rejected };
}
