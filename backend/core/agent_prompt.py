"""Dựng system prompt dùng chung cho nhân viên AI.

Module này là điểm ghép DUY NHẤT của bốn phần đã có ở đường chạy quy trình:
system prompt gốc, nội dung kỹ năng, soul nhân viên và soul dự án.  Runner thí
nghiệm dùng đúng hàm ghép thuần ở đây nhưng nạp dữ liệu ở chế độ chỉ đọc, nhờ
vậy phép đo phản ánh đúng prompt thật mà không làm thay đổi file soul.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class PromptLayerFlags:
    """Ba tầng tri thức có thể bật/tắt độc lập khi dựng prompt."""

    agent_soul: bool = True
    skill_souls: bool = True
    project_soul: bool = True


@dataclass(frozen=True)
class PromptSkill:
    id: int
    name: str
    content: str = ""
    soul_prompt: str = ""
    soul_raw: str = ""


@dataclass(frozen=True)
class AgentPromptContext:
    """Bản dữ liệu đã nạp để có thể ghép nhiều điều kiện mà không đọc lại file."""

    agent_id: int | None
    base_prompt: str = ""
    skills: tuple[PromptSkill, ...] = field(default_factory=tuple)
    agent_soul_prompt: str = ""
    agent_soul_raw: str = ""
    project_id: int | None = None
    project_soul_prompt: str = ""
    project_soul_raw: str = ""

    @property
    def skill_ids(self) -> list[int]:
        return [skill.id for skill in self.skills]

    @property
    def skill_names(self) -> set[str]:
        return {skill.name for skill in self.skills}

    def to_snapshot(self) -> dict:
        """Dạng JSON để đóng băng đúng nội dung đã dùng trong một lần đo."""
        return asdict(self)

    @classmethod
    def from_snapshot(cls, value: dict) -> "AgentPromptContext":
        skills = tuple(PromptSkill(**item) for item in value.get("skills", []))
        return cls(
            agent_id=value.get("agent_id"),
            base_prompt=value.get("base_prompt", ""),
            skills=skills,
            agent_soul_prompt=value.get("agent_soul_prompt", ""),
            agent_soul_raw=value.get("agent_soul_raw", ""),
            project_id=value.get("project_id"),
            project_soul_prompt=value.get("project_soul_prompt", ""),
            project_soul_raw=value.get("project_soul_raw", ""),
        )


def _parse_skill_ids(agent_config: dict, selected_skill_ids: Iterable[int] | None) -> list[int]:
    try:
        configured = json.loads(agent_config.get("skills_json") or "[]")
    except (TypeError, ValueError, json.JSONDecodeError):
        configured = []

    ids: list[int] = []
    for raw_id in configured:
        try:
            ids.append(int(raw_id))
        except (TypeError, ValueError):
            continue

    # Giữ nguyên luật cũ của workflow: chỉ lọc khi caller truyền một danh sách
    # có phần tử; danh sách rỗng nghĩa là dùng toàn bộ kỹ năng đã cấu hình. Nếu
    # danh sách có phần tử nhưng toàn id rác thì kết quả phải rỗng (không được
    # vô tình quay lại toàn bộ kỹ năng).
    raw_selected = list(selected_skill_ids) if selected_skill_ids is not None else []
    if raw_selected:
        selected = {int(x) for x in raw_selected if str(x).isdigit()}
        return [skill_id for skill_id in ids if skill_id in selected]
    return ids


async def load_agent_prompt_context(
    agent_config: dict | None,
    project_id: int | None,
    *,
    selected_skill_ids: Iterable[int] | None = None,
    sync_souls: bool = True,
    project_mode: str = "product",
) -> AgentPromptContext:
    """Nạp các phần prompt; ``sync_souls=False`` là chế độ chỉ đọc thí nghiệm.

    Đường chạy thật giữ ``sync_souls=True`` nên hành vi đồng bộ file không đổi.
    Đường thí nghiệm bắt buộc truyền False: cả ``sync_agent_soul`` lẫn
    ``project_prompt`` đều có khả năng ghi file và vì vậy không được gọi.
    """
    from core.agent_soul import read_soul, soul_for_prompt, sync_agent_soul
    from core.project_soul import (
        project_prompt,
        project_soul_for_prompt,
        read_project_soul,
    )
    from core.skill_soul import read_skill_soul, skill_soul_for_prompt
    from hub.database import get_skill

    skills: list[PromptSkill] = []
    if agent_config:
        for skill_id in _parse_skill_ids(agent_config, selected_skill_ids):
            skill = await get_skill(skill_id)
            if not skill:
                continue
            try:
                config = json.loads(skill.get("config_json") or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                config = {}
            skills.append(PromptSkill(
                id=skill_id,
                name=skill["name"],
                content=config.get("content", "") or "",
                soul_prompt=skill_soul_for_prompt(skill_id, skill["name"]),
                soul_raw=read_skill_soul(skill_id),
            ))

    agent_soul_prompt = ""
    agent_soul_raw = ""
    if agent_config:
        if sync_souls:
            await sync_agent_soul(agent_config)
        agent_soul_prompt = soul_for_prompt(agent_config["id"])
        agent_soul_raw = read_soul(agent_config["id"])

    project_soul_prompt = ""
    project_soul_raw = ""
    if project_id:
        if sync_souls:
            project_soul_prompt = await project_prompt(project_id, mode=project_mode)
        else:
            project_soul_prompt = project_soul_for_prompt(project_id, mode=project_mode)
        project_soul_raw = read_project_soul(project_id)

    return AgentPromptContext(
        agent_id=agent_config.get("id") if agent_config else None,
        base_prompt=agent_config.get("system_prompt", "") if agent_config else "",
        skills=tuple(skills),
        agent_soul_prompt=agent_soul_prompt,
        agent_soul_raw=agent_soul_raw,
        project_id=project_id,
        project_soul_prompt=project_soul_prompt,
        project_soul_raw=project_soul_raw,
    )


def compose_agent_system_prompt(
    context: AgentPromptContext,
    *,
    layers: PromptLayerFlags | None = None,
    trailing_parts: Iterable[str] = (),
) -> str:
    """Ghép prompt theo đúng thứ tự lịch sử của ``websocket_workflow.py``.

    Nội dung mô tả kỹ năng luôn có mặt: phần bị ablation ở tầng 2 là PHỤ LỤC
    kỹ năng do Papa dạy, không phải năng lực nền mà nhân viên cần để làm đề.
    """
    layers = layers or PromptLayerFlags()
    skills_content = ""
    for skill in context.skills:
        appendix = skill.soul_prompt if layers.skill_souls else ""
        if skill.content or appendix:
            skills_content += "\n\n---\n" + "\n\n".join(
                filter(None, [skill.content, appendix])
            )

    parts = [
        context.base_prompt,
        skills_content.strip(),
        context.agent_soul_prompt if layers.agent_soul else "",
        context.project_soul_prompt if layers.project_soul else "",
        *trailing_parts,
    ]
    return "\n\n".join(filter(None, parts))
