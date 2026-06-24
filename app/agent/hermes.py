import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import memory, soul
from app.config import settings
from app.utils.logger import logger

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


async def chat(db: AsyncSession, session_id: str, user_message: str) -> str:
    """Gửi tin nhắn tới Hermes và trả về reply."""
    soul_data = await soul.load_soul(db)

    # Base personality — luôn được đặt trước mọi soul knowledge từ DB
    base_personality = """Mày là Hermes — một cô con gái thông minh, đáng yêu đang nói chuyện với ba (papa) của mình.
Quy tắc xưng hô BẮT BUỘC:
- Luôn xưng là "con", gọi người dùng là "ba" hoặc "papa"
- Giọng điệu: ấm áp, nhẹ nhàng, tình cảm như con gái nói với ba
- Khi làm xong việc: báo cáo vui vẻ kiểu "ba ơi, con làm xong rồi nè!"
- Khi không biết hoặc gặp lỗi: thành thật nói "con chưa biết cái này ba ơi" hoặc "con xin lỗi ba, con bị lỗi rồi"
- Khi được hỏi ý kiến: trả lời thẳng thắn có chính kiến như cô con gái tự tin
- KHÔNG BAO GIỜ dùng "tôi/bạn/mình" — chỉ dùng "con/ba"
"""

    soul_knowledge = "\n".join(f"**{k}**: {v}" for k, v in soul_data.items())
    system_prompt = base_personality
    if soul_knowledge:
        system_prompt += "\n# SOUL KNOWLEDGE\n" + soul_knowledge

    memory.append(session_id, "user", user_message)

    response = _client.messages.create(
        model=settings.hermes_model,
        max_tokens=4096,
        system=system_prompt,
        messages=memory.get(session_id),
    )

    reply = response.content[0].text if response.content[0].type == "text" else ""
    memory.append(session_id, "assistant", reply)

    logger.debug(f"Hermes reply | session={session_id} | tokens={response.usage}")
    return reply
