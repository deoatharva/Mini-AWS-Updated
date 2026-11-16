export function getReturnPath(location, fallback = '/') {
  const from = location?.state?.from;

  if (!from?.pathname) {
    return fallback;
  }

  return `${from.pathname}${from.search || ''}${from.hash || ''}`;
}
