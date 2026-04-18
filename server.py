try:
	import cgi
except Exception:
	cgi = None
import json
import os
import re
import sys
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CMR_DIR = os.path.join(DATA_DIR, "cmr")
ORDERS_FILE = os.path.join(DATA_DIR, "driver_orders.json")
MAX_PLAYERS = 8
VIDEO_CONTROLLER_NAME = "sobik"


def _default_scores():
	return {str(i): 0 for i in range(1, MAX_PLAYERS + 1)}


def _default_player_names():
	return {str(i): "Gracz %d" % i for i in range(1, MAX_PLAYERS + 1)}

BUZZER_STATE = {
	"round_id": 1,
	"round_started_ms": 0,
	"winner": None,
	"winner_name": "",
	"winner_time_ms": None,
	"video_url": "",
	"video_paused": False,
	"video_time_sec": 0.0,
	"scores": _default_scores(),
	"player_names": _default_player_names(),
	"last_update_ms": 0,
}


def ensure_dirs():
	os.makedirs(DATA_DIR, exist_ok=True)
	os.makedirs(CMR_DIR, exist_ok=True)


def read_orders():
	if not os.path.exists(ORDERS_FILE):
		return []
	try:
		with open(ORDERS_FILE, "r", encoding="utf-8") as f:
			parsed = json.load(f)
		if isinstance(parsed, list):
			return parsed
		return []
	except Exception:
		return []


def write_orders(items):
	with open(ORDERS_FILE, "w", encoding="utf-8") as f:
		json.dump(items, f, ensure_ascii=False, indent=2)


def sanitize_filename(filename):
	name = os.path.basename(filename or "cmr")
	name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
	if not name:
		name = "cmr"
	return name


