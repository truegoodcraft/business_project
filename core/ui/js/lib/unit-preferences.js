/* Expose a simple helper to choose default display units based on settings */
import { DIM_DEFAULTS_METRIC, DIM_DEFAULTS_IMPERIAL } from './units.js';
export function preferredUnitForDimension(dimension){
  const american = !!(window.BUS_UNITS && window.BUS_UNITS.american);
  return (american ? DIM_DEFAULTS_IMPERIAL : DIM_DEFAULTS_METRIC)[dimension] || 'ea';
}
