try:
	import cgi
except Exception:
	cgi = None
import json
import os
import random
import re
import sys
import time
import unicodedata
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CMR_DIR = os.path.join(DATA_DIR, "cmr")
ORDERS_FILE = os.path.join(DATA_DIR, "driver_orders.json")
AVATAR_DIR = os.path.join(DATA_DIR, "avatars")
AVATAR_PRESET_DIR = os.path.join(BASE_DIR, "avatar_presets")
MAX_PLAYERS = 8
VIDEO_CONTROLLER_NAME = "sobik"
VIDEO_CONTROLLER_PASSWORD = "lol123ASD@"
DEEZER_POLISH_HIPHOP_QUERY = "polski hip hop"
QUIZ_PHASE_DURATIONS = [16]
QUIZ_PHASE_POINTS = [3]
QUIZ_REVEAL_CLIP_SEC = 10


def _fold_text_answer(text):
	if not text:
		return ""
	s = unicodedata.normalize("NFD", str(text))
	s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
	s = s.lower()
	s = re.sub(r"[^\w\s]+", " ", s, flags=re.UNICODE)
	s = re.sub(r"\s+", " ", s).strip()
	return s


def _strip_title_feat(title):
	t = str(title or "").strip()
	parts = re.split(r"\s*\(\s*feat", t, 1, flags=re.I)
	t = parts[0]
	parts = re.split(r"\s+feat\.?\s", t, 1, flags=re.I)
	return parts[0].strip()


def _default_scores():
	return {str(i): 0 for i in range(1, MAX_PLAYERS + 1)}


def _default_player_names():
	return {str(i): "Gracz %d" % i for i in range(1, MAX_PLAYERS + 1)}


def _default_player_avatars():
	return {str(i): "" for i in range(1, MAX_PLAYERS + 1)}


def _default_name_for_player(player):
	return "Gracz %d" % player

BUZZER_STATE = {
	"round_id": 1,
	"round_started_ms": 0,
	"winner": None,
	"winner_name": "",
	"winner_time_ms": None,
	"video_url": "",
	"video_paused": False,
	"video_time_sec": 0.0,
	"quiz_preview_url": "",
	"quiz_track_label": "",
	"quiz_track_title": "",
	"quiz_track_artist": "",
	"quiz_track_id": "",
	"quiz_music_query": DEEZER_POLISH_HIPHOP_QUERY,
	"quiz_reveal_active": False,
	"quiz_reveal_seek_middle": False,
	"quiz_command_token": 0,
	"quiz_command_duration_sec": 0,
	"quiz_command_issued_ms": 0,
	"quiz_round_active": False,
	"quiz_phase_index": -1,
	"quiz_guessed_players": {},
	"quiz_artist_hint_players": {},
	"quiz_wrong_players": {},
	"quiz_wrong_guesses": {},
	"quiz_ready_players": {},
	"scores": _default_scores(),
	"player_names": _default_player_names(),
	"player_avatars": _default_player_avatars(),
	"last_update_ms": 0,
}


