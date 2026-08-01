from __future__ import annotations

import asyncio
import logging
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReactionTypeEmoji

from packages.channels import ChannelMessage
from packages.config import Settings
from packages.core import Task
from services.channels import ChannelGateway
from services.integrations.telegram_adapter import TelegramAdapter
from services.orchestrator.capabilities import plan_actions_for_goal
from services.orchestrator.runtime import OrchestratorRuntime
from services.perception.stt import STT_UNAVAILABLE

LOGGER = logging.getLogger(__name__)

# Telegram Bot API hard limit; leave headroom for safety.
_TELEGRAM_TEXT_LIMIT = 4000
# Shown in chat while the agent works; header "печатает…" comes from sendChatAction.
_ACK_TEXT = "✅ Запрос принят\n⏳ ИИ печатает ответ…"
_BUSY_TEXT = (
    "⏳ Уже обрабатываю предыдущий запрос.\n"
    "Дождитесь ответа — затем можно писать снова."
)
_TYPING_INTERVAL_SECONDS = 3.0
_PROGRESS_INTERVAL_SECONDS = 8.0


def split_telegram_text(text: str, limit: int = _TELEGRAM_TEXT_LIMIT) -> list[str]:
    """Split long agent replies into Telegram-safe chunks."""
    value = text if text else "(пустой ответ)"
    if len(value) <= limit:
        return [value]
    chunks: list[str] = []
    rest = value
    while rest:
        chunks.append(rest[:limit])
        rest = rest[limit:]
    return chunks


