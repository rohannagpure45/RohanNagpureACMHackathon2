export function formatDuration(sec: number): string {
  const minutes = Math.floor(sec / 60);
  const seconds = Math.floor(sec % 60);
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

export function formatAngle(deg: number): string {
  return `${deg.toFixed(1)}\u00B0`;
}

export function getFatigueColor(score: number): string {
  if (score < 0.3) return '#4caf50';
  if (score < 0.6) return '#ff9800';
  return '#f44336';
}
