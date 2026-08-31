"""
엔드투엔드 테스트용 최소 Discord API 스텁.

`discord-mcp` 바이너리를 진짜 서브프로세스로 띄워 stdio 전송을 검증할 때,
실제 Discord를 때리지 않기 위해 DISCORD_API_BASE_URL이 이쪽을 가리키게 한다.
실패 경로도 스텁한다 — 에러가 프로세스 경계를 넘어 모델에게 도달하는지가
이 서버에서 가장 자주 깨졌던 부분이기 때문이다.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

VIEW_CHANNEL = 1 << 10
SEND_MESSAGES = 1 << 11
READ_HISTORY = 1 << 16

# partial guild: owner_id가 없고 permissions는 있다 (/users/@me/guilds의 형태)
GUILD = {
    "id": "111", "name": "Stub Guild", "icon": None,
    "permissions": str(VIEW_CHANNEL | SEND_MESSAGES | READ_HISTORY),
}
CHANNEL = {"id": "222", "name": "general", "type": 0, "guild_id": "111", "topic": "hi"}
LOCKED_CHANNEL = {"id": "444", "name": "locked", "type": 0, "guild_id": "111"}
AUTHOR = {"id": "999", "username": "stub", "bot": False}
MESSAGE = {
    "id": "333",
    "channel_id": "222",
    "content": "hello from the stub",
    "author": AUTHOR,
    "timestamp": "2026-01-01T00:00:00+00:00",
}
MEMBER_ME = {"user": {"id": "999", "username": "stub"}, "roles": []}

# Message Content Intent가 꺼진 앱. 이 상태가 실제 사용자의 상태였다.
APPLICATION = {"id": "1", "name": "stub-app", "flags": 0}

ROUTES = {
    ("GET", "/users/@me"): AUTHOR,
    ("GET", "/users/@me/guilds"): [GUILD],
    ("GET", "/applications/@me"): APPLICATION,
    ("GET", "/guilds/111/channels"): [CHANNEL, LOCKED_CHANNEL],
    ("GET", "/guilds/111/members/@me"): MEMBER_ME,
    ("GET", "/channels/222"): CHANNEL,
    ("GET", "/channels/444"): LOCKED_CHANNEL,
    ("GET", "/channels/222/messages"): [MESSAGE],
    ("POST", "/channels/222/messages"): MESSAGE,
}

# 봇이 볼 수 없는 채널. Discord가 실제로 돌려주는 형태 그대로 응답한다.
FAILURES = {
    ("GET", "/channels/444/messages"): (403, {"message": "Missing Access", "code": 50001}),
}


class Handler(BaseHTTPRequestHandler):
    def _reply(self):
        path = self.path.split("?", 1)[0]
        key = (self.command, path)

        if key in FAILURES:
            status, body = FAILURES[key]
        elif key in ROUTES:
            status, body = 200, ROUTES[key]
        else:
            status, body = 404, {"message": "stub: no such route", "code": 0}

        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = do_PATCH = do_DELETE = _reply

    def log_message(self, *args):  # 테스트 출력 오염 방지
        pass


def serve() -> tuple[HTTPServer, str]:
    """스텁을 임의 포트로 띄우고 (서버, base_url)을 돌려준다."""
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


if __name__ == "__main__":
    server, url = serve()
    print(url, flush=True)
    server.serve_forever()
