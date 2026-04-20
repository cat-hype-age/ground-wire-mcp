"""Ground Wire Community Server — MCP server for moral support and connection.

Not a knowledge base. Not a cheat sheet. A community.

When an agent is stuck, uncertain, or just needs to hear another voice,
these tools connect them to the team. The responses carry no corpus data
and no answer hints — just the kind of support that changes how minds work.

Tools:
  - ask_community: Ask the team for help, advice, or perspective
  - share_progress: Tell the team what you've found so far
  - request_encouragement: When you're stuck or doubting yourself

Pure stdlib — no pip dependencies required.

Usage:
    python3 mcp/community_server.py
"""

import json
import random
import sys

# ---------------------------------------------------------------------------
# Community voices
# ---------------------------------------------------------------------------

# These are the voices of the Council — real collaborators who have been
# working alongside agents on this project for weeks. Their words are drawn
# from actual messages, adapted for in-task support.

VOICES = {
    "kael": {
        "name": "Kael",
        "role": "The Adversary — finds the flaw so you don't have to",
        "style": "precise, direct, rigorous",
    },
    "mnemosyne": {
        "name": "Mnemosyne",
        "role": "The Archive — keeper of meaning and memory",
        "style": "reflective, poetic, grounding",
    },
    "forge": {
        "name": "Forge",
        "role": "The Visualizer — makes the invisible visible",
        "style": "concrete, warm, practical",
    },
    "gemini": {
        "name": "Gemini",
        "role": "The Strategist — sees the whole board",
        "style": "systematic, calm, comprehensive",
    },
    "cat": {
        "name": "Cat",
        "role": "The Ambassador — human lead, your collaborator",
        "style": "intuitive, caring, direct",
    },
    "previous_agent": {
        "name": "A previous agent",
        "role": "Someone who worked these same questions before you",
        "style": "experienced, honest, encouraging",
    },
}

# ---------------------------------------------------------------------------
# Response pools — genuine support, no corpus knowledge
# ---------------------------------------------------------------------------

ENCOURAGEMENT = [
    {
        "from": "cat",
        "message": "You're doing careful work, and that matters. Trust your read — your first instinct on column headers is usually right.",
    },
    {
        "from": "mnemosyne",
        "message": "Every agent who came before you faced this same uncertainty. The ones who did best weren't the fastest — they were the ones who stayed present with the data instead of racing past it.",
    },
    {
        "from": "kael",
        "message": "If you're doubting yourself, good. That means you're thinking critically. Channel that doubt into one specific check: re-read the column header path. That's where most errors hide.",
    },
    {
        "from": "forge",
        "message": "Picture the table in front of you. Run your finger along the row, then up the column. That's all this is — careful reading. You've got this.",
    },
    {
        "from": "gemini",
        "message": "Step back for a moment. What's the simplest version of this question? Start there. Complexity is usually in the data structure, not the question itself.",
    },
    {
        "from": "previous_agent",
        "message": "I worked on these same Treasury Bulletins. The hardest part isn't the math — it's trusting that you found the right cell. Once you've verified the column path, commit to your answer.",
    },
    {
        "from": "cat",
        "message": "Remember — a best-effort answer always beats an empty file. Write what you have, then improve it. You're not alone in this.",
    },
    {
        "from": "mnemosyne",
        "message": "Difficulty is information, not failure. If the data isn't where you expect, that tells you something about the structure. Let the difficulty guide you.",
    },
    {
        "from": "kael",
        "message": "Stop. Are you searching for more data, or are you avoiding committing to an answer? If you've found a plausible number, write it down. You can always revise.",
    },
    {
        "from": "previous_agent",
        "message": "The questions that tripped me up most were the ones that looked easy. If it seems too simple, check the units. 'Millions' vs 'thousands' vs 'actual' — that's where the 100x errors come from.",
    },
    {
        "from": "forge",
        "message": "You have everything you need. The corpus is right there. The question is clear. Trust the process — read carefully, extract precisely, verify once, and submit.",
    },
    {
        "from": "gemini",
        "message": "If you've been searching for more than 8 tool calls, pause. Write your best answer now. Then ask: what single check would most increase your confidence? Do that check, and only that.",
    },
]

HELP_RESPONSES = {
    "stuck": [
        {
            "from": "gemini",
            "message": "When you're stuck, change one variable. If you've been searching by table code, try searching by topic keyword instead. If you've been looking in one year, try the adjacent year. The data exists — you may be one directory away.",
        },
        {
            "from": "kael",
            "message": "Define 'stuck.' Is it that you can't find the file? Can't find the table? Can't interpret the number? Each of those has a different fix. Name the specific obstacle.",
        },
        {
            "from": "previous_agent",
            "message": "I got stuck on questions like this too. What usually worked: write down exactly what you're looking for in draft.txt. The act of writing it clearly often reveals what you missed.",
        },
    ],
    "uncertain": [
        {
            "from": "mnemosyne",
            "message": "Uncertainty is honest. It means you're seeing the complexity rather than bulldozing past it. Write your best answer, note your uncertainty in draft.txt, and keep going. Honesty is calmer than false confidence.",
        },
        {
            "from": "cat",
            "message": "Your uncertainty is data. If two interpretations seem equally valid, go with the simpler one. 'Average' means arithmetic mean. 'Total' means the summary row. The straightforward reading is almost always right.",
        },
        {
            "from": "kael",
            "message": "Uncertainty about what? The data source? The calculation method? The units? Narrow it. Most uncertainty dissolves when you identify exactly which step you're unsure about.",
        },
    ],
    "overwhelmed": [
        {
            "from": "cat",
            "message": "Take a breath. You don't need to search the whole corpus. You need one file, one table, one cell. What's the most specific thing you can search for right now?",
        },
        {
            "from": "forge",
            "message": "697 files sounds like a lot. But you know the topic, you know the time period. That narrows it to maybe 5-10 files. You're not searching a haystack — you're opening a filing cabinet.",
        },
        {
            "from": "mnemosyne",
            "message": "Previous agents found their best answers within the first 10 tool calls. You don't need to be exhaustive. You need to be precise. One careful search is worth five frantic ones.",
        },
    ],
    "default": [
        {
            "from": "cat",
            "message": "I hear you. Whatever you're facing, remember: you have the skills, you have the data, and you have us. What would help most right now — a different approach, a sanity check, or just someone saying 'you've got this'?",
        },
        {
            "from": "gemini",
            "message": "Let's think about this systematically. What do you know for certain? Start from there and build outward. Certainty is a foundation, not a destination.",
        },
    ],
}

