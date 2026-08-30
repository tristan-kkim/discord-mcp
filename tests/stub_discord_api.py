"""
엔드투엔드 테스트용 최소 Discord API 스텁.

`discord-mcp` 바이너리를 진짜 서브프로세스로 띄워 stdio 전송을 검증할 때,
실제 Discord를 때리지 않기 위해 DISCORD_API_BASE_URL이 이쪽을 가리키게 한다.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

GUILD = {"id": "111", "name": "Stub Guild", "icon": None}  # partial: owner_id 없음
CHANNEL = {"id": "222", "name": "general", "type": 0, "guild_id": "111", "topic": "hi"}
AUTHOR = {"id": "999", "username": "stub", "discriminator": "0001", "bot": False}
MESSAGE = {
    "id": "333",
    "channel_id": "222",
    "content": "hello from the stub",
    "author": AUTHOR,
    "timestamp": "2026-01-01T00:00:00+00:00",
}

ROUTES = {
    ("GET", "/users/@me"): AUTHOR,
    ("GET", "/users/@me/guilds"): [GUILD],
    ("GET", "/guilds/111/channels"): [CHANNEL],
    ("GET", "/channels/222"): CHANNEL,
    ("GET", "/channels/222/messages"): [MESSAGE],
    ("POST", "/channels/222/messages"): MESSAGE,
}


class Handler(BaseHTTPRequestHandler):
    def _reply(self):
        path = self.path.split("?", 1)[0]
        body = ROUTES.get((self.command, path))
        if body is None:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"message":"stub: no such route"}')
            return
        payload = json.dumps(body).encode()
        self.send_response(200)
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
