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
