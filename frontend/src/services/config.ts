/**
 * Base URL for the FastAPI backend. Sourced from Vite's environment
 * variables so the frontend never hardcodes a backend host — this makes
 * the same build work across local dev, Docker Compose, and any future
 * deployment target.
 */
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