class TelegramBotService:
    """Polling Telegram bot that routes admin chat messages into the runtime."""

    def __init__(
        self,
        settings: Settings,
        runtime: OrchestratorRuntime | None = None,
        gateway: ChannelGateway | None = None,
    ) -> None:
        self._settings = settings
        self._adapter = TelegramAdapter(
            token=settings.telegram_bot_token,
            admin_chat_id=settings.telegram_admin_chat_id,
        )
        self._runtime = runtime or OrchestratorRuntime(settings)
        self._gateway = gateway or ChannelGateway()
        self._bot: Bot | None = None
        self._dispatcher: Dispatcher | None = None
        self._task: asyncio.Task[None] | None = None
        # One in-flight agent job per chat — prevents silent queue pile-ups.
        self._busy_chats: set[str] = set()

    @property
    def adapter(self) -> TelegramAdapter:
        return self._adapter

    def is_ready(self) -> bool:
        return self._adapter.is_available()

    def format_task_reply(self, message: ChannelMessage, success: bool, detail: str) -> str:
        status = "ok" if success else "failed"
        return (
            f"[{message.channel}] {status}\n"
            f"You: {message.text}\n"
            f"Agent: {detail}"
        )

    def notify_task_status(self, text: str) -> None:
        """Push outbound status via Bot API helpers (works without polling)."""
        if not self._adapter.is_configured():
            return
        try:
            self._adapter.notify_admin(text)
        except Exception:  # noqa: BLE001 - notification must not break chat replies
            LOGGER.exception("Failed to notify Telegram admin")

    def handle_voice_file(
        self,
        user_id: str,
        audio_path: Path | str,
        duration_seconds: float = 0.0,
        *,
        notify: bool = True,
    ) -> str:
        """Transcribe a local audio file via STT, then run it as a text goal."""
        if not self._adapter.is_authorized(user_id):
            return "Access denied. Only the configured admin chat can use this bot."

        voice = self._gateway.ingest_voice(
            "telegram",
            transcript="",
            duration_seconds=duration_seconds,
            audio_path=audio_path,
            language=self._runtime.settings.stt_language,
        )
        if not voice.transcript or voice.transcript == STT_UNAVAILABLE:
            return (
                "Голос не распознан (STT недоступен). "
                "Установи faster-whisper: pip install 'local-ai-agent[integrations]' "
                "или отправь текст. "
                "Для русского языка оставь LOCAL_AI_AGENT_STT_LANGUAGE пустым (auto)."
            )
        return self.handle_text(user_id, voice.transcript, notify=notify)

    def handle_text(self, user_id: str, text: str, *, notify: bool = True) -> str:
        if not self._adapter.is_authorized(user_id):
            return "Access denied. Only the configured admin chat can use this bot."

        inbound = self._gateway.ingest_text("telegram", user_id, text)
        command = text.strip().lower()
        if command in {"/start", "start"}:
            return (
                "Local AI Agent online.\n"
                "Пиши обычным текстом — отвечу через локальную модель Ollama.\n"
                "Команды: /status /help"
            )
        if command in {"/help", "help"}:
            return (
                "Commands:\n"
                "/start - bot greeting\n"
                "/status - runtime status\n"
                "/approve <task-id> - continue paused approval task\n"
                "/reject <task-id> - reject paused approval task\n"
                "/help - this help\n"
                "Текст = чат с локальной Ollama.\n"
                "Голос = STT (auto RU/EN) → та же обработка.\n"
                "Примеры:\n"
                "• создай файл hello.py со скриптом print hello\n"
                "• найди в интернете pathlib\n"
                "• https://example.com — загрузка страницы"
            )
        if command in {"/status", "status"}:
            agents = self._runtime.refresh_agents()
            settings = self._runtime.settings
            ollama_ok = agents.online
            resolved = agents.resolved
            return (
                f"app={settings.app_name}\n"
                f"env={settings.env}\n"
                f"model_primary={settings.model_primary}\n"
                f"model_router={settings.model_router}\n"
                f"model_primary_resolved={resolved.primary}\n"
                f"model_router_resolved={resolved.router}\n"
                f"ollama_url={settings.ollama_url}\n"
                f"ollama_ok={ollama_ok}\n"
                f"stt_language={settings.stt_language or 'auto'}\n"
                f"web_search=duckduckgo"
            )

        approval_reply = self._handle_approval_command(text)
        if approval_reply is not None:
            return approval_reply

        if not self._runtime.agents.online:
            self._runtime.refresh_agents()

        actions = plan_actions_for_goal(inbound.text, f"telegram:{user_id}")
        chat_only = len(actions) == 1 and actions[0].name == "reflect"
        if chat_only:
            # Fast conversational path: skip swarm/router fan-out.
            try:
                memory_hits = self._runtime.memory_store.retrieve(inbound.text, limit=5)
                snippets = [f"{item.key}:{item.value}" for item in memory_hits]
                action = actions[0]
                result = self._runtime.capabilities.reflect(action, snippets)
                reply = self.format_task_reply(inbound, result.success, result.message)
            except Exception as exc:  # noqa: BLE001 - surface to chat
                LOGGER.exception("Telegram chat failed for chat %s", user_id)
                reply = self.format_task_reply(inbound, False, f"error: {exc}")
            if notify:
                self.notify_task_status(reply)
            return reply

        task = Task(
            title=f"telegram:{user_id}",
            goal=inbound.text,
            actions=actions,
        )
        try:
            result = self._runtime.run_task(task)
        except Exception as exc:  # noqa: BLE001 - surface runtime errors to Telegram chat
            LOGGER.exception("Telegram task failed for chat %s", user_id)
            reply = self.format_task_reply(inbound, False, f"error: {exc}")
            if notify:
                self.notify_task_status(reply)
            return reply

        policy = result.policy_decision
        if not result.success and policy is not None and policy.required_approval:
            reply = self.format_task_reply(
                inbound,
                False,
                (
                    f"approval required for task {task.id}: {result.message}\n"
                    f"Approve: /approve {task.id}\n"
                    f"Reject: /reject {task.id}"
                ),
            )
        else:
            reply = self.format_task_reply(inbound, result.success, result.message)
        if notify:
            self.notify_task_status(reply)
        return reply

    def _handle_approval_command(self, text: str) -> str | None:
        parts = text.strip().split()
        if not parts:
            return None
        verb = parts[0].lower().lstrip("/")
        if verb not in {"approve", "reject"}:
            return None
        if len(parts) < 2:
            return f"Usage: /{verb} <task-id>"
        task_id = parts[1].strip()
        approved = verb == "approve"
        try:
            result = self._runtime.continue_task(
                task_id,
                approved=approved,
                reviewer="telegram",
            )
        except Exception as exc:  # noqa: BLE001 - surface to chat
            LOGGER.exception("Telegram %s failed for task %s", verb, task_id)
            return f"{verb} failed: {exc}"
        status = "approved" if approved else "rejected"
        return (
            f"Task {task_id} {status}.\n"
            f"success={result.success}\n"
            f"{result.message}"
        )

    async def _download_voice_to_temp(self, message: Message) -> tuple[Path, float] | None:
        assert self._bot is not None
        voice = message.voice or message.audio
        if voice is None:
            return None
        duration = float(getattr(voice, "duration", 0) or 0)
        file = await self._bot.get_file(voice.file_id)
        if file.file_path is None:
            return None
        suffix = Path(file.file_path).suffix or ".ogg"
        temp = tempfile.NamedTemporaryFile(prefix="tg-voice-", suffix=suffix, delete=False)
        temp_path = Path(temp.name)
        temp.close()
        await self._bot.download_file(file.file_path, destination=temp_path)
        return temp_path, duration

    async def _send_chunks(self, message: Message, text: str) -> None:
        chunks = split_telegram_text(text)
        for chunk in chunks:
            await message.answer(chunk)

    async def _edit_or_answer(self, status: Message, message: Message, text: str) -> None:
        chunks = split_telegram_text(text)
        try:
            await status.edit_text(chunks[0])
        except Exception:  # noqa: BLE001 - fall back to a fresh reply
            LOGGER.exception("Failed to edit Telegram status message; sending new reply")
            await message.answer(chunks[0])
        for chunk in chunks[1:]:
            await message.answer(chunk)

    async def _send_typing(self, chat_id: int) -> None:
        """Show Telegram header status «печатает…» (expires ~5s; refresh often)."""
        if self._bot is None:
            return
        try:
            await self._bot.send_chat_action(chat_id=chat_id, action="typing")
        except Exception:  # noqa: BLE001 - typing is best-effort
            LOGGER.debug("Telegram typing action failed for chat %s", chat_id, exc_info=True)

    async def _keep_typing(self, chat_id: int) -> None:
        while True:
            await self._send_typing(chat_id)
            await asyncio.sleep(_TYPING_INTERVAL_SECONDS)

    async def _progress_status(self, status: Message, started: float) -> None:
        """Refresh ack message so the user sees the job is still alive."""
        while True:
            await asyncio.sleep(_PROGRESS_INTERVAL_SECONDS)
            elapsed = max(1, int(asyncio.get_running_loop().time() - started))
            try:
                await status.edit_text(
                    f"✅ Запрос принят\n"
                    f"⏳ ИИ печатает ответ… ({elapsed}с)\n"
                    f"Сверху в чате должно быть «печатает»."
                )
            except Exception:  # noqa: BLE001 - ignore edit races / identical content
                LOGGER.debug("Telegram progress edit skipped", exc_info=True)

    async def _react(self, message: Message, emoji: str) -> None:
        try:
            await message.react([ReactionTypeEmoji(emoji=emoji)])
        except Exception:  # noqa: BLE001 - reactions are optional UX
            LOGGER.debug("Telegram reaction %s failed", emoji, exc_info=True)

    def _try_begin_chat_job(self, chat_key: str) -> bool:
        if chat_key in self._busy_chats:
            return False
        self._busy_chats.add(chat_key)
        return True

    def _end_chat_job(self, chat_key: str) -> None:
        self._busy_chats.discard(chat_key)

    async def _respond_with_thinking(
        self,
        message: Message,
        worker: Callable[[], str],
    ) -> None:
        """Ack receipt, show «печатает…», run work off-loop, then replace status with reply."""
        chat_id = message.chat.id
        chat_key = str(chat_id)
        if not self._try_begin_chat_job(chat_key):
            await self._send_typing(chat_id)
            await message.answer(_BUSY_TEXT)
            return

        typing_task = asyncio.create_task(
            self._keep_typing(chat_id),
            name=f"telegram-typing-{chat_id}",
        )
        progress_task: asyncio.Task[None] | None = None
        status: Message | None = None
        try:
            # 1) Header «печатает…» immediately on receive
            await self._send_typing(chat_id)
            # 2) Reaction on the user message = request seen
            await self._react(message, "👀")
            # 3) Visible ack in the thread
            status = await message.answer(_ACK_TEXT)
            started = asyncio.get_running_loop().time()
            progress_task = asyncio.create_task(
                self._progress_status(status, started),
                name=f"telegram-progress-{chat_id}",
            )
            try:
                reply = await asyncio.to_thread(worker)
            except Exception as exc:  # noqa: BLE001 - always answer the user
                LOGGER.exception("Telegram worker failed for chat %s", chat_id)
                reply = f"Ошибка обработки: {exc}"
            if progress_task is not None:
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass
                progress_task = None
            await self._edit_or_answer(status, message, reply)
            await self._react(message, "✅")
        except Exception:  # noqa: BLE001 - last-resort user-visible failure
            LOGGER.exception("Telegram respond_with_thinking failed for chat %s", chat_id)
            fail = "Не удалось обработать сообщение. Попробуйте ещё раз."
            if status is None:
                await message.answer(fail)
            else:
                try:
                    await status.edit_text(fail)
                except Exception:  # noqa: BLE001
                    await message.answer(fail)
            await self._react(message, "❌")
        finally:
            typing_task.cancel()
            try:
                await typing_task
            except asyncio.CancelledError:
                pass
            if progress_task is not None:
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass
            self._end_chat_job(chat_key)

    def _register_handlers(self, dispatcher: Dispatcher) -> None:
        @dispatcher.message(CommandStart())
        async def start_handler(message: Message) -> None:
            reply = await asyncio.to_thread(
                self.handle_text,
                str(message.chat.id),
                "/start",
                notify=False,
            )
            await self._send_chunks(message, reply)

        @dispatcher.message(Command("help"))
        async def help_handler(message: Message) -> None:
            reply = await asyncio.to_thread(
                self.handle_text,
                str(message.chat.id),
                "/help",
                notify=False,
            )
            await self._send_chunks(message, reply)

        @dispatcher.message(Command("status"))
        async def status_handler(message: Message) -> None:
            reply = await asyncio.to_thread(
                self.handle_text,
                str(message.chat.id),
                "/status",
                notify=False,
            )
            await self._send_chunks(message, reply)

        @dispatcher.message(Command("approve"))
        async def approve_handler(message: Message) -> None:
            reply = await asyncio.to_thread(
                self.handle_text,
                str(message.chat.id),
                message.text or "/approve",
                notify=False,
            )
            await self._send_chunks(message, reply)

        @dispatcher.message(Command("reject"))
        async def reject_handler(message: Message) -> None:
            reply = await asyncio.to_thread(
                self.handle_text,
                str(message.chat.id),
                message.text or "/reject",
                notify=False,
            )
            await self._send_chunks(message, reply)

        @dispatcher.message(F.voice | F.audio)
        async def voice_handler(message: Message) -> None:
            chat_id = str(message.chat.id)
            downloaded: Path | None = None

            def work() -> str:
                nonlocal downloaded
                # Download stays async below; sync stage only runs STT+task.
                if downloaded is None:
                    return "Could not download voice message."
                return self.handle_voice_file(
                    chat_id,
                    downloaded,
                    duration,
                    notify=False,
                )

            # Voice needs async download first, then shared ack/typing pipeline.
            if not self._try_begin_chat_job(chat_id):
                await self._send_typing(message.chat.id)
                await message.answer(_BUSY_TEXT)
                return

            typing_task = asyncio.create_task(
                self._keep_typing(message.chat.id),
                name=f"telegram-typing-voice-{chat_id}",
            )
            progress_task: asyncio.Task[None] | None = None
            status: Message | None = None
            duration = 0.0
            try:
                await self._send_typing(message.chat.id)
                await self._react(message, "👀")
                status = await message.answer(_ACK_TEXT)
                started = asyncio.get_running_loop().time()
                progress_task = asyncio.create_task(
                    self._progress_status(status, started),
                    name=f"telegram-progress-voice-{chat_id}",
                )
                try:
                    payload = await self._download_voice_to_temp(message)
                    if payload is None:
                        reply = "Could not download voice message."
                    else:
                        downloaded, duration = payload
                        reply = await asyncio.to_thread(work)
                except Exception:  # noqa: BLE001
                    LOGGER.exception("Telegram voice handling failed for chat %s", chat_id)
                    reply = "Voice handling failed. Send text instead."
                if progress_task is not None:
                    progress_task.cancel()
                    try:
                        await progress_task
                    except asyncio.CancelledError:
                        pass
                    progress_task = None
                if status is None:
                    await self._send_chunks(message, reply)
                else:
                    await self._edit_or_answer(status, message, reply)
                await self._react(message, "✅")
            finally:
                typing_task.cancel()
                try:
                    await typing_task
                except asyncio.CancelledError:
                    pass
                if progress_task is not None:
                    progress_task.cancel()
                    try:
                        await progress_task
                    except asyncio.CancelledError:
                        pass
                if downloaded is not None:
                    downloaded.unlink(missing_ok=True)
                self._end_chat_job(chat_id)

        @dispatcher.message(F.text)
        async def text_handler(message: Message) -> None:
            text = message.text or ""
            chat_id = str(message.chat.id)
            # Fast slash-commands: no thinking placeholder.
            if text.strip().startswith("/"):
                reply = await asyncio.to_thread(
                    self.handle_text,
                    chat_id,
                    text,
                    notify=False,
                )
                await self._send_chunks(message, reply)
                return

            await self._respond_with_thinking(
                message,
                lambda: self.handle_text(chat_id, text, notify=False),
            )

    async def _poll(self) -> None:
        assert self._bot is not None
        assert self._dispatcher is not None
        LOGGER.info("Telegram bot polling started")
        await self._dispatcher.start_polling(self._bot)

    def start_background(self) -> asyncio.Task[None] | None:
        if not self.is_ready():
            LOGGER.warning("Telegram bot is not configured; polling will not start")
            return None
        if self._task and not self._task.done():
            return self._task

        token = self._settings.telegram_bot_token
        assert token is not None
        self._bot = Bot(token=token)
        self._dispatcher = Dispatcher()
        self._register_handlers(self._dispatcher)
        self._task = asyncio.create_task(self._poll(), name="telegram-bot-polling")
        return self._task

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._bot is not None:
            await self._bot.session.close()
        self._task = None
        self._bot = None
        self._dispatcher = None
        LOGGER.info("Telegram bot stopped")


async def run_telegram_bot_forever(
    settings: Settings,
    runtime: OrchestratorRuntime | None = None,
    on_started: Callable[[], Awaitable[None] | None] | None = None,
) -> None:
    service = TelegramBotService(settings=settings, runtime=runtime)
    if not service.is_ready():
        raise RuntimeError(
            "Telegram bot is not configured. Set LOCAL_AI_AGENT_TELEGRAM_BOT_TOKEN "
            "and LOCAL_AI_AGENT_TELEGRAM_ADMIN_CHAT_ID."
        )
    task = service.start_background()
    assert task is not None
    if on_started is not None:
        maybe = on_started()
        if maybe is not None:
            await maybe
    try:
        await task
    finally:
        await service.stop()
