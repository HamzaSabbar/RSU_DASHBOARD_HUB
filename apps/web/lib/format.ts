const nbsp = "\u00A0";

function replaceDecimalSeparator(s: string): string {
  return s.replace(".", ",");
}

export function formatBigNumber(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) {
    return `${replaceDecimalSeparator((value / 1_000_000).toFixed(2))}${nbsp}M`;
  }
  if (abs >= 1_000) {
    return `${replaceDecimalSeparator((value / 1_000).toFixed(0))}${nbsp}k`;
  }
  return value.toString();
}

export function formatInteger(value: number): string {
  return value.toLocaleString("fr-FR").replaceAll(",", nbsp);
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "";
  const sign = value > 0 ? "+" : "";
  return `${sign}${replaceDecimalSeparator(value.toFixed(1))}%`;
}

export function formatPeriodLabel(isoDate: string): string {
  return formatMonth(isoDate.slice(0, 7));
}

export function formatMonth(ym: string): string {
  const [year, month] = ym.split("-");
  if (!year || !month) return ym;
  const names = [
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
  ];
  const idx = Number(month) - 1;
  const label = names[idx] ?? month;
  return `${label} ${year}`;
}
