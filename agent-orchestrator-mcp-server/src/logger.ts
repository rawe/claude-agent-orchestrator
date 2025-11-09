/**
 * Simple file-based logger for debugging MCP server
 */

import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Create logs directory relative to the MCP server root
const LOG_DIR = path.join(__dirname, "..", "logs");
const LOG_FILE = path.join(LOG_DIR, "mcp-server.log");

// Ensure logs directory exists
function ensureLogDir() {
  if (!fs.existsSync(LOG_DIR)) {
    fs.mkdirSync(LOG_DIR, { recursive: true });
  }
}

/**
 * Log levels
 */
export enum LogLevel {
  DEBUG = "DEBUG",
  INFO = "INFO",
  WARN = "WARN",
  ERROR = "ERROR"
}

/**
 * Check if logging is enabled via environment variable
 */
function isLoggingEnabled(): boolean {
  return process.env.MCP_SERVER_DEBUG === "true";
}

/**
 * Write a log entry to the log file
 */
export function log(level: LogLevel, message: string, data?: any) {
  // Only log if debugging is enabled
  if (!isLoggingEnabled()) {
    return;
  }

  try {
    ensureLogDir();

    const timestamp = new Date().toISOString();
    const logEntry = {
      timestamp,
      level,
      message,
      ...(data && { data })
    };

    const logLine = JSON.stringify(logEntry) + "\n";

    fs.appendFileSync(LOG_FILE, logLine);
  } catch (error) {
    // If logging fails, write to stderr but don't crash
    console.error("Failed to write to log file:", error);
  }
}

/**
 * Convenience methods
 */
export const logger = {
  debug: (message: string, data?: any) => log(LogLevel.DEBUG, message, data),
  info: (message: string, data?: any) => log(LogLevel.INFO, message, data),
  warn: (message: string, data?: any) => log(LogLevel.WARN, message, data),
  error: (message: string, data?: any) => log(LogLevel.ERROR, message, data),
};

/**
 * Clear the log file (useful for testing)
 */
export function clearLog() {
  if (!isLoggingEnabled()) {
    return;
  }

  try {
    ensureLogDir();
    fs.writeFileSync(LOG_FILE, "");
  } catch (error) {
    console.error("Failed to clear log file:", error);
  }
}
