

export const intToRgb = (i) => ([(i >> 16) & 0xFF, (i >> 8) & 0xFF, i & 0xFF])
export const rgbToCss = (r, g, b) => `rgb(${r}, ${g}, ${b})`

export const HSVtoRGB = (h, s, v) => {
  var r, g, b, i, f, p, q, t
  i = Math.floor(h * 6)
  f = h * 6 - i
  p = v * (1 - s)
  q = v * (1 - f * s)
  t = v * (1 - (1 - f) * s)
  switch (i % 6) {
  case 0: r = v, g = t, b = p; break
  case 1: r = q, g = v, b = p; break
  case 2: r = p, g = v, b = t; break
  case 3: r = p, g = q, b = v; break
  case 4: r = t, g = p, b = v; break
  case 5: r = v, g = p, b = q; break
  }
  return [r, g, b]
}

export function hashString(s) {
  return cyrb53(s)
}

const cyrb53 = function(str, seed = 0) {
  let h1 = 0xdeadbeef ^ seed, h2 = 0x41c6ce57 ^ seed
  for (let i = 0, ch; i < str.length; i++) {
    ch = str.charCodeAt(i)
    h1 = Math.imul(h1 ^ ch, 2654435761)
    h2 = Math.imul(h2 ^ ch, 1597334677)
  }
  h1 = Math.imul(h1 ^ (h1>>>16), 2246822507) ^ Math.imul(h2 ^ (h2>>>13), 3266489909)
  h2 = Math.imul(h2 ^ (h2>>>16), 2246822507) ^ Math.imul(h1 ^ (h1>>>13), 3266489909)
  return 4294967296 * (2097151 & h2) + (h1>>>0)
}


export function timeSince(dateInput) {
  // 59s, 59m, 23h, Jan 11 (2025), Sep 1 (2024), 2024 Jan 31 
  const now = new Date()
  const date = new Date(dateInput)
  const seconds = Math.floor((now - date) / 1000)

  if (seconds < 60) return seconds + "s ago"

  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return minutes + "m ago"

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return hours + "h ago"

  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

  let thresholdYear = now.getFullYear() - 1
  let thresholdMonth = now.getMonth() + 1
  const threshold = new Date(thresholdYear, thresholdMonth, 1)

  if (date >= threshold) {
    return months[date.getMonth()] + " " + date.getDate()
  }

  return date.getFullYear() + " " + months[date.getMonth()] + " " + date.getDate()
}