class AppHandler(SimpleHTTPRequestHandler):
	def _send_cors_headers(self):
		self.send_header("Access-Control-Allow-Origin", "*")
		self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		self.send_header("Access-Control-Allow-Headers", "Content-Type")

	def json_response(self, payload, status=200):
		body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
		self.send_response(status)
		self._send_cors_headers()
		self.send_header("Content-Type", "application/json; charset=utf-8")
		self.send_header("Content-Length", str(len(body)))
		self.end_headers()
		self.wfile.write(body)

	def do_OPTIONS(self):
		self.send_response(204)
		self._send_cors_headers()
		self.end_headers()

	def _now_ms(self):
		return int(time.time() * 1000)

	def _sanitize_player(self, value):
		try:
			player = int(value)
		except Exception:
			return None
		if player < 1 or player > MAX_PLAYERS:
			return None
		return player

	def _sanitize_name(self, value, default_name):
		text = str(value or "").strip()
		if not text:
			return default_name
		if len(text) > 20:
			return text[:20]
		return text

	def _sanitize_delta(self, value):
		try:
			delta = int(value)
		except Exception:
			return None
		if delta not in (-1, 1):
			return None
		return delta

	def _sanitize_time_sec(self, value):
		try:
			time_sec = float(value)
		except Exception:
			return None
		if time_sec < 0:
			return 0.0
		if time_sec > 86400:
			return 86400.0
		return time_sec

	def _sanitize_bool(self, value):
		if isinstance(value, bool):
			return value
		return None

	def _is_video_controller(self, name):
		text = str(name or "").strip().lower()
		return text == VIDEO_CONTROLLER_NAME

	def _new_round(self):
		BUZZER_STATE["round_id"] = BUZZER_STATE["round_id"] + 1
		BUZZER_STATE["round_started_ms"] = self._now_ms()
		BUZZER_STATE["winner"] = None
		BUZZER_STATE["winner_name"] = ""
		BUZZER_STATE["winner_time_ms"] = None
		BUZZER_STATE["video_paused"] = False
		BUZZER_STATE["last_update_ms"] = self._now_ms()

	def _ensure_round_started(self):
		if BUZZER_STATE["round_started_ms"] == 0:
			self._new_round()

	def _ensure_scores_and_names(self):
		scores = BUZZER_STATE.get("scores")
		if not isinstance(scores, dict):
			BUZZER_STATE["scores"] = _default_scores()
		names = BUZZER_STATE.get("player_names")
		if not isinstance(names, dict):
			BUZZER_STATE["player_names"] = _default_player_names()
		for i in range(1, MAX_PLAYERS + 1):
			key = str(i)
			if key not in BUZZER_STATE["scores"]:
				BUZZER_STATE["scores"][key] = 0
			if key not in BUZZER_STATE["player_names"]:
				BUZZER_STATE["player_names"][key] = "Gracz %d" % i

	def _public_buzzer_state(self):
		self._ensure_scores_and_names()
		return {
			"roundId": BUZZER_STATE["round_id"],
			"roundStartedMs": BUZZER_STATE["round_started_ms"],
			"winner": BUZZER_STATE["winner"],
			"winnerName": BUZZER_STATE["winner_name"],
			"winnerTimeMs": BUZZER_STATE["winner_time_ms"],
			"videoUrl": BUZZER_STATE["video_url"],
			"videoPaused": BUZZER_STATE["video_paused"],
			"videoTimeSec": BUZZER_STATE["video_time_sec"],
			"videoControllerName": VIDEO_CONTROLLER_NAME,
			"scores": BUZZER_STATE["scores"],
			"playerNames": BUZZER_STATE["player_names"],
			"lastUpdateMs": BUZZER_STATE["last_update_ms"],
		}

	def do_GET(self):
		parsed = urlparse(self.path)
		if parsed.path == "/api/driver-orders":
			self.json_response(read_orders(), 200)
			return
		if parsed.path == "/api/buzzer-state":
			self._ensure_round_started()
			self.json_response(self._public_buzzer_state(), 200)
			return
		super().do_GET()

	def do_POST(self):
		parsed = urlparse(self.path)
		if parsed.path == "/api/driver-orders":
			self.handle_driver_orders_post()
			return
		if parsed.path == "/api/upload-cmr":
			self.handle_upload_cmr_post()
			return
		if parsed.path == "/api/buzzer-click":
			self.handle_buzzer_click_post()
			return
		if parsed.path == "/api/buzzer-reset":
			self.handle_buzzer_reset_post()
			return
		if parsed.path == "/api/buzzer-video":
			self.handle_buzzer_video_post()
			return
		if parsed.path == "/api/buzzer-score":
			self.handle_buzzer_score_post()
			return
		if parsed.path == "/api/buzzer-join":
			self.handle_buzzer_join_post()
			return
		if parsed.path == "/api/buzzer-video-sync":
			self.handle_buzzer_video_sync_post()
			return
		self.json_response({"error": "Not found"}, 404)

	def handle_driver_orders_post(self):
		try:
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, list):
				self.json_response({"error": "Payload must be a list"}, 400)
				return
			# Najważniejsze: pełną listę zleceń zapisujemy atomowo do data/driver_orders.json.
			write_orders(parsed)
			self.json_response({"ok": True}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_upload_cmr_post(self):
		try:
			if cgi is None:
				self.json_response({"error": "Upload CMR chwilowo niedostepny na tej wersji Pythona"}, 501)
				return
			form = cgi.FieldStorage(
				fp=self.rfile,
				headers=self.headers,
				environ={
					"REQUEST_METHOD": "POST",
					"CONTENT_TYPE": self.headers.get("Content-Type", ""),
				},
			)
			file_item = form["cmrFile"] if "cmrFile" in form else None
			if not file_item or not getattr(file_item, "filename", ""):
				self.json_response({"error": "Brak pliku cmrFile"}, 400)
				return
			filename = sanitize_filename(file_item.filename)
			stamp = str(int(time.time() * 1000))
			final_name = stamp + "_" + filename
			target_path = os.path.join(CMR_DIR, final_name)
			with open(target_path, "wb") as out:
				out.write(file_item.file.read())
			rel = "/data/cmr/" + final_name
			self.json_response({"ok": True, "path": rel}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_buzzer_click_post(self):
		try:
			self._ensure_round_started()
			self._ensure_scores_and_names()
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return

			player = self._sanitize_player(parsed.get("player"))
			if player is None:
				self.json_response({"error": "Invalid player number"}, 400)
				return

			player_name = self._sanitize_name(parsed.get("name"), "Gracz %d" % player)
			BUZZER_STATE["player_names"][str(player)] = player_name
			if BUZZER_STATE["winner"] is not None:
				self.json_response(
					{
						"ok": True,
						"accepted": False,
						"state": self._public_buzzer_state(),
					},
					200,
				)
				return

			now_ms = self._now_ms()
			reaction_ms = now_ms - BUZZER_STATE["round_started_ms"]
			if reaction_ms < 0:
				reaction_ms = 0

			# Najważniejsze: zapisujemy pierwszego klikającego globalnie, żeby każdy klient widział tego samego zwycięzcę.
			BUZZER_STATE["winner"] = player
			BUZZER_STATE["winner_name"] = player_name
			BUZZER_STATE["winner_time_ms"] = reaction_ms
			BUZZER_STATE["video_paused"] = True
			BUZZER_STATE["last_update_ms"] = now_ms

			self.json_response(
				{
					"ok": True,
					"accepted": True,
					"state": self._public_buzzer_state(),
				},
				200,
			)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_buzzer_reset_post(self):
		try:
			self._new_round()
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_buzzer_video_post(self):
		try:
			self._ensure_round_started()
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			video_url = str(parsed.get("videoUrl", "")).strip()
			BUZZER_STATE["video_url"] = video_url
			BUZZER_STATE["video_paused"] = False
			BUZZER_STATE["video_time_sec"] = 0.0
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_buzzer_video_sync_post(self):
		try:
			self._ensure_round_started()
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			name = str(parsed.get("name", "")).strip()
			if not self._is_video_controller(name):
				self.json_response({"error": "Only sobik can control video"}, 403)
				return
			time_sec = self._sanitize_time_sec(parsed.get("timeSec"))
			if time_sec is None:
				self.json_response({"error": "Invalid timeSec"}, 400)
				return
			paused = self._sanitize_bool(parsed.get("paused"))
			if paused is None:
				self.json_response({"error": "Invalid paused flag"}, 400)
				return
			# Najważniejsze: tylko sobik aktualizuje globalny czas filmu, zeby wszystkim przewijalo sie identycznie.
			BUZZER_STATE["video_time_sec"] = time_sec
			BUZZER_STATE["video_paused"] = paused
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_buzzer_score_post(self):
		try:
			self._ensure_round_started()
			self._ensure_scores_and_names()
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			player = self._sanitize_player(parsed.get("player"))
			if player is None:
				self.json_response({"error": "Invalid player number"}, 400)
				return
			delta = self._sanitize_delta(parsed.get("delta"))
			if delta is None:
				self.json_response({"error": "Invalid delta"}, 400)
				return
			player_name = self._sanitize_name(parsed.get("name"), "Gracz %d" % player)
			key = str(player)
			# Najważniejsze: punkty zapisujemy globalnie na serwerze, żeby kazdy klient widzial ten sam ranking.
			BUZZER_STATE["scores"][key] = int(BUZZER_STATE["scores"].get(key, 0)) + delta
			BUZZER_STATE["player_names"][key] = player_name
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_buzzer_join_post(self):
		try:
			self._ensure_round_started()
			self._ensure_scores_and_names()
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			player = self._sanitize_player(parsed.get("player"))
			if player is None:
				self.json_response({"error": "Invalid player number"}, 400)
				return
			player_name = self._sanitize_name(parsed.get("name"), "Gracz %d" % player)
			BUZZER_STATE["player_names"][str(player)] = player_name
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)


def main():
	ensure_dirs()
	port = 8080
	env_port = os.environ.get("PORT", "").strip()
	if env_port:
		try:
			port = int(env_port)
		except Exception:
			port = 8080
	if len(sys.argv) > 1:
		try:
			port = int(sys.argv[1])
		except Exception:
			pass
	server = HTTPServer(("0.0.0.0", port), AppHandler)
	print("Serwer uruchomiony na http://0.0.0.0:%d (LAN: http://<twoj-ip>:%d)" % (port, port))
	server.serve_forever()


if __name__ == "__main__":
	main()
