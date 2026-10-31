import { describe, expect, it } from 'vitest';
import { date, money, totals } from './utils';

describe('accounting display', () => {
  it('rounds tax half-up exactly like the backend', () => {
    expect(totals([{ quantity: 3, unit_price: '25.25' }], '13')).toEqual({
      subtotal: '75.75',
      tax: '9.85',
      total: '85.60',
    });
    expect(totals([{ quantity: 1, unit_price: '0.05' }], '10').tax).toBe('0.01');
  });
  it('keeps large monetary values precise', () => {
    expect(money('9999999999999999.99', 'USD')).toBe('USD 9,999,999,999,999,999.99');
  });
  it('handles an empty order without invented totals', () => {
    expect(totals([], 13).total).toBe('0.00');
  });
  it('formats timestamps consistently in UTC', () => {
    expect(date('2026-01-01T01:00:00Z')).toContain('2026');
    expect(date(null)).toBe('—');
  });
});
