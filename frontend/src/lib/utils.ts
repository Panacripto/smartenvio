export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("es-DO", { style: "currency", currency: "DOP" }).format(value);
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat("es-DO", { year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(date));
}

export function formatDateTime(date: string | Date): string {
  return new Intl.DateTimeFormat("es-DO", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(date));
}
