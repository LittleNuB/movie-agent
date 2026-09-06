"""AgentScope conversation, durable sessions, inbox delivery and specialist delegation."""

import asyncio
import logging

from agentscope.agent import Agent, ContextConfig, ModelConfig, ReActConfig
from agentscope.app.message_bus import InMemoryMessageBus, MessageBusKeys
from agentscope.app.middleware import InboxMiddleware
from agentscope.app.storage import AsyncSQLAlchemyStorage, SessionConfig
from agentscope.credential import OpenAICredential
from agentscope.message import HintBlock, Msg, UserMsg
from agentscope.model import OpenAIChatModel
from agentscope.permission import PermissionBehavior, PermissionRule
from agentscope.state import AgentState
from agentscope.tool import Toolkit

from .config import Configuration
from .prompts import ROLES
from .store import Store, uid


class Runtime:
    def __init__(self, store: Store, config: Configuration):
        self.store, self.config = store, config
        self.sessions = AsyncSQLAlchemyStorage("sqlite+aiosqlite:///" + (store.root / "agents.sqlite3").as_posix())
        self.bus = InMemoryMessageBus()
        self.running = {}
        self.agents = {}
        self.tool_factory = lambda project_id, role: []
        self.closing = False
        self.waker = None
        self.specialists = {}

    async def start(self):
        logging.getLogger("agentscope").setLevel(logging.WARNING)
        await self.sessions.__aenter__()
        await self.bus.__aenter__()
        # Durable input records, not the in-memory bus, own restart recovery.
        for project in self.store.projects():
            for entry in self.store.records(project["id"], "inputs"):
                if entry["status"] in {"pending", "processing"}:
                    self.store.update_record(entry["id"], status="pending")
                    await self._push(project["id"], entry)
        self.waker = asyncio.create_task(self._wake_loop())
        for project in self.store.projects():
            for run in self.store.records(project["id"], "runs"):
                if run["role"] != "director" and run["status"] in {"pending", "running"}:
                    self.specialists[run["id"]] = asyncio.create_task(self._specialist(run))

    async def close(self):
        self.closing = True
        if self.waker:
            self.waker.cancel()
        tasks = list(self.running.values()) + list(self.specialists.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        if self.waker:
            await asyncio.gather(self.waker, return_exceptions=True)
        await self.bus.aclose()
        await self.sessions.aclose()

    async def notify(self, project_id, text, *, source="user", input_id=None):
        entry_id = input_id or uid()
        try:
            existing = self.store.record(entry_id, project_id)
        except KeyError:
            existing = None
        if existing:
            if existing.get("text") != text:
                raise ValueError("同一消息身份不能用于不同内容")
            return existing
        entry = self.store.put_record(project_id, "inputs", {"text": text, "source": source, "status": "pending"},
                                      record_id=entry_id)
        await self._push(project_id, entry)
        return entry

    async def _push(self, project_id, entry):
        hint = HintBlock(id=entry["id"], source=entry["source"], hint=entry["text"])
        await self.bus.queue_push(MessageBusKeys.inbox(project_id), hint.model_dump(mode="json"))
        await self.wake(project_id)

    async def wake(self, project_id):
        await self.bus.queue_push(MessageBusKeys.wakeup_queue(), {"session_id": project_id})

    async def _wake_loop(self):
        while not self.closing:
            for _, wake in await self.bus.queue_drain(MessageBusKeys.wakeup_queue(), max_count=64):
                pid = wake["session_id"]
                if pid in self.running and not self.running[pid].done():
                    continue
                self.running[pid] = asyncio.create_task(self._run(pid))
            await asyncio.sleep(0.15)

    def model(self, purpose="director"):
        binding = self.config.binding(purpose)
        if binding.protocol != "openai":
            raise ValueError("导演和视觉理解需要 OpenAI 兼容对话接口")
        options = dict(binding.parameters)
        thinking = options.pop("thinking", None)
        params = OpenAIChatModel.Parameters.model_validate(options)
        return OpenAIChatModel(
            OpenAICredential(api_key=binding.key or "local-no-key", base_url=binding.base_url),
            binding.model, parameters=params, stream=True, max_retries=0,
            client_kwargs={"max_retries": 0, "timeout": 180},
            extra_body={"thinking": thinking} if thinking is not None else None,
        )

    async def make_agent(self, project_id, role="director", session_id=None):
        sid = session_id or project_id
        saved = await self.sessions.get_session("local", role, sid)
        state = saved.state if saved else AgentState(session_id=sid)
        tools = self.tool_factory(project_id, role)
        for tool in tools:
            state.permission_context.allow_rules[tool.name] = [PermissionRule(
                tool_name=tool.name, rule_content=None, behavior=PermissionBehavior.ALLOW,
                source="movie-app:domain-tools-enforce-project-authorization")]
        return Agent(role, ROLES[role], self.model(), toolkit=Toolkit(tools=tools), state=state,
                     middlewares=[InboxMiddleware(self.bus)] if role == "director" else [],
                     model_config=ModelConfig(max_retries=0), context_config=ContextConfig(max_image_num=12),
                     react_config=ReActConfig(max_iters=24, stop_on_reject=True))

    async def persist_agent(self, agent, project_id):
        await self.sessions.upsert_session("local", agent.name,
            SessionConfig(workspace_id=project_id, name=self.store.project(project_id)["title"]),
            state=agent.state, session_id=agent.state.session_id)

    async def _run(self, project_id):
        agent = None
        message_id = uid()
        text = ""
        received = set()
        run = self.store.put_record(project_id, "runs", {"role": "director", "status": "running",
                                                         "input_tokens": 0, "output_tokens": 0})
        try:
            agent = await self.make_agent(project_id)
            self.agents[project_id] = agent
            self.store.update_project(project_id, status="running")
            self.store.put_record(project_id, "messages", {"role": "director", "text": "", "streaming": True}, message_id)
            prompt = "处理收件箱的新消息。先读取项目真实状态，再按用户意图与有效授权行动。"
            async for event in agent.reply_stream(UserMsg("项目服务", prompt), yield_final_msg=True):
                if isinstance(event, Msg):
                    continue
                kind = str(event.type).lower()
                if kind == "text_block_delta":
                    text += event.delta
                    self.store.event(project_id, "text_delta", {"id": message_id, "delta": event.delta})
                elif kind == "hint_block":
                    try:
                        self.store.update_record(event.block_id, status="processing")
                        received.add(event.block_id)
                    except KeyError:
                        pass
                elif kind == "model_call_end":
                    latest = self.store.record(run["id"])
                    self.store.update_record(run["id"], input_tokens=latest["input_tokens"] + event.input_tokens,
                                             output_tokens=latest["output_tokens"] + event.output_tokens)
                elif kind in {"tool_call_end", "tool_result_end"}:
                    self.store.event(project_id, "activity", {"kind": kind, "tool": getattr(event, "name", "film_tool")})
                    await self.persist_agent(agent, project_id)
                elif kind == "exceed_max_iters":
                    text += "\n本轮处理已达到执行步数，需要结合现有产物继续；未完成的任务仍有记录。"
            await self.persist_agent(agent, project_id)
            for entry_id in received:
                self.store.update_record(entry_id, status="done")
            self.store.update_record(message_id, text=text or "已处理当前消息，实际进展见作品和任务记录。", streaming=False)
            self.store.update_record(run["id"], status="completed")
        except asyncio.CancelledError:
            if agent:
                await self.persist_agent(agent, project_id)
            if not self.closing:
                for entry_id in received:
                    self.store.update_record(entry_id, status="done")
            try:
                self.store.update_record(message_id, text=text or "当前本地处理已停止。", streaming=False)
            except KeyError:
                pass
            self.store.update_record(run["id"], status="interrupted")
        except Exception as exc:  # noqa: BLE001 -- SDK errors can contain request credentials
            # Never serialize SDK exceptions: they may include request bodies or URLs.
            error = f"模型交互暂时失败（{type(exc).__name__}），已有作品与输入仍保留；请检查连接或继续对话。"
            self.store.put_record(project_id, "messages", {"role": "director", "text": error, "error": True})
            try:
                self.store.update_record(message_id, text=text, streaming=False)
            except KeyError:
                pass
            self.store.update_record(run["id"], status="failed", error_type=type(exc).__name__)
            for entry in self.store.records(project_id, "inputs"):
                if entry["status"] in {"pending", "processing"}:
                    self.store.update_record(entry["id"], status="failed")
        finally:
            self.agents.pop(project_id, None)
            p = self.store.project(project_id)
            if p["status"] == "running":
                waiting = any(r["status"] == "pending" for r in self.store.records(project_id, "reviews"))
                status = "stopped" if p.get("production_paused") else "waiting_review" if waiting else "idle"
                self.store.update_project(project_id, status=status)
            # Inputs arriving at the final model step still get their own next turn.
            pending = [e for e in self.store.records(project_id, "inputs") if e["status"] == "pending"]
            if pending and not self.closing:
                await self.wake(project_id)

    async def delegate(self, project_id, role, task):
        if role not in {"visual", "post", "check"}:
            raise ValueError("请选择 visual、post 或 check 专业职责")
        if self.store.setting("single_agent", False):
            return {"message": "当前为单 Agent 对照模式；请主导演使用相同工具直接处理此任务。"}
        for run in self.store.records(project_id, "runs"):
            if run["role"] == role and run.get("task") == task and run["status"] in {"pending", "running"}:
                return {"role": role, "run_id": run["id"], "status": run["status"]}
        run = self.store.put_record(project_id, "runs", {"role": role, "task": task, "status": "pending",
            "input_tokens": 0, "output_tokens": 0, "epoch": self.store.project(project_id)["epoch"]})
        self.specialists[run["id"]] = asyncio.create_task(self._specialist(run))
        return {"role": role, "run_id": run["id"], "status": "pending",
                "message": "专业任务已交办，结果会进入导演收件箱。现在可继续与用户交流。"}

    async def _specialist(self, run):
        pid, rid = run["project_id"], run["id"]
        agent = None
        text = ""
        try:
            if self.store.project(pid).get("production_paused"):
                self.store.update_record(rid, status="interrupted")
                return
            agent = await self.make_agent(pid, run["role"], rid)
            self.store.update_record(rid, status="running")
            async for event in agent.reply_stream(UserMsg("主导演", run["task"]), yield_final_msg=True):
                if isinstance(event, Msg):
                    continue
                kind = str(event.type).lower()
                if kind == "text_block_delta":
                    text += event.delta
                elif kind == "model_call_end":
                    latest = self.store.record(rid)
                    self.store.update_record(rid, input_tokens=latest["input_tokens"] + event.input_tokens,
                                             output_tokens=latest["output_tokens"] + event.output_tokens)
                elif kind in {"tool_call_end", "tool_result_end"}:
                    await self.persist_agent(agent, pid)
            await self.persist_agent(agent, pid)
            self.store.update_record(rid, status="completed", result=text)
            if not self.store.project(pid).get("production_paused"):
                await self.notify(pid, f"专业任务 {rid}（{run['role']}）已返回：{text}",
                                  source="specialist", input_id="specialist-" + rid)
        except asyncio.CancelledError:
            if agent:
                await self.persist_agent(agent, pid)
            self.store.update_record(rid, status="pending" if self.closing else "interrupted", result=text)
        except Exception as exc:  # noqa: BLE001 -- retain partial work and sanitized failure
            self.store.update_record(rid, status="failed", error_type=type(exc).__name__, result=text)
            if not self.closing and not self.store.project(pid).get("production_paused"):
                await self.notify(pid, f"专业任务 {rid} 失败（{type(exc).__name__}）；已有产物仍保留，请先查看项目再决定修复。", source="specialist")

    async def stop(self, project_id):
        self.store.stop(project_id)
        task = self.running.get(project_id)
        if task and not task.done():
            task.cancel()
        for run in self.store.records(project_id, "runs"):
            task = self.specialists.get(run["id"])
            if task and not task.done():
                task.cancel()
