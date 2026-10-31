import Decimal from 'decimal.js';

export function money(value = 0, currency = 'CAD') {
  const [whole, fraction] = new Decimal(value).toFixed(2).split('.');
  return `${currency} ${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}.${fraction}`;
}
export function totals(items, taxRate = 0) {
  const subtotal = items
    .reduce(
      (sum, item) => sum.plus(new Decimal(item.unit_price || 0).times(item.quantity || 0)),
      new Decimal(0),
    )
    .toDecimalPlaces(2, Decimal.ROUND_HALF_UP);
  const tax = subtotal
    .times(taxRate || 0)
    .div(100)
    .toDecimalPlaces(2, Decimal.ROUND_HALF_UP);
  return {
    subtotal: subtotal.toFixed(2),
    tax: tax.toFixed(2),
    total: subtotal.plus(tax).toFixed(2),
  };
}
export function date(value) {
  return value
    ? new Intl.DateTimeFormat('en-CA', { dateStyle: 'medium', timeZone: 'UTC' }).format(
        new Date(value),
      )
    : '—';
}
export function label(value = '') {
  return value
    .toLowerCase()
    .replaceAll('_', ' ')
    .replace(/^./, (s) => s.toUpperCase());
}
export function initials(user) {
  return (
    (user.first_name?.[0] || user.email[0]).toUpperCase() +
    (user.last_name?.[0] || '').toUpperCase()
  );
}
