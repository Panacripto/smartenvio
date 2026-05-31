const KEY = "app-theme";
const RATES_KEY = "app-show-rates";

export type Theme = "green" | "blue" | "orange" | "red";

export function getTheme(): Theme {
  return (localStorage.getItem(KEY) as Theme) || "green";
}

export function setTheme(t: Theme) {
  localStorage.setItem(KEY, t);
  document.documentElement.setAttribute("data-theme", t);
}

export function initTheme() {
  setTheme(getTheme());
}

export function getShowRates(): boolean {
  return localStorage.getItem(RATES_KEY) !== "false";
}

export function setShowRates(v: boolean) {
  localStorage.setItem(RATES_KEY, String(v));
}
