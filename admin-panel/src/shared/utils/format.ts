const dateFormatter = new Intl.DateTimeFormat('fa-IR', {
  year: 'numeric',
  month: 'long',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

const numberFormatter = new Intl.NumberFormat('fa-IR')

export function formatDate(value: string) {
  return dateFormatter.format(new Date(value))
}

export function formatNumber(value: number) {
  return numberFormatter.format(value)
}
