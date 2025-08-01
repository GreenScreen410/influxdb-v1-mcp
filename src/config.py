import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE_PATH = os.getenv("LOG_FILE", "logs/mcp_server.log")
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", 10 * 1024 * 1024))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", 5))

root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

log_file = Path(LOG_FILE_PATH)
log_file.parent.mkdir(parents=True, exist_ok=True)

file_handler = RotatingFileHandler(log_file, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 8086))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

MCP_MAX_POOL_SIZE = int(os.getenv("MCP_MAX_POOL_SIZE", 10))

if not all([DB_USER, DB_PASSWORD]):
    logger.error("Database credentials (DB_USER, DB_PASSWORD) not found in environment variables or .env file.")

logger.info(f"Logging to console and to file: {LOG_FILE_PATH} (Level: {LOG_LEVEL}, MaxSize: {LOG_MAX_BYTES}B, Backups: {LOG_BACKUP_COUNT})")
