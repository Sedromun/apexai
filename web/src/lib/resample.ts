/**
 * Linear-interpolate values sampled along `srcDist` onto the `targetDist` grid.
 * Both distance arrays must be monotonically non-decreasing. Used to overlay a
 * reference lap (different sampling) on the current lap's distance axis.
 */
export function resampleByDistance(
  srcDist: number[],
  srcVals: number[],
  targetDist: number[],
): (number | null)[] {
  const n = srcDist.length;
  const out = new Array<number | null>(targetDist.length);
  if (n === 0) return out.fill(null);

  let i = 0;
  for (let k = 0; k < targetDist.length; k++) {
    const d = targetDist[k];
    if (d <= srcDist[0]) {
      out[k] = srcVals[0];
      continue;
    }
    if (d >= srcDist[n - 1]) {
      out[k] = srcVals[n - 1];
      continue;
    }
    while (i < n - 1 && srcDist[i + 1] < d) i++;
    const d0 = srcDist[i];
    const d1 = srcDist[i + 1];
    out[k] = d1 === d0 ? srcVals[i] : srcVals[i] + ((d - d0) / (d1 - d0)) * (srcVals[i + 1] - srcVals[i]);
  }
  return out;
}

/**
 * Overlay a reference lap onto the current lap aligned by LAP FRACTION rather than
 * absolute metres. Two laps of the same circuit can have slightly different measured
 * lengths and a different distance origin (the game's start/finish vs Racenet's timing
 * point) — e.g. a Zandvoort эталон reads 4199 m vs a captured 4256 m, a ~60 m skew that
 * smears every corner. Normalising each lap to [0,1] over its own start→finish makes the
 * corners line up. Both distance arrays must be monotonically non-decreasing.
 */
export function resampleByFraction(
  srcDist: number[],
  srcVals: number[],
  targetDist: number[],
): (number | null)[] {
  if (srcDist.length === 0 || targetDist.length === 0) {
    return new Array<number | null>(targetDist.length).fill(null);
  }
  const s0 = srcDist[0];
  const sSpan = srcDist[srcDist.length - 1] - s0 || 1;
  const t0 = targetDist[0];
  const tSpan = targetDist[targetDist.length - 1] - t0 || 1;
  const srcFrac = srcDist.map((d) => (d - s0) / sSpan);
  const targetFrac = targetDist.map((d) => (d - t0) / tSpan);
  return resampleByDistance(srcFrac, srcVals, targetFrac);
}
