/**
 * Compatibility entrypoint for the bundled live server.
 * The extracted parser also handles quoted YAML keys; keep one implementation.
 */
export { parseDesignMd, assessCoverage } from './lib/design-parser.mjs';
