/**
 * Compatibility entrypoint for the bundled live server.
 * The extracted validator uses the shared command vocabulary without changing
 * the event protocol or the insert-mode rules.
 */
export { VISUAL_ACTIONS, validateEvent } from './live/event-validation.mjs';
