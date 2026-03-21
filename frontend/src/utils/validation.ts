export const COLOMBIA_BOUNDS = {
  lat: { min: -4.0, max: 13.5 },
  lon: { min: -82.0, max: -66.0 },
} as const;

export const RADIUS_BOUNDS = {
  min: 1,
  max: 500,
} as const;

export function isValidLat(lat: number): boolean {
  return lat >= COLOMBIA_BOUNDS.lat.min && lat <= COLOMBIA_BOUNDS.lat.max;
}

export function isValidLon(lon: number): boolean {
  return lon >= COLOMBIA_BOUNDS.lon.min && lon <= COLOMBIA_BOUNDS.lon.max;
}

export function isValidRadius(radius: number): boolean {
  return radius >= RADIUS_BOUNDS.min && radius <= RADIUS_BOUNDS.max;
}

export function isValidSearchParams(lat: number, lon: number, radius: number): boolean {
  return isValidLat(lat) && isValidLon(lon) && isValidRadius(radius);
}
