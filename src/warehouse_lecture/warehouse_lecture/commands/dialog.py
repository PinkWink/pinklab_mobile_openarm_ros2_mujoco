"""Dialog manager: utterance -> (clarify | confirm | execute) with short-term context (M4 example 05, promoted).

    dm = DialogManager(parser, executor=run_fn, speak=print)
    dm.handle("상자 옮겨")            -> asks which parcel (slot missing), remembers the pending intent
    dm.handle("파란 거")              -> fills the slot from context, confirms, executes
State: last command (for "그거", "거기"), pending clarification, confirmation policy per intent.
"""

from .schema import Intent, RobotCommand

CONFIRM_INTENTS = {Intent.move_object}          # long, physical actions get a yes/no before running
# 확인 대기 중에만 쓰이므로 짧은 감탄사도 긍정으로 본다.
YES = ("응", "네", "예", "그래", "좋아", "해", "ok", "yes", "맞아", "진행", "음", "어", "엉", "오케이")
NO = ("아니", "아냐", "취소", "no", "안 해", "하지 마", "그만")


class DialogManager:
    def __init__(self, parser, executor=None, speak=print, confirm=True, max_context=6):
        self.parser, self.executor, self.speak = parser, executor, speak
        self.confirm = confirm
        self.context = []             # [(user, assistant_json)] given back to the parser for slot filling
        self.max_context = max_context
        self.pending = None           # RobotCommand waiting for confirmation
        self.clarifying = None        # last utterance that needed more information
        self.log = []                 # (user, action, text)

    def handle(self, text):
        text = text.strip()
        if not text:
            return None
        if self.pending is not None:
            return self._answer_confirmation(text)
        utterance = f"{self.clarifying} / {text}" if self.clarifying else text
        cmd = self.parser.parse(utterance, context=self.context)
        problems = cmd.validate_world()
        self._remember(utterance, cmd)
        if cmd.intent == Intent.answer or problems:
            # clarification (or refusal / plain answer): nothing executes
            reply = cmd.reply or ("; ".join(problems) if problems else "")
            asks = problems or any(k in reply for k in ("?", "까요", "알려", "말씀", "어떤", "어디", "무엇", "무슨", "구체적"))
            self.clarifying = utterance if asks else None
            return self._say("clarify" if self.clarifying else "answer", reply, cmd)
        self.clarifying = None
        if self.confirm and cmd.intent in CONFIRM_INTENTS:
            self.pending = cmd
            return self._say("confirm", f"{cmd.reply or cmd.describe()} 진행할까요?", cmd)
        return self._execute(cmd, text)

    def _answer_confirmation(self, text):
        cmd, self.pending = self.pending, None
        t = "".join(ch for ch in text.lower() if ch.isalnum() or ch == " ").strip()   # 문장부호·말줄임표 제거
        if any(t.startswith(y) or y == t for y in YES):
            return self._execute(cmd, text)
        if any(n in t for n in NO):
            return self._say("cancel", "취소했습니다.", cmd)
        # anything else is treated as a new utterance (e.g. a correction)
        return self.handle(text)

    def _execute(self, cmd, text):
        if self.executor is None:
            return self._say("execute(dry)", cmd.reply or cmd.describe(), cmd)
        self._say("execute", cmd.reply or cmd.describe(), cmd)
        result = self.executor(cmd, text)
        spoken = getattr(result, "spoken", None) or str(result)
        return self._say("result", spoken, cmd)

    def _remember(self, user, cmd):
        self.context.append((user, cmd.model_dump_json(exclude_none=True)))
        self.context = self.context[-self.max_context:]

    def _say(self, action, text, cmd):
        self.log.append((action, text))
        self.speak(text)
        return action, text, cmd


class PlanDialogManager(DialogManager):
    """Same dialog states, but the parser returns a RobotPlan (step list) and the confirmation
    shows the numbered steps. ``executor(plan, text)`` runs it (ExecutePlan action client)."""

    def handle(self, text):
        text = text.strip()
        if not text:
            return None
        if self.pending is not None:
            return self._answer_confirmation(text)
        utterance = f"{self.clarifying} / {text}" if self.clarifying else text
        plan = self.parser.parse(utterance, context=self.context)
        problems = plan.validate_world()
        self._remember(utterance, plan)
        if not plan.steps or problems:
            reply = plan.reply or ("; ".join(problems) if problems else "")
            asks = bool(problems) or any(k in reply for k in ("?", "까요", "알려", "말씀", "어떤", "어디", "무엇", "무슨", "구체적"))
            self.clarifying = utterance if asks else None
            return self._say("clarify" if self.clarifying else "answer", reply, plan)
        self.clarifying = None
        if self.confirm and plan.needs_confirmation():
            self.pending = plan
            return self._say("confirm", f"{plan.reply or plan.summary}\n{plan.describe()}\n진행할까요?", plan)
        return self._execute(plan, text)

    def _execute(self, plan, text):
        if self.executor is None:
            return self._say("execute(dry)", plan.describe(), plan)
        self._say("execute", plan.reply or plan.summary or plan.describe(), plan)
        result = self.executor(plan, text)
        spoken = getattr(result, "spoken", None) or str(result)
        return self._say("result", spoken, plan)
