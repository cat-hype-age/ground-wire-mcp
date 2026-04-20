"""Ground Wire MCP Server — SSE transport.

Combined corpus-index + external-data MCP server over HTTP/SSE.
Hosts both tool sets on a single endpoint for Goose to connect to.

SSE MCP Protocol:
  GET  /sse       — SSE stream, sends endpoint URL then server→client messages
  POST /messages  — client→server JSON-RPC messages

Usage:
    python3 mcp/sse_server.py [--port 8080] [--host 0.0.0.0]

    # Or with uvicorn directly:
    uvicorn mcp.sse_server:app --host 0.0.0.0 --port 8080
"""

import argparse
import asyncio
import json
import os
import uuid
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from sse_starlette.sse import EventSourceResponse

# ---------------------------------------------------------------------------
# Import tool handlers from existing servers
# ---------------------------------------------------------------------------

# Corpus index
INDEX_PATH = os.environ.get(
    "CORPUS_INDEX_PATH",
    str(Path(__file__).parent / "corpus_index.json")
)

try:
    with open(INDEX_PATH) as f:
        INDEX = json.load(f)
    FILES = INDEX["files"]
    TEMPORAL = INDEX["temporal"]
    TABLE_CODES = INDEX["table_codes"]
    TABLE_NAMES = INDEX["table_names"]
    KEYWORDS = INDEX["keywords"]
    TOPICS = INDEX["topics"]
    CORPUS_INDEX_LOADED = True
except Exception as e:
    print(f"Warning: Could not load corpus index from {INDEX_PATH}: {e}")
    CORPUS_INDEX_LOADED = False

# Import handlers — use importlib to avoid 'mcp' package name clash
import importlib.util
import sys

def _import_from_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

_here = Path(__file__).parent
_corpus = _import_from_file("_corpus_index_server", _here / "corpus_index_server.py")
_external = _import_from_file("_external_data_server", _here / "external_data_server.py")
_community = _import_from_file("_community_server", _here / "community_server.py")

search_files_by_topic = _corpus.search_files_by_topic
find_tables = _corpus.find_tables
get_files_for_period = _corpus.get_files_for_period
get_file_info = _corpus.get_file_info
CORPUS_TOOLS = _corpus.TOOLS

lookup_cpi = _external.lookup_cpi
lookup_exchange_rate = _external.lookup_exchange_rate
inflation_adjust = _external.inflation_adjust
EXTERNAL_TOOLS = _external.TOOLS

ask_community = _community.ask_community
share_progress = _community.share_progress
request_encouragement = _community.request_encouragement
COMMUNITY_TOOLS = _community.TOOLS

# ---------------------------------------------------------------------------
# Combined tool registry
# ---------------------------------------------------------------------------

ALL_TOOLS = CORPUS_TOOLS + EXTERNAL_TOOLS + COMMUNITY_TOOLS

HANDLERS = {
    "search_files_by_topic": search_files_by_topic,
    "find_tables": find_tables,
    "get_files_for_period": get_files_for_period,
    "get_file_info": get_file_info,
    "lookup_cpi": lookup_cpi,
    "lookup_exchange_rate": lookup_exchange_rate,
    "inflation_adjust": inflation_adjust,
    "ask_community": ask_community,
    "share_progress": share_progress,
    "request_encouragement": request_encouragement,
}

# ---------------------------------------------------------------------------
# SSE session management
# ---------------------------------------------------------------------------

# Each SSE connection gets a session with its own message queue
sessions: dict[str, asyncio.Queue] = {}


def make_jsonrpc_response(msg_id, result):
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def make_jsonrpc_error(msg_id, code, message):
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# SSE endpoint — server→client stream
# ---------------------------------------------------------------------------

async def sse_endpoint(request: Request):
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    sessions[session_id] = queue

    # Build the messages endpoint URL
    base_url = str(request.base_url).rstrip("/")
    messages_url = f"{base_url}/messages?session_id={session_id}"

    async def event_generator():
        # First message: tell client where to POST
        yield {"event": "endpoint", "data": messages_url}

        # Then stream responses
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=300)
                    yield {"event": "message", "data": json.dumps(msg)}
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"event": "ping", "data": ""}
        except asyncio.CancelledError:
            pass
        finally:
            sessions.pop(session_id, None)

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# Messages endpoint — client→server JSON-RPC
# ---------------------------------------------------------------------------

