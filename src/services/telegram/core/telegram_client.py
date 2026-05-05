import json
import logging
import time
from typing import Dict, List, Optional, Tuple

import requests
from requests import HTTPError

from core.config import Config

logger = logging.getLogger(__name__)


class TelegramClient:
    """Handles Telegram API calls."""
    
    def __init__(self):
        self.request_timeout = getattr(self, "request_timeout", 20)
        self.offset = getattr(self, "offset", 0)
        self.chat_ids = getattr(self, "chat_ids", [])

    def _split_response(self, result, default_keyboard=None) -> Tuple[str, Optional[Dict]]:
        """Normalize action results into (text, keyboard)."""
        if isinstance(result, tuple):
            if len(result) != 2:
                return str(result), default_keyboard
            first, second = result
            if isinstance(first, dict) and not isinstance(second, dict):
                logger.warning("Action returned legacy (keyboard, text) order; normalizing")
                return str(second), first
            return str(first), second
        return str(result), default_keyboard

    def _sanitize_error(self, error: Exception) -> str:
        text = str(error)
        token = getattr(self, "token", None)
        if token:
            text = text.replace(str(token), "<telegram-token>")
        return text

    def _log_request_error(self, message: str, error: Exception):
        body = getattr(getattr(error, "response", None), "text", "")
        token = getattr(self, "token", None)
        if token and body:
            body = body.replace(str(token), "<telegram-token>")
        logger.error("%s: %s %s", message, self._sanitize_error(error), body[:300])
    
    def get_updates(self) -> List[Dict]:
        """Get updates from Telegram API."""
        try:
            response = requests.get(
                f"{self.base_url}/getUpdates",
                params={"offset": self.offset, "timeout": 25},
                timeout=max(self.request_timeout, 35)
            )
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                return data.get("result", [])
        except Exception as e:
            self._log_request_error("Failed to get updates", e)
        return []
    
    def send_message(self, text, reply_markup=None, chat_id=None):
        """Send message to Telegram chat."""
        target_chats = [chat_id] if chat_id else self.chat_ids
        
        for chat in target_chats:
            try:
                payload = {
                    "chat_id": chat,
                    "text": text,
                    "parse_mode": "Markdown",
                }
                if reply_markup:
                    payload["reply_markup"] = json.dumps(reply_markup)
                
                return self._post_telegram("sendMessage", payload)
            except Exception as e:
                self._log_request_error("Failed to send message", e)
        return None
    
    def edit_message(self, query, text, reply_markup=None):
        """Edit existing message."""
        try:
            payload = {
                "chat_id": query["message"]["chat"]["id"],
                "message_id": query["message"]["message_id"],
                "text": text,
                "parse_mode": "Markdown",
            }
            if reply_markup:
                payload["reply_markup"] = json.dumps(reply_markup)
            
            return self._post_telegram("editMessageText", payload)
        except Exception as e:
            self._log_request_error("Failed to edit message", e)
        return None

    def delete_message(self, query):
        """Delete the current Telegram message."""
        try:
            payload = {
                "chat_id": query["message"]["chat"]["id"],
                "message_id": query["message"]["message_id"],
            }
            return self._post_telegram("deleteMessage", payload)
        except Exception as e:
            self._log_request_error("Failed to delete message", e)
        return None

    def _post_telegram(self, method: str, payload: Dict):
        response = requests.post(
            f"{self.base_url}/{method}",
            json=payload,
            timeout=self.request_timeout
        )
        try:
            response.raise_for_status()
            return response.json()
        except HTTPError as exc:
            body = response.text or ""
            if "message is not modified" in body:
                logger.info("Telegram %s skipped: message is not modified", method)
                return None
            if "can't parse entities" in body and payload.get("parse_mode"):
                fallback = dict(payload)
                fallback.pop("parse_mode", None)
                retry = requests.post(
                    f"{self.base_url}/{method}",
                    json=fallback,
                    timeout=self.request_timeout
                )
                retry.raise_for_status()
                logger.warning("Telegram %s retried without Markdown parse mode", method)
                return retry.json()
            raise exc
    
    def handle_update(self, update: Dict):
        """Handle incoming update."""
        if "message" in update:
            self.handle_message(update["message"])
        elif "callback_query" in update:
            self.handle_callback(update["callback_query"])
    
    def handle_message(self, message: Dict):
        """Handle incoming message."""
        text = message.get("text", "")
        chat_id = str(message.get("chat", {}).get("id", ""))
        
        if not any(cid == chat_id for cid in self.chat_ids):
            logger.warning(f"Unauthorized access from {chat_id}")
            return
        
        # Handle commands
        if text.startswith("/"):
            self.handle_command(text, chat_id)
        else:
            self.handle_text(text, chat_id)
    
    def handle_command(self, command: str, chat_id: str):
        """Handle Telegram command."""
        if command.startswith("/start"):
            text, reply_markup = self._split_response(
                self.handle_action("menu"),
                default_keyboard=self.keyboard(),
            )
            self.send_message(
                text,
                reply_markup=reply_markup,
                chat_id=chat_id
            )
        elif command.startswith("/status"):
            text, reply_markup = self._split_response(
                self.handle_action("status"),
                default_keyboard=self.keyboard_for_action("status"),
            )
            self.send_message(
                text,
                reply_markup=reply_markup,
                chat_id=chat_id
            )
        elif command.startswith("/help"):
            text, reply_markup = self._split_response(
                self.handle_action("help"),
                default_keyboard=self.keyboard_for_action("help"),
            )
            self.send_message(
                text,
                reply_markup=reply_markup,
                chat_id=chat_id
            )
        elif command.startswith("/scan"):
            self.send_message(
                self.handle_scan_message(command),
                reply_markup=self.keyboard_for_action("scan_wallet"),
                chat_id=chat_id,
            )
        elif command.startswith("/newwallet") or command.startswith("/wallet_new"):
            text, reply_markup = self._split_response(
                self.handle_action("wallet_create_prompt"),
                default_keyboard=self.wallet_create_confirm_keyboard(),
            )
            self.send_message(text, reply_markup=reply_markup, chat_id=chat_id)
        elif command.startswith("/mirror") or command.startswith("/smartcopy"):
            self.handle_text(command, chat_id)
    
    def handle_callback(self, callback_query: Dict):
        """Handle callback query."""
        action = callback_query.get("data", "")
        chat_id = str(callback_query["message"]["chat"]["id"])
        
        if not any(cid == chat_id for cid in self.chat_ids):
            logger.warning(f"Unauthorized callback from {chat_id}")
            return
        
        # Answer callback
        try:
            requests.post(
                f"{self.base_url}/answerCallbackQuery",
                json={"callback_query_id": callback_query["id"]},
                timeout=5
            )
        except Exception:
            pass
        
        # Process action
        logger.info("Handling callback action: %s", action)
        if action == "close_menu":
            self.delete_message(callback_query)
            return

        result = self.handle_action(action)
        
        # Edit message if it's a callback
        text, reply_markup = self._split_response(
            result,
            default_keyboard=self.keyboard_for_action(action),
        )
        
        self.edit_message(callback_query, text=text, reply_markup=reply_markup)
