from dataclasses import dataclass
import json
import os

import aiohttp
from sanic import Blueprint, Request
from sanic.response import text as text_response
from sanic.log import logger
from sanic_ext import openapi, validate
from sqlalchemy import select

from backend_sanic.embeddings import strings_to_embeddings
from backend_sanic.models import EmbeddedChunk


APP_OLLAMA_HOST: str = os.environ.get("APP_OLLAMA_HOST", "")
if not APP_OLLAMA_HOST:
    raise Exception("APP_OLLAMA_HOST environment variable not set")

OLLAMA_MODEL = "mistral-openorca"


@dataclass
class ChatRequest:
    msg: str


bp = Blueprint("chat")


@bp.route("/chat", methods={"POST"})
@openapi.definition(
    body={"application/json": ChatRequest},
    response=openapi.response(
        200, {"text/plain": str}, "Returns chunked chat completion text"
    ),
)
@validate(json=ChatRequest)
async def chat(request: Request, body: ChatRequest):
    """Generate text from a prompt msg"""
    generate_url = f"http://{APP_OLLAMA_HOST}/api/generate"
    chat_msg = body.msg
    if not chat_msg:
        logger.error(f"{chat_msg=} not provided in {body=} {request.body=}")
        return text_response("error: msg not provided", status=400)
    chat_embedding = strings_to_embeddings(chat_msg)
    logger.info(f"{chat_msg=} {chat_embedding=}")
    session = request.ctx.session
    async with session.begin():
        result = await session.scalars(
            select(EmbeddedChunk)
            .filter(EmbeddedChunk.vector.l2_distance(chat_embedding) < 0.2)
            .order_by(EmbeddedChunk.vector.l2_distance(chat_embedding).desc())
            .limit(3)
        )
        close_chunks = result.all()
        logger.info(f"{close_chunks=}")
    if len(close_chunks) > 0:
        close_texts = [chunk.chunk_text for chunk in close_chunks]
        context = "\n###\n".join(close_texts)
        prompt_msg = f"""Use the following context to respond to the message.
context: {context}\n###
message: {chat_msg}
"""
    else:
        prompt_msg = chat_msg
    generate_request = {
        "model": OLLAMA_MODEL,
        "prompt": prompt_msg,
        "stream": True,
    }
    logger.info(f"handling {generate_request=}")
    sanic_response = await request.respond(content_type="text/plain")
    complete_text = ""
    async with aiohttp.ClientSession() as session:
        async with session.post(generate_url, json=generate_request) as response:
            logger.info(f"{response.status=} from {generate_url=}")
            response.raise_for_status()
            async for data in response.content.iter_any():
                data_str = data.decode("utf-8")
                data_obj = json.loads(data_str)
                response_text = data_obj["response"]
                complete_text += response_text
                await sanic_response.send(response_text)
    await sanic_response.eof()
    logger.info(f"handled {generate_request=} with {complete_text=}")