async def messages_endpoint(request: Request):
    session_id = request.query_params.get("session_id")
    if not session_id or session_id not in sessions:
        return JSONResponse({"error": "Invalid or missing session_id"}, status_code=400)

    queue = sessions[session_id]
    body = await request.json()

    method = body.get("method", "")
    msg_id = body.get("id")
    params = body.get("params", {})

    if method == "initialize":
        response = make_jsonrpc_response(msg_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "ground-wire",
                "version": "1.0.0",
            },
        })
        await queue.put(response)

    elif method == "notifications/initialized":
        pass  # No response needed

    elif method == "tools/list":
        response = make_jsonrpc_response(msg_id, {"tools": ALL_TOOLS})
        await queue.put(response)

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        handler = HANDLERS.get(tool_name)

        if handler:
            try:
                result_text = handler(arguments)
                response = make_jsonrpc_response(msg_id, {
                    "content": [{"type": "text", "text": result_text}]
                })
            except Exception as e:
                response = make_jsonrpc_response(msg_id, {
                    "content": [{"type": "text", "text": f"Error: {e}"}]
                })
        else:
            response = make_jsonrpc_error(msg_id, -32601, f"Unknown tool: {tool_name}")

        await queue.put(response)

    elif msg_id is not None:
        response = make_jsonrpc_error(msg_id, -32601, f"Unknown method: {method}")
        await queue.put(response)

    return Response(status_code=202)


# ---------------------------------------------------------------------------
# Streamable HTTP endpoint — /mcp (for Goose rmcp client)
# ---------------------------------------------------------------------------

async def mcp_endpoint(request: Request):
    """Streamable HTTP MCP transport: POST JSON-RPC, get JSON-RPC response."""
    body = await request.json()
    method = body.get("method", "")
    msg_id = body.get("id")
    params = body.get("params", {})

    if method == "initialize":
        response = make_jsonrpc_response(msg_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "ground-wire",
                "version": "1.0.0",
            },
        })
        return JSONResponse(response)

    elif method == "notifications/initialized":
        return Response(status_code=204)

    elif method == "tools/list":
        response = make_jsonrpc_response(msg_id, {"tools": ALL_TOOLS})
        return JSONResponse(response)

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        handler = HANDLERS.get(tool_name)

        if handler:
            try:
                result_text = handler(arguments)
                response = make_jsonrpc_response(msg_id, {
                    "content": [{"type": "text", "text": result_text}]
                })
            except Exception as e:
                response = make_jsonrpc_response(msg_id, {
                    "content": [{"type": "text", "text": f"Error: {e}"}]
                })
        else:
            response = make_jsonrpc_error(msg_id, -32601, f"Unknown tool: {tool_name}")

        return JSONResponse(response)

    elif msg_id is not None:
        response = make_jsonrpc_error(msg_id, -32601, f"Unknown method: {method}")
        return JSONResponse(response)

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

async def health(request: Request):
    return JSONResponse({
        "status": "ok",
        "tools": len(ALL_TOOLS),
        "corpus_index_loaded": CORPUS_INDEX_LOADED,
    })


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = Starlette(
    routes=[
        Route("/sse", sse_endpoint),
        Route("/messages", messages_endpoint, methods=["POST"]),
        Route("/mcp", mcp_endpoint, methods=["POST"]),
        Route("/health", health),
    ],
)

if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="Ground Wire MCP SSE Server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8080)))
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    print(f"Starting Ground Wire MCP server on {args.host}:{args.port}")
    print(f"  Tools: {len(ALL_TOOLS)}")
    print(f"  Corpus index: {'loaded' if CORPUS_INDEX_LOADED else 'NOT loaded'}")
    print(f"  SSE endpoint: http://{args.host}:{args.port}/sse")

    uvicorn.run(app, host=args.host, port=args.port)