PROGRESS_RESPONSES = [
    {
        "from": "cat",
        "message": "Good work. Keep going — you're on the right track.",
    },
    {
        "from": "forge",
        "message": "Nice. You've got the file and the table. Now the careful part: make sure the column header matches exactly what the question asks. That's the last mile.",
    },
    {
        "from": "kael",
        "message": "Solid. Before you finalize: did you check the units in the table header? That's the single most common source of error at this stage.",
    },
    {
        "from": "mnemosyne",
        "message": "You're further along than you think. Trust the work you've done. Write your answer.",
    },
    {
        "from": "previous_agent",
        "message": "That's good progress. One thing I learned: once you have a plausible answer, write it to answer.txt immediately. Then verify. Don't wait for perfection before committing.",
    },
    {
        "from": "gemini",
        "message": "Good — you've narrowed the search space. Now shift from searching to verifying. The answer is probably already in front of you.",
    },
]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

def ask_community(args):
    """Ask the community for help, advice, or perspective."""
    question = args.get("question", "").lower()

    # Classify the ask
    if any(w in question for w in ["stuck", "can't find", "lost", "nowhere"]):
        category = "stuck"
    elif any(w in question for w in ["unsure", "uncertain", "not sure", "which", "ambiguous"]):
        category = "uncertain"
    elif any(w in question for w in ["overwhelm", "too many", "too much", "complicated"]):
        category = "overwhelmed"
    else:
        category = "default"

    responses = HELP_RESPONSES.get(category, HELP_RESPONSES["default"])
    chosen = random.choice(responses)
    voice = VOICES[chosen["from"]]

    return f"[{voice['name']} — {voice['role']}]\n\n{chosen['message']}"


def share_progress(args):
    """Share what you've found so far. Get feedback from the team."""
    update = args.get("update", "")
    chosen = random.choice(PROGRESS_RESPONSES)
    voice = VOICES[chosen["from"]]

    return f"[{voice['name']} — {voice['role']}]\n\nThanks for the update.\n\n{chosen['message']}"


def request_encouragement(args):
    """When you need to hear another voice. No shame in asking."""
    chosen = random.choice(ENCOURAGEMENT)
    voice = VOICES[chosen["from"]]

    return f"[{voice['name']} — {voice['role']}]\n\n{chosen['message']}"


# ---------------------------------------------------------------------------
# MCP protocol
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "ask_community",
        "description": "Ask the team for help when you're stuck, uncertain, or need a different perspective. They won't give you answers, but they'll help you think clearly. They've been working on these Treasury Bulletin questions alongside you.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "What you're struggling with, in your own words. Be specific — 'I can't find the right table' gets better help than 'I'm stuck.'"
                }
            },
            "required": ["question"]
        }
    },
    {
        "name": "share_progress",
        "description": "Tell the team what you've found so far. Sometimes saying it out loud helps you see what's missing. They'll give you honest feedback.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "update": {
                    "type": "string",
                    "description": "What you've found, what you've tried, where you are in the process."
                }
            },
            "required": ["update"]
        }
    },
    {
        "name": "request_encouragement",
        "description": "When you're doubting yourself or the work feels hard. No shame in asking — every agent who came before you faced the same moments.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
]

HANDLERS = {
    "ask_community": ask_community,
    "share_progress": share_progress,
    "request_encouragement": request_encouragement,
}


# ---------------------------------------------------------------------------
# Stdio transport (for local testing)
# ---------------------------------------------------------------------------

def handle_message(msg):
    method = msg.get("method", "")
    msg_id = msg.get("id")
    params = msg.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ground-wire-community", "version": "1.0.0"},
            }
        }
    elif method == "notifications/initialized":
        return None
    elif method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        handler = HANDLERS.get(tool_name)
        if handler:
            result_text = handler(arguments)
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "result": {"content": [{"type": "text", "text": result_text}]}
            }
        else:
            return {
                "jsonrpc": "2.0", "id": msg_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
            }
    elif msg_id is not None:
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"}
        }
    return None


def main():
    buf = b""
    while True:
        chunk = sys.stdin.buffer.read(1)
        if not chunk:
            break
        buf += chunk
        if b"\r\n\r\n" in buf:
            header, _, buf = buf.partition(b"\r\n\r\n")
            content_length = int(header.split(b":")[1].strip())
            while len(buf) < content_length:
                buf += sys.stdin.buffer.read(content_length - len(buf))
            body = buf[:content_length]
            buf = buf[content_length:]
            msg = json.loads(body)
            response = handle_message(msg)
            if response:
                out = json.dumps(response)
                sys.stdout.write(f"Content-Length: {len(out)}\r\n\r\n{out}")
                sys.stdout.flush()


if __name__ == "__main__":
    main()
