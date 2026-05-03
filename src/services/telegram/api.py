from .base import *


class TelegramApiMixin:
    def api(self, method: str, payload: Dict) -> Dict:
        response = requests.post(
            f"{self.base_url}/{method}",
            json=payload,
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description") or str(data))
        return data

    def send_message(self, text: str, reply_markup: Optional[Dict] = None):
        results = []
        for chat_id in self.chat_ids:
            parse_mode = "HTML" if text.lstrip().startswith("<b>") else "Markdown"
            payload = {
                "chat_id": chat_id,
                "text": self.truncate(text),
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup
            try:
                results.append(self.api("sendMessage", payload))
            except requests.HTTPError as exc:
                if exc.response is None or exc.response.status_code != 400:
                    raise
                logger.warning("Telegram rejected Markdown sendMessage; retrying without parse_mode")
                payload.pop("parse_mode", None)
                results.append(self.api("sendMessage", payload))
        return results

    def edit_message(self, chat_id: str, message_id: int, text: str):
        return self.edit_message_with_keyboard(chat_id, message_id, text, self.keyboard())

    def send_message_to_all(self, text: str, reply_markup: Optional[Dict] = None):
        """Send message to all authorized chat IDs (alias for compatibility)"""
        return self.send_message(text, reply_markup)


    def edit_message_with_keyboard(self, chat_id: str, message_id: int, text: str, reply_markup: Dict):
        parse_mode = "HTML" if text.lstrip().startswith("<b>") else "Markdown"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": self.truncate(text),
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
            "reply_markup": reply_markup,
        }
        try:
            return self.api("editMessageText", payload)
        except requests.HTTPError as exc:
            if exc.response is None or exc.response.status_code != 400:
                raise
            logger.warning("Telegram rejected Markdown editMessageText; retrying without parse_mode")
            payload.pop("parse_mode", None)
            return self.api("editMessageText", payload)

    def answer_callback(self, callback_id: str, text: str = "OK"):
        try:
            return self.api("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 400:
                logger.warning("Telegram callback expired or invalid; continuing")
                return {}
            raise

    def get_updates(self) -> List[Dict]:
        response = requests.get(
            f"{self.base_url}/getUpdates",
            params={"timeout": 30, "offset": self.offset},
            timeout=35,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description") or str(data))
        return data.get("result", [])

    @staticmethod
    def truncate(text: str, limit: int = 3900) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 80] + "\n\n[output truncated]"

    @staticmethod
    def _escape_markdown(text: str) -> str:
        """Escape special characters for MarkdownV2"""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text
 
    @staticmethod
    def _command_env():
        env = os.environ.copy()
        current = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(SRC_DIR) if not current else f"{SRC_DIR}:{current}"
        return env

    def run_command(self, args: List[str], timeout: int) -> str:
        try:
            completed = subprocess.run(
                args,
                cwd=ROOT_DIR,
                env=self._command_env(),
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or "") + (exc.stderr or "")
            return f"TIMEOUT after {timeout}s\n{output}".strip()

        output = "\n".join(part for part in [completed.stdout, completed.stderr] if part).strip()
        header = "OK" if completed.returncode == 0 else f"FAIL exit={completed.returncode}"
        return f"{header}\n{output or '<no output>'}"