def ensure_dirs():
	os.makedirs(DATA_DIR, exist_ok=True)
	os.makedirs(CMR_DIR, exist_ok=True)
	os.makedirs(AVATAR_DIR, exist_ok=True)
	os.makedirs(AVATAR_PRESET_DIR, exist_ok=True)


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

	def _sanitize_duration_sec(self, value):
		try:
			duration = int(value)
		except Exception:
			return None
		if duration < 1 or duration > 30:
			return None
		return duration

	def _sanitize_ready(self, value):
		if isinstance(value, bool):
			return value
		return None

	def _is_video_controller(self, name):
		text = str(name or "").strip().lower()
		return text == VIDEO_CONTROLLER_NAME

	def _is_valid_video_controller_password(self, password):
		return str(password or "") == VIDEO_CONTROLLER_PASSWORD

	def _is_default_player_name(self, player, name):
		return str(name or "").strip() == _default_name_for_player(player)

	def _same_name(self, left, right):
		return str(left or "").strip().lower() == str(right or "").strip().lower()

	def _find_player_by_name(self, name):
		target = str(name or "").strip().lower()
		if not target:
			return None
		for i in range(1, MAX_PLAYERS + 1):
			key = str(i)
			current = str(BUZZER_STATE["player_names"].get(key, "")).strip().lower()
			if current == target:
				return i
		return None

	def _pick_free_player(self):
		for i in range(1, MAX_PLAYERS + 1):
			key = str(i)
			current_name = BUZZER_STATE["player_names"].get(key, _default_name_for_player(i))
			if self._is_default_player_name(i, current_name):
				return i
		return 1

	def _new_round(self):
		BUZZER_STATE["round_id"] = BUZZER_STATE["round_id"] + 1
		BUZZER_STATE["round_started_ms"] = self._now_ms()
		BUZZER_STATE["winner"] = None
		BUZZER_STATE["winner_name"] = ""
		BUZZER_STATE["winner_time_ms"] = None
		BUZZER_STATE["video_paused"] = False
		BUZZER_STATE["quiz_round_active"] = False
		BUZZER_STATE["quiz_phase_index"] = -1
		BUZZER_STATE["quiz_command_duration_sec"] = 0
		BUZZER_STATE["quiz_command_issued_ms"] = 0
		BUZZER_STATE["quiz_reveal_active"] = False
		BUZZER_STATE["quiz_reveal_seek_middle"] = False
		BUZZER_STATE["quiz_track_label"] = ""
		BUZZER_STATE["quiz_track_title"] = ""
		BUZZER_STATE["quiz_track_artist"] = ""
		BUZZER_STATE["quiz_track_id"] = ""
		BUZZER_STATE["quiz_preview_url"] = ""
		BUZZER_STATE["last_update_ms"] = self._now_ms()
		self._ensure_quiz_state()
		for i in range(1, MAX_PLAYERS + 1):
			# Najważniejsze: po resecie kolejna runda wymaga ponownego Gotowy (unikamy podwójnego autostartu).
			BUZZER_STATE["quiz_ready_players"][str(i)] = False
			BUZZER_STATE["quiz_artist_hint_players"][str(i)] = False
			BUZZER_STATE["quiz_guessed_players"][str(i)] = False
			BUZZER_STATE["quiz_wrong_players"][str(i)] = False
			BUZZER_STATE["quiz_wrong_guesses"][str(i)] = []

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

	def _ensure_player_avatars(self):
		pa = BUZZER_STATE.get("player_avatars")
		if not isinstance(pa, dict):
			BUZZER_STATE["player_avatars"] = _default_player_avatars()
			pa = BUZZER_STATE["player_avatars"]
		for i in range(1, MAX_PLAYERS + 1):
			key = str(i)
			if key not in pa:
				pa[key] = ""

	def _sanitize_avatar_preset_filename(self, raw):
		name = os.path.basename(str(raw or "").strip())
		if not name or name in (".", ".."):
			return None
		if not re.match(r"^[A-Za-z0-9._-]+$", name):
			return None
		low = name.lower()
		if not (
			low.endswith(".png")
			or low.endswith(".jpg")
			or low.endswith(".jpeg")
			or low.endswith(".webp")
			or low.endswith(".gif")
		):
			return None
		path = os.path.join(AVATAR_PRESET_DIR, name)
		if not os.path.isfile(path):
			return None
		return name

	def _avatar_preset_public_url(self, filename):
		return "/avatar_presets/" + filename

	def _is_avatar_preset_taken(self, public_url, except_key):
		self._ensure_player_avatars()
		for i in range(1, MAX_PLAYERS + 1):
			k = str(i)
			if k == except_key:
				continue
			if not self._is_player_occupied(i):
				continue
			cur = str(BUZZER_STATE["player_avatars"].get(k, "")).strip()
			if cur == public_url:
				return True
		return False

	def _delete_legacy_uploaded_avatar_file(self, key):
		self._ensure_player_avatars()
		prev = str(BUZZER_STATE.get("player_avatars", {}).get(key, "")).strip()
		if prev.startswith("/data/avatars/"):
			rel = prev.lstrip("/").replace("/", os.sep)
			path = os.path.join(BASE_DIR, rel)
			if os.path.isfile(path):
				try:
					os.remove(path)
				except Exception:
					pass
		stem = os.path.join(AVATAR_DIR, "p%s" % key)
		for ext in (".jpg", ".png", ".webp"):
			path = stem + ext
			if os.path.isfile(path):
				try:
					os.remove(path)
				except Exception:
					pass

	def _ensure_quiz_state(self):
		guessed = BUZZER_STATE.get("quiz_guessed_players")
		if not isinstance(guessed, dict):
			BUZZER_STATE["quiz_guessed_players"] = {}
			guessed = BUZZER_STATE["quiz_guessed_players"]
		ready = BUZZER_STATE.get("quiz_ready_players")
		if not isinstance(ready, dict):
			BUZZER_STATE["quiz_ready_players"] = {}
			ready = BUZZER_STATE["quiz_ready_players"]
		for i in range(1, MAX_PLAYERS + 1):
			key = str(i)
			if key not in guessed:
				guessed[key] = False
			if key not in ready:
				ready[key] = False
		hint = BUZZER_STATE.get("quiz_artist_hint_players")
		if not isinstance(hint, dict):
			BUZZER_STATE["quiz_artist_hint_players"] = {}
			hint = BUZZER_STATE["quiz_artist_hint_players"]
		for i in range(1, MAX_PLAYERS + 1):
			key = str(i)
			if key not in hint:
				hint[key] = False
		mq = BUZZER_STATE.get("quiz_music_query")
		if not isinstance(mq, str) or len(str(mq).strip()) < 2:
			# Najważniejsze: domyślny typ muzyki przy starym stanie serwera bez tego pola.
			BUZZER_STATE["quiz_music_query"] = DEEZER_POLISH_HIPHOP_QUERY
		if "quiz_reveal_active" not in BUZZER_STATE:
			BUZZER_STATE["quiz_reveal_active"] = False
		if "quiz_reveal_seek_middle" not in BUZZER_STATE:
			BUZZER_STATE["quiz_reveal_seek_middle"] = False
		if "quiz_track_title" not in BUZZER_STATE:
			BUZZER_STATE["quiz_track_title"] = ""
		if "quiz_track_artist" not in BUZZER_STATE:
			BUZZER_STATE["quiz_track_artist"] = ""
		wrong = BUZZER_STATE.get("quiz_wrong_players")
		if not isinstance(wrong, dict):
			BUZZER_STATE["quiz_wrong_players"] = {}
			wrong = BUZZER_STATE["quiz_wrong_players"]
		wg = BUZZER_STATE.get("quiz_wrong_guesses")
		if not isinstance(wg, dict):
			BUZZER_STATE["quiz_wrong_guesses"] = {}
			wg = BUZZER_STATE["quiz_wrong_guesses"]
		for i in range(1, MAX_PLAYERS + 1):
			key = str(i)
			if key not in wrong:
				wrong[key] = False
			if key not in wg or not isinstance(wg.get(key), list):
				wg[key] = []

	def _is_player_occupied(self, player):
		key = str(player)
		name = BUZZER_STATE["player_names"].get(key, _default_name_for_player(player))
		return not self._is_default_player_name(player, name)

	def _count_guessed_players(self):
		self._ensure_quiz_state()
		total = 0
		for i in range(1, MAX_PLAYERS + 1):
			key = str(i)
			if self._is_player_occupied(i) and bool(BUZZER_STATE["quiz_guessed_players"].get(key)):
				total = total + 1
		return total

	def _count_occupied_players(self):
		self._ensure_scores_and_names()
		total = 0
		for i in range(1, MAX_PLAYERS + 1):
			if self._is_player_occupied(i):
				total = total + 1
		return total

	def _count_ready_players(self):
		self._ensure_quiz_state()
		total = 0
		for i in range(1, MAX_PLAYERS + 1):
			key = str(i)
			if self._is_player_occupied(i) and bool(BUZZER_STATE["quiz_ready_players"].get(key)):
				total = total + 1
		return total

	def _all_occupied_ready(self):
		occupied = self._count_occupied_players()
		if occupied <= 0:
			return False
		return self._count_ready_players() >= occupied

	def _quiz_points_for_phase(self):
		phase_index = int(BUZZER_STATE.get("quiz_phase_index", -1))
		if phase_index < 0 or phase_index >= len(QUIZ_PHASE_POINTS):
			return 0
		return QUIZ_PHASE_POINTS[phase_index]

	def _sanitize_music_query(self, raw):
		text = str(raw or "").strip()
		if len(text) < 2:
			return None
		if len(text) > 120:
			text = text[:120]
		return text

	def _current_quiz_music_query(self):
		self._ensure_quiz_state()
		q = self._sanitize_music_query(BUZZER_STATE.get("quiz_music_query", ""))
		if not q:
			return DEEZER_POLISH_HIPHOP_QUERY
		return q

	def _pick_random_quiz_track(self):
		# Najważniejsze: losowy utwór z puli wyników Deezer dla zapytania ustawionego przez sobika.
		query = self._current_quiz_music_query()
		tracks = self._fetch_deezer_tracks(query, 50)
		if not tracks:
			return None
		random.shuffle(tracks)
		last_id = str(BUZZER_STATE.get("quiz_track_id", "")).strip()
		for track in tracks:
			track_id = str(track.get("id", "")).strip()
			if track_id and track_id != last_id:
				return track
		return tracks[0]

	def _start_quiz_round(self):
		self._ensure_quiz_state()
		for i in range(1, MAX_PLAYERS + 1):
			key = str(i)
			BUZZER_STATE["quiz_guessed_players"][key] = False
			BUZZER_STATE["quiz_artist_hint_players"][key] = False
			BUZZER_STATE["quiz_wrong_players"][key] = False
			BUZZER_STATE["quiz_wrong_guesses"][key] = []
		BUZZER_STATE["quiz_round_active"] = True
		BUZZER_STATE["quiz_phase_index"] = 0
		BUZZER_STATE["quiz_command_token"] = int(BUZZER_STATE["quiz_command_token"]) + 1
		BUZZER_STATE["quiz_command_duration_sec"] = QUIZ_PHASE_DURATIONS[0]
		BUZZER_STATE["quiz_command_issued_ms"] = self._now_ms()

	def _start_quiz_round_with_random_track(self):
		# Najważniejsze: wspólna logika losowania utworu i startu fazy 1 (reczny start i auto-start).
		random_track = self._pick_random_quiz_track()
		if random_track is None:
			return False
		BUZZER_STATE["quiz_track_id"] = str(random_track.get("id", "")).strip()
		BUZZER_STATE["quiz_preview_url"] = str(random_track.get("previewUrl", "")).strip()
		BUZZER_STATE["quiz_track_label"] = str(random_track.get("label", "")).strip()[:120]
		BUZZER_STATE["quiz_track_title"] = str(random_track.get("title", "") or "").strip()[:120]
		BUZZER_STATE["quiz_track_artist"] = str(random_track.get("artist", "") or "").strip()[:120]
		BUZZER_STATE["quiz_reveal_active"] = False
		BUZZER_STATE["quiz_reveal_seek_middle"] = False
		self._start_quiz_round()
		BUZZER_STATE["last_update_ms"] = self._now_ms()
		return True

	def _maybe_auto_start_quiz_when_all_ready(self):
		# Najważniejsze: gdy sobik ustawi typ albo ostatnia osoba kliknie Gotowy — start bez osobnego guzika.
		self._ensure_scores_and_names()
		self._ensure_quiz_state()
		if bool(BUZZER_STATE.get("quiz_reveal_active")):
			return False
		if bool(BUZZER_STATE.get("quiz_round_active")):
			return False
		if self._count_occupied_players() <= 0:
			return False
		if not self._all_occupied_ready():
			return False
		return self._start_quiz_round_with_random_track()

	def _guess_matches_deezer(self, guess, title, artist):
		raw_guess = str(guess or "").strip()
		if len(raw_guess) < 3:
			return False
		title_clean = _strip_title_feat(title)
		g = _fold_text_answer(raw_guess)
		t = _fold_text_answer(title_clean)
		a = _fold_text_answer(artist)
		if len(t) < 2 or len(a) < 2:
			return False
		if t in g and a in g:
			return True
		parts = re.split(r"\s*[-\u2013\u2014]\s*", raw_guess)
		if len(parts) >= 2:
			left = _fold_text_answer(parts[0])
			right = _fold_text_answer(parts[-1])
			pair1 = (a in left or left in a) and (t in right or right in t)
			pair2 = (t in left or left in t) and (a in right or right in a)
			if pair1 or pair2:
				return True
		toks_t = [w for w in t.split() if len(w) > 2]
		toks_a = [w for w in a.split() if len(w) > 2]
		if not toks_t:
			toks_t = [t] if t else []
		if not toks_a:
			toks_a = [a] if a else []
		ok_t = all(w in g for w in toks_t) if toks_t else (t in g)
		ok_a = all(w in g for w in toks_a) if toks_a else (a in g)
		return bool(ok_t and ok_a)

	def _artist_words_in_guess(self, guess, artist):
		g = _fold_text_answer(guess)
		a = _fold_text_answer(artist)
		if len(a) < 2:
			return False
		if a in g:
			return True
		words = [w for w in a.split() if len(w) > 2]
		if not words:
			return a in g
		return all(w in g for w in words)

	def _title_words_in_guess(self, guess, title):
		title_clean = _strip_title_feat(title)
		g = _fold_text_answer(guess)
		t = _fold_text_answer(title_clean)
		if len(t) < 2:
			return False
		if t in g:
			return True
		words = [w for w in t.split() if len(w) > 2]
		if not words:
			return t in g
		return all(w in g for w in words)

	def _artist_only_matches_round(self, guess, title, artist):
		# Najważniejsze: poprawny artysta biezacego utworu, ale bez pelnego trafienia tytulu (podswietlenie zolte).
		if self._guess_matches_deezer(guess, title, artist):
			return False
		if not self._artist_words_in_guess(guess, artist):
			return False
		return not self._title_words_in_guess(guess, title)

	def _begin_quiz_reveal(self):
		self._ensure_quiz_state()
		BUZZER_STATE["quiz_round_active"] = False
		BUZZER_STATE["quiz_reveal_active"] = True
		BUZZER_STATE["quiz_phase_index"] = -1
		BUZZER_STATE["quiz_reveal_seek_middle"] = True
		BUZZER_STATE["quiz_command_token"] = int(BUZZER_STATE["quiz_command_token"]) + 1
		BUZZER_STATE["quiz_command_duration_sec"] = QUIZ_REVEAL_CLIP_SEC
		BUZZER_STATE["quiz_command_issued_ms"] = self._now_ms()
		for i in range(1, MAX_PLAYERS + 1):
			# Najważniejsze: po ujawnieniu trzeba znowu zaznaczyc Gotowy przed kolejna piosenka.
			BUZZER_STATE["quiz_ready_players"][str(i)] = False
			BUZZER_STATE["quiz_artist_hint_players"][str(i)] = False
		BUZZER_STATE["last_update_ms"] = self._now_ms()

	def _advance_quiz_phase(self):
		self._ensure_quiz_state()
		current_index = int(BUZZER_STATE.get("quiz_phase_index", -1))
		next_index = current_index + 1
		if next_index >= len(QUIZ_PHASE_DURATIONS):
			return False
		BUZZER_STATE["quiz_phase_index"] = next_index
		BUZZER_STATE["quiz_command_token"] = int(BUZZER_STATE["quiz_command_token"]) + 1
		BUZZER_STATE["quiz_command_duration_sec"] = QUIZ_PHASE_DURATIONS[next_index]
		BUZZER_STATE["quiz_command_issued_ms"] = self._now_ms()
		return True

	def _public_buzzer_state(self):
		self._ensure_scores_and_names()
		self._ensure_quiz_state()
		self._ensure_player_avatars()
		# Najważniejsze: tytul/artysta tylko w fazie ujawnienia (po rundzie), nie podczas zgadywania.
		show_quiz_answer = bool(BUZZER_STATE.get("quiz_reveal_active"))
		ql = BUZZER_STATE.get("quiz_track_label", "") if show_quiz_answer else ""
		qt = BUZZER_STATE.get("quiz_track_title", "") if show_quiz_answer else ""
		qa = BUZZER_STATE.get("quiz_track_artist", "") if show_quiz_answer else ""
		return {
			"roundId": BUZZER_STATE["round_id"],
			"roundStartedMs": BUZZER_STATE["round_started_ms"],
			"winner": BUZZER_STATE["winner"],
			"winnerName": BUZZER_STATE["winner_name"],
			"winnerTimeMs": BUZZER_STATE["winner_time_ms"],
			"videoUrl": BUZZER_STATE["video_url"],
			"videoPaused": BUZZER_STATE["video_paused"],
			"videoTimeSec": BUZZER_STATE["video_time_sec"],
			"quizPreviewUrl": BUZZER_STATE["quiz_preview_url"],
			"quizTrackLabel": ql,
			"quizTrackTitle": qt,
			"quizTrackArtist": qa,
			"quizTrackId": BUZZER_STATE["quiz_track_id"],
			"quizMusicQuery": self._current_quiz_music_query(),
			"quizRevealActive": bool(BUZZER_STATE.get("quiz_reveal_active")),
			"quizRevealSeekMiddle": bool(BUZZER_STATE.get("quiz_reveal_seek_middle")),
			"quizCommandToken": BUZZER_STATE["quiz_command_token"],
			"quizCommandDurationSec": BUZZER_STATE["quiz_command_duration_sec"],
			"quizCommandIssuedMs": BUZZER_STATE["quiz_command_issued_ms"],
			"quizRoundActive": BUZZER_STATE["quiz_round_active"],
			"quizPhaseIndex": BUZZER_STATE["quiz_phase_index"],
			"quizPhaseDurations": QUIZ_PHASE_DURATIONS,
			"quizPhasePoints": QUIZ_PHASE_POINTS,
			"quizGuessedPlayers": BUZZER_STATE["quiz_guessed_players"],
			"quizArtistHintPlayers": BUZZER_STATE["quiz_artist_hint_players"],
			"quizWrongPlayers": BUZZER_STATE["quiz_wrong_players"],
			"quizWrongGuesses": BUZZER_STATE["quiz_wrong_guesses"],
			"quizGuessedCount": self._count_guessed_players(),
			"quizReadyPlayers": BUZZER_STATE["quiz_ready_players"],
			"quizReadyCount": self._count_ready_players(),
			"quizOccupiedCount": self._count_occupied_players(),
			"videoControllerName": VIDEO_CONTROLLER_NAME,
			"scores": BUZZER_STATE["scores"],
			"playerNames": BUZZER_STATE["player_names"],
			"playerAvatars": BUZZER_STATE["player_avatars"],
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
		if parsed.path == "/api/deezer-search":
			self.handle_deezer_search_get(parsed.query)
			return
		if parsed.path == "/api/deezer-polish-hiphop":
			self.handle_deezer_polish_hiphop_get(parsed.query)
			return
		if parsed.path == "/api/avatar-presets":
			self.handle_avatar_presets_get()
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
		if parsed.path == "/api/buzzer-join-auto":
			self.handle_buzzer_join_auto_post()
			return
		if parsed.path == "/api/buzzer-video-sync":
			self.handle_buzzer_video_sync_post()
			return
		if parsed.path == "/api/buzzer-leave":
			self.handle_buzzer_leave_post()
			return
		if parsed.path == "/api/buzzer-avatar":
			self.handle_buzzer_avatar_post()
			return
		if parsed.path == "/api/quiz-music-type":
			self.handle_quiz_music_type_post()
			return
		if parsed.path == "/api/quiz-track":
			self.handle_quiz_track_post()
			return
		if parsed.path == "/api/quiz-play":
			self.handle_quiz_play_post()
			return
		if parsed.path == "/api/quiz-ready":
			self.handle_quiz_ready_post()
			return
		if parsed.path == "/api/quiz-start-round":
			self.handle_quiz_start_round_post()
			return
		if parsed.path == "/api/quiz-next-phase":
			self.handle_quiz_next_phase_post()
			return
		if parsed.path == "/api/quiz-guess":
			self.handle_quiz_guess_post()
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
			name = str(parsed.get("name", "")).strip()
			if not self._is_video_controller(name):
				self.json_response({"error": "Only sobik can set video"}, 403)
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
			name = self._sanitize_name(parsed.get("name"), "")
			if not self._is_video_controller(name):
				self.json_response({"error": "Only sobik can change scores"}, 403)
				return
			target_player = self._sanitize_player(parsed.get("targetPlayer"))
			if target_player is None:
				self.json_response({"error": "Invalid target player number"}, 400)
				return
			delta = self._sanitize_delta(parsed.get("delta"))
			if delta is None:
				self.json_response({"error": "Invalid delta"}, 400)
				return
			key = str(target_player)
			# Najważniejsze: punkty zapisujemy globalnie na serwerze, żeby kazdy klient widzial ten sam ranking.
			BUZZER_STATE["scores"][key] = int(BUZZER_STATE["scores"].get(key, 0)) + delta
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

	def handle_buzzer_join_auto_post(self):
		try:
			self._ensure_round_started()
			self._ensure_scores_and_names()
			self._ensure_quiz_state()
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			raw_name = str(parsed.get("name", "")).strip()
			if not raw_name:
				self.json_response({"error": "Name is required"}, 400)
				return
			player_name = self._sanitize_name(raw_name, raw_name)
			if self._is_video_controller(player_name):
				password = parsed.get("password")
				if not self._is_valid_video_controller_password(password):
					self.json_response({"error": "Invalid admin password"}, 403)
					return
			existing_player = self._find_player_by_name(player_name)
			if existing_player is not None:
				assigned_player = existing_player
			else:
				assigned_player = self._pick_free_player()
			BUZZER_STATE["player_names"][str(assigned_player)] = player_name
			BUZZER_STATE["quiz_ready_players"][str(assigned_player)] = False
			BUZZER_STATE["quiz_guessed_players"][str(assigned_player)] = False
			BUZZER_STATE["quiz_artist_hint_players"][str(assigned_player)] = False
			BUZZER_STATE["quiz_wrong_players"][str(assigned_player)] = False
			BUZZER_STATE["quiz_wrong_guesses"][str(assigned_player)] = []
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			self.json_response(
				{
					"ok": True,
					"player": assigned_player,
					"state": self._public_buzzer_state(),
				},
				200,
			)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_buzzer_leave_post(self):
		try:
			self._ensure_round_started()
			self._ensure_scores_and_names()
			self._ensure_quiz_state()
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
			name = self._sanitize_name(parsed.get("name"), _default_name_for_player(player))
			key = str(player)
			current_name = BUZZER_STATE["player_names"].get(key, _default_name_for_player(player))
			if not self._same_name(current_name, name):
				self.json_response({"ok": True, "released": False, "state": self._public_buzzer_state()}, 200)
				return
			# Najważniejsze: przy wyjsciu karty zwalniamy slot gracza, zeby kolejna osoba mogla go zajac.
			BUZZER_STATE["player_names"][key] = _default_name_for_player(player)
			BUZZER_STATE["quiz_ready_players"][key] = False
			BUZZER_STATE["quiz_guessed_players"][key] = False
			BUZZER_STATE["quiz_artist_hint_players"][key] = False
			BUZZER_STATE["quiz_wrong_players"][key] = False
			BUZZER_STATE["quiz_wrong_guesses"][key] = []
			self._delete_legacy_uploaded_avatar_file(key)
			self._ensure_player_avatars()
			BUZZER_STATE["player_avatars"][key] = ""
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			self.json_response({"ok": True, "released": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_buzzer_avatar_post(self):
		try:
			self._ensure_round_started()
			self._ensure_scores_and_names()
			self._ensure_player_avatars()
			ensure_dirs()
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
			name = self._sanitize_name(parsed.get("name"), _default_name_for_player(player))
			key = str(player)
			current_name = BUZZER_STATE["player_names"].get(key, _default_name_for_player(player))
			if not self._same_name(current_name, name):
				self.json_response({"error": "Player identity mismatch"}, 403)
				return
			if bool(parsed.get("clear")):
				self._delete_legacy_uploaded_avatar_file(key)
				BUZZER_STATE["player_avatars"][key] = ""
				BUZZER_STATE["last_update_ms"] = self._now_ms()
				self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
				return
			filename = self._sanitize_avatar_preset_filename(parsed.get("preset"))
			if not filename:
				self.json_response({"error": "Niepoprawny lub brak pliku w avatar_presets"}, 400)
				return
			public_url = self._avatar_preset_public_url(filename)
			if self._is_avatar_preset_taken(public_url, key):
				self.json_response({"error": "Ten avatar jest juz zajety przez innego gracza"}, 400)
				return
			self._delete_legacy_uploaded_avatar_file(key)
			BUZZER_STATE["player_avatars"][key] = public_url
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_avatar_presets_get(self):
		try:
			ensure_dirs()
			out = []
			if os.path.isdir(AVATAR_PRESET_DIR):
				for name in sorted(os.listdir(AVATAR_PRESET_DIR)):
					if name.startswith("."):
						continue
					low = name.lower()
					if not (
						low.endswith(".png")
						or low.endswith(".jpg")
						or low.endswith(".jpeg")
						or low.endswith(".webp")
						or low.endswith(".gif")
					):
						continue
					out.append({"id": name, "url": self._avatar_preset_public_url(name)})
			self.json_response({"presets": out}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def _get_limit_from_query(self, query_text, default_limit):
		parsed_query = parse_qs(query_text or "")
		limit_raw = str((parsed_query.get("limit") or [str(default_limit)])[0]).strip()
		try:
			limit = int(limit_raw)
		except Exception:
			limit = default_limit
		if limit < 1:
			limit = 1
		if limit > 50:
			limit = 50
		return limit

	def _fetch_deezer_url_json(self, url):
		req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
		with urlopen(req, timeout=8) as response:
			raw = response.read().decode("utf-8", errors="replace")
		return json.loads(raw)

	def _deezer_track_to_suggest_dict(self, item):
		preview = str(item.get("preview") or "").strip()
		if not preview:
			return None
		title = str(item.get("title") or "").strip()
		artist_name = str((item.get("artist") or {}).get("name") or "").strip()
		label = title
		if artist_name:
			label = title + " - " + artist_name
		return {
			"id": str(item.get("id") or ""),
			"label": label[:120],
			"previewUrl": preview,
			"title": title[:80],
			"artist": artist_name[:80],
		}

	def _deezer_track_involves_artist_id(self, item, artist_id):
		try:
			want = int(artist_id)
		except Exception:
			return False
		main = item.get("artist") or {}
		try:
			if int(main.get("id") or 0) == want:
				return True
		except Exception:
			pass
		for c in item.get("contributors") or []:
			try:
				if int(c.get("id") or 0) == want:
					return True
			except Exception:
				continue
		return False

	def _deezer_artist_name_matches_query(self, query, artist_name):
		q = _fold_text_answer(query)
		a = _fold_text_answer(artist_name)
		if not q or not a:
			return False
		if q == a:
			return True
		if a.startswith(q) or q.startswith(a):
			return True
		if " " not in q and q in a:
			return True
		return False

	def _deezer_try_resolve_artist_id(self, term):
		t = term.strip()
		if not t or " - " in t:
			return None
		words = t.split()
		if len(words) > 2:
			return None
		url = "https://api.deezer.com/search/artist?" + urlencode({"q": t, "limit": 8})
		try:
			parsed = self._fetch_deezer_url_json(url)
		except Exception:
			return None
		data = parsed.get("data") or []
		if not data:
			return None
		first = data[0]
		name = str(first.get("name") or "").strip()
		if not self._deezer_artist_name_matches_query(t, name):
			return None
		try:
			return int(first.get("id") or 0)
		except Exception:
			return None

	def _fetch_deezer_tracks_for_artist_id(self, artist_id, term, limit):
		out = []
		seen = set()
		try:
			aid = int(artist_id)
		except Exception:
			return []

		def push_item(item):
			tid = str(item.get("id") or "").strip()
			if not tid or tid in seen:
				return
			if not self._deezer_track_involves_artist_id(item, aid):
				return
			rec = self._deezer_track_to_suggest_dict(item)
			if not rec:
				return
			seen.add(tid)
			out.append(rec)

		try:
			top_url = "https://api.deezer.com/artist/%d/top?limit=50" % aid
			top_parsed = self._fetch_deezer_url_json(top_url)
			for item in top_parsed.get("data") or []:
				push_item(item)
				if len(out) >= limit:
					return out[:limit]
		except Exception:
			pass
		try:
			st_lim = min(100, max(50, limit * 4))
			search_url = "https://api.deezer.com/search/track?" + urlencode({"q": term, "limit": st_lim})
			search_parsed = self._fetch_deezer_url_json(search_url)
			for item in search_parsed.get("data") or []:
				push_item(item)
				if len(out) >= limit:
					break
		except Exception:
			pass
		return out[:limit]

	def _fetch_deezer_tracks(self, term, limit):
		url = "https://api.deezer.com/search?" + urlencode({"q": term, "limit": limit})
		try:
			parsed = self._fetch_deezer_url_json(url)
		except Exception:
			return []
		items = parsed.get("data", [])
		tracks = []
		for item in items:
			rec = self._deezer_track_to_suggest_dict(item)
			if rec:
				tracks.append(rec)
		return tracks

	def handle_deezer_search_get(self, query_text):
		try:
			parsed_query = parse_qs(query_text or "")
			term = str((parsed_query.get("q") or [""])[0]).strip()
			if not term:
				self.json_response({"tracks": []}, 200)
				return
			limit = self._get_limit_from_query(query_text, 15)
			# Najważniejsze: sam artysta (np. „sobel”) → tylko jego utwory i featy (contributors na Deezer).
			artist_id = self._deezer_try_resolve_artist_id(term)
			if artist_id is not None:
				tracks = self._fetch_deezer_tracks_for_artist_id(artist_id, term, limit)
				if tracks:
					self.json_response({"tracks": tracks}, 200)
					return
			tracks = self._fetch_deezer_tracks(term, limit)
			self.json_response({"tracks": tracks}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_deezer_polish_hiphop_get(self, query_text):
		try:
			limit = self._get_limit_from_query(query_text, 30)
			tracks = self._fetch_deezer_tracks(DEEZER_POLISH_HIPHOP_QUERY, max(limit * 2, 30))
			random.shuffle(tracks)
			self.json_response({"tracks": tracks[:limit]}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_music_type_post(self):
		try:
			self._ensure_round_started()
			self._ensure_quiz_state()
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			name = self._sanitize_name(parsed.get("name"), "")
			if not self._is_video_controller(name):
				self.json_response({"error": "Only sobik can set quiz music type"}, 403)
				return
			query = self._sanitize_music_query(parsed.get("query"))
			if not query:
				self.json_response({"error": "Invalid query (2-120 chars)"}, 400)
				return
			BUZZER_STATE["quiz_music_query"] = query
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			self._maybe_auto_start_quiz_when_all_ready()
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_track_post(self):
		try:
			self._ensure_round_started()
			self._ensure_quiz_state()
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			name = self._sanitize_name(parsed.get("name"), "")
			if not self._is_video_controller(name):
				self.json_response({"error": "Only sobik can set quiz track"}, 403)
				return
			preview_url = str(parsed.get("previewUrl", "")).strip()
			if not preview_url:
				self.json_response({"error": "Missing previewUrl"}, 400)
				return
			label = str(parsed.get("label", "")).strip()
			BUZZER_STATE["quiz_preview_url"] = preview_url
			BUZZER_STATE["quiz_track_label"] = label[:120]
			BUZZER_STATE["quiz_track_id"] = str(parsed.get("trackId", "")).strip()
			BUZZER_STATE["quiz_round_active"] = False
			BUZZER_STATE["quiz_phase_index"] = -1
			BUZZER_STATE["quiz_command_duration_sec"] = 0
			BUZZER_STATE["quiz_command_issued_ms"] = 0
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_play_post(self):
		try:
			self._ensure_round_started()
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			name = self._sanitize_name(parsed.get("name"), "")
			if not self._is_video_controller(name):
				self.json_response({"error": "Only sobik can play quiz clip"}, 403)
				return
			if not str(BUZZER_STATE.get("quiz_preview_url", "")).strip():
				self.json_response({"error": "No quiz track selected"}, 400)
				return
			duration_sec = self._sanitize_duration_sec(parsed.get("durationSec"))
			if duration_sec is None:
				self.json_response({"error": "Invalid durationSec"}, 400)
				return
			now_ms = self._now_ms()
			# Najważniejsze: token komendy wymusza odtworzenie nowego klipu u wszystkich klientów.
			BUZZER_STATE["quiz_command_token"] = int(BUZZER_STATE["quiz_command_token"]) + 1
			BUZZER_STATE["quiz_command_duration_sec"] = duration_sec
			BUZZER_STATE["quiz_command_issued_ms"] = now_ms
			BUZZER_STATE["last_update_ms"] = now_ms
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_ready_post(self):
		try:
			self._ensure_round_started()
			self._ensure_scores_and_names()
			self._ensure_quiz_state()
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
			name = self._sanitize_name(parsed.get("name"), _default_name_for_player(player))
			key = str(player)
			current_name = BUZZER_STATE["player_names"].get(key, _default_name_for_player(player))
			if not self._same_name(current_name, name):
				self.json_response({"error": "Player identity mismatch"}, 403)
				return
			ready = self._sanitize_ready(parsed.get("ready"))
			if ready is None:
				self.json_response({"error": "Invalid ready value"}, 400)
				return
			BUZZER_STATE["quiz_ready_players"][key] = ready
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			self._maybe_auto_start_quiz_when_all_ready()
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_start_round_post(self):
		try:
			self._ensure_round_started()
			self._ensure_scores_and_names()
			self._ensure_quiz_state()
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			name = self._sanitize_name(parsed.get("name"), "")
			if not self._is_video_controller(name):
				self.json_response({"error": "Only sobik can start quiz round"}, 403)
				return
			if not self._all_occupied_ready():
				self.json_response({"error": "Not all players are ready"}, 400)
				return
			if not self._start_quiz_round_with_random_track():
				self.json_response({"error": "No Deezer tracks available"}, 500)
				return
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_next_phase_post(self):
		try:
			self._ensure_round_started()
			self._ensure_scores_and_names()
			self._ensure_quiz_state()
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			name = self._sanitize_name(parsed.get("name"), "")
			if not self._is_video_controller(name):
				self.json_response({"error": "Only sobik can advance quiz phase"}, 403)
				return
			if bool(BUZZER_STATE.get("quiz_reveal_active")):
				self.json_response({"error": "Reveal is active"}, 400)
				return
			if not bool(BUZZER_STATE.get("quiz_round_active")):
				self.json_response({"error": "Quiz round is not active"}, 400)
				return
			current_index = int(BUZZER_STATE.get("quiz_phase_index", -1))
			last_idx = len(QUIZ_PHASE_DURATIONS) - 1
			if current_index >= last_idx:
				# Najważniejsze: po ostatniej fazie (16s) przechodzimy do ~10s z srodka preview + podpis utworu.
				self._begin_quiz_reveal()
				self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
				return
			if self._count_guessed_players() >= self._count_occupied_players():
				self.json_response({"error": "All active players already guessed"}, 400)
				return
			if not self._advance_quiz_phase():
				self.json_response({"error": "Already at last phase"}, 400)
				return
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_guess_post(self):
		try:
			self._ensure_round_started()
			self._ensure_scores_and_names()
			self._ensure_quiz_state()
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
			name = self._sanitize_name(parsed.get("name"), _default_name_for_player(player))
			key = str(player)
			current_name = BUZZER_STATE["player_names"].get(key, _default_name_for_player(player))
			if not self._same_name(current_name, name):
				self.json_response({"error": "Player identity mismatch"}, 403)
				return
			if not bool(BUZZER_STATE.get("quiz_round_active")):
				self.json_response({"error": "Quiz round is not active"}, 400)
				return
			if bool(BUZZER_STATE["quiz_guessed_players"].get(key)):
				self.json_response({"ok": True, "alreadyGuessed": True, "state": self._public_buzzer_state()}, 200)
				return
			if bool(BUZZER_STATE["quiz_wrong_players"].get(key)):
				self.json_response({"ok": True, "alreadyEliminated": True, "state": self._public_buzzer_state()}, 200)
				return
			guess = str(parsed.get("guess", "")).strip()
			if len(guess) < 3:
				self.json_response({"error": "Za krotka odpowiedz"}, 400)
				return
			title = str(BUZZER_STATE.get("quiz_track_title", "") or "")
			artist = str(BUZZER_STATE.get("quiz_track_artist", "") or "")
			if self._guess_matches_deezer(guess, title, artist):
				BUZZER_STATE["quiz_artist_hint_players"][key] = False
				BUZZER_STATE["quiz_guessed_players"][key] = True
				points = self._quiz_points_for_phase()
				BUZZER_STATE["scores"][key] = int(BUZZER_STATE["scores"].get(key, 0)) + points
				BUZZER_STATE["last_update_ms"] = self._now_ms()
				if self._count_guessed_players() >= self._count_occupied_players():
					self._begin_quiz_reveal()
				self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
				return
			if self._artist_only_matches_round(guess, title, artist):
				BUZZER_STATE["quiz_artist_hint_players"][key] = True
				BUZZER_STATE["last_update_ms"] = self._now_ms()
				self.json_response({"ok": True, "artistHintOnly": True, "state": self._public_buzzer_state()}, 200)
				return
			BUZZER_STATE["quiz_artist_hint_players"][key] = False
			BUZZER_STATE["quiz_wrong_players"][key] = True
			prev = BUZZER_STATE["quiz_wrong_guesses"].get(key)
			if not isinstance(prev, list):
				prev = []
				BUZZER_STATE["quiz_wrong_guesses"][key] = prev
			prev.append(guess[:200])
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			self.json_response({"ok": True, "guessWrong": True, "state": self._public_buzzer_state()}, 200)
			return
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
