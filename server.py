try:
	import cgi
except Exception:
	cgi = None
import json
import os
import random
import re
import secrets
import ssl
import sys
import threading
import time
import unicodedata
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CMR_DIR = os.path.join(DATA_DIR, "cmr")
ORDERS_FILE = os.path.join(DATA_DIR, "driver_orders.json")
QUIZ_SOLO_LEADERBOARD_FILE = os.path.join(DATA_DIR, "quiz_solo_leaderboard.json")
SOLO_QUIZ_SESSIONS = {}
SOLO_QUIZ_LOCK = threading.Lock()
BUZZER_QUIZ_LOCK = threading.Lock()
SOLO_SESSION_TTL_MS = 6 * 60 * 60 * 1000
AVATAR_DIR = os.path.join(DATA_DIR, "avatars")
AVATAR_PRESET_DIR = os.path.join(BASE_DIR, "avatar_presets")
MAX_PLAYERS = 8
VIDEO_CONTROLLER_NAME = "sobik"
VIDEO_CONTROLLER_PASSWORD = "lol123ASD@"
DEEZER_POLISH_HIPHOP_QUERY = "polski hip hop"
QUIZ_MUSIC_FIXED_POLISH = "polska_muzyka_wylacznie"
QUIZ_MUSIC_FIXED_POLISH_LABEL = ""
QUIZ_POLISH_ONLY_FALLBACK_TERMS = (
	"polski rap",
	"polski hip hop",
	"trap polska",
	"polski pop",
	"2024 polska muzyka",
	"2023 polska muzyka",
	"rap polska",
	"hip hop polska",
	"drill polska",
	"polska muzyka",
	"lista przebojów polska",
)
QUIZ_HIPHOP_YEAR_RANGE_QUERY = "hiphop_years_2022_2026"
QUIZ_HIPHOP_YEAR_QUERY_LEGACY = "hip hop [2022-2026]"
QUIZ_HIPHOP_YEAR_MIN = 2022
QUIZ_HIPHOP_YEAR_MAX = 2026
# Najważniejsze: tylko polska muzyka w quizie — zakres lat (gdy Deezer podaje rok wydania).
QUIZ_MODERN_POP_YEAR_MIN = 2012
QUIZ_MODERN_POP_YEAR_MAX = 2026
# Najważniejsze: podfoldowane igły — odcinają zachodnią muzykę poważną / import z PL-ISRC (np. Bartók).
QUIZ_BLOCK_FOREIGN_CLASSICAL_NEEDLES = (
	"bartok",
	"bela bartok",
	"beethoven",
	"mozart",
	"vivaldi",
	"tchaikovsky",
	"tchaikov",
	"mussorgsky",
	"debussy",
	"brahms",
	"dvorak",
	"mahler",
	"wagner",
	"rachmanin",
	"stravinsky",
	"orchester",
	"roumain",
	"roumanie",
	"populaires roumain",
	"danses populaires",
	"philharmonia",
)
DEEZER_HTTP_UA = (
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
	"(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)
QUIZ_POLISH_DIVERSE_DEEZER_QUERIES = (
	"polski rap",
	"polski hip hop",
	"trap polska",
	"rap polska",
	"hip hop polska",
	"drill polska",
	"polski pop",
	"2025 polska muzyka",
	"2024 polska muzyka",
	"2023 polska muzyka",
	"polski rock",
	"piosenki po polsku",
	"muzyka polska",
	"polska ballada",
	"polski folk rock",
)
# Najważniejsze: pula quizu — wyłącznie utwory powiązane z tą listą (Deezer search po nazwie + dopasowanie wykonawcy).
QUIZ_POOL_WHITELIST_ARTISTS = (
	"Fagata",
	"Mata",
	"Szpaku",
	"Sobel",
	"Quebo",
	"Quebonafide",
	"miu",
	"Malik Montana",
	"OKI",
	"White 2115",
	"SB Maffija",
	"SVMIR",
	"Sentino",
	"Kaz Bałagane",
	"Gibbs",
	"Pezet",
	"Bambi",
	"Young Leosia",
	"Dzarma",
	"Margaret",
	"Rubens Babicz",
	"Row Babicze",
	"Kizo",
	"Krzysztof Krafczyk",
	"Sanah",
	"Dawid Podsiadło",
	"Bedoes",
	"Kabe",
	"Kinny Zimmer",
	"Fukaj",
	"Chivas",
	"Skolim",
	"Modelki",
	"Żabson",
	"Koder",
	"Vito Bambino",
	"PRO8L3M",
	"Young Igi",
	"Wac To Ja",
	"Otsochodzi",
	"Blacha 2115",
	"Kuqe 2115",
	"Avi",
	"Reto",
	"Kayah",
	"Bungee",
	"Smolasty",
	"Wersow",
	"Guzior",
	"Dajczman",
)
QUIZ_MODERN_POOL_ARTIST_SEEDS = QUIZ_POOL_WHITELIST_ARTISTS
POLISH_SCENE_ARTIST_SEEDS = (
	"Sanah",
	"Dawid Podsiadło",
	"Maanam",
	"Lady Pank",
	"Wilki",
	"Myslovitz",
	"Enej",
	"Krzysztof Zalewski",
	"Mrozu",
	"Natalia Szroeder",
	"Czesław Niemen",
	"Perfect",
	"Dżem",
	"Szpaku",
	"Sobel",
	"OKI",
	"Bedoes",
	"Mata",
	"Young Leosia",
	"Quebonafide",
	"Kukon",
	"Taco Hemingway",
	"Białas",
	"Malach",
	"Zeams",
	"Gibbs",
	"Schafter",
	"White 2115",
	"Hades",
	"PRO8L3M",
	"Dawid Obiekt",
	"Pezet",
	"Żabson",
	"Skolim",
	"Modelki",
	"Koder",
	"Vito Bambino",
	"Young Igi",
	"Wac To Ja",
	"Otsochodzi",
	"Blacha 2115",
	"Kuqe 2115",
	"Avi",
	"Reto",
	"Kayah",
	"Bungee",
	"Smolasty",
	"Wersow",
	"Guzior",
	"Dajczman",
)
# Najważniejsze: długości kolejnych tierów zgadywania (zawsze od początku preview po stronie klienta — intro/bit, potem więcej od startu).
QUIZ_PHASE_DURATIONS = [0.5, 2, 4, 6]
QUIZ_PHASE_POINTS = [4, 3, 2, 1]
QUIZ_REVEAL_CLIP_SEC = 10
QUIZ_AFTER_REVEAL_NEXT_SEC = 1.0
QUIZ_MAX_SKIPS_PER_ROUND = 4
QUIZ_POOL_CACHE_TTL_MS = 40 * 60 * 1000
QUIZ_POOL_BUILD_MAX_DEEZER_HTTP = 14
# Najważniejsze: najpierw kilka zapytań z sortem RANKING_DESC (popularne na Deezerze).
QUIZ_POOL_POPULAR_LEADING_MAX_HTTP = 6
# Najważniejsze: żeby jeden artysta (np. z jednego wyniku search) nie zajmował całej puli.
QUIZ_POOL_MAX_TRACKS_PER_ARTIST = 4
# Najważniejsze: po złożeniu puli zostaje tylko N utworów z najwyższym rank Deezera (nie „lista Billboard”, tylko przecięcie naszej puli).
QUIZ_POOL_TOP_BY_RANK_COUNT = 30
QUIZ_POLISH_POPULAR_LEADING_TERMS = (
	"polski rap",
	"polski hip hop",
	"trap polska",
	"polski pop",
	"2024 polska muzyka",
	"polski rock",
)
QUIZ_POOL_SCENE_MAX_ARTISTS = 10
_DEEZER_LAST_FETCH_ERR = ""
_QUIZ_TRACK_POOL_CACHE = None
_QUIZ_TRACK_POOL_CACHE_MS = 0

_POLISH_DIACRITICS_RE = re.compile(
	r"[\u0105\u0107\u0119\u0142\u0144\u00f3\u015b\u017a\u017c\u0104\u0106\u0118\u0141\u0143\u00d3\u015a\u0179\u017b]"
)

SEARCH_POLISH_NAME_HINTS = (
	"Malik Montana",
	"Męskie Granie",
	"Męskie Granie Orkiestra",
	"Sanah",
	"Dawid Podsiadło",
	"Żabson",
	"Quebonafide",
	"Białas",
)


def _deezer_ssl_context():
	# Najważniejsze: na niektórych Windowsach domyślny magazyn certów bywa zły — certifi pomaga przy SSL do api.deezer.com.
	try:
		import certifi

		return ssl.create_default_context(cafile=certifi.where())
	except Exception:
		return ssl.create_default_context()


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
	"quiz_music_query": QUIZ_MUSIC_FIXED_POLISH,
	"quiz_reveal_active": False,
	"quiz_reveal_seek_middle": False,
	"quiz_command_token": 0,
	"quiz_command_duration_sec": 0,
	"quiz_command_issued_ms": 0,
	"quiz_round_active": False,
	"quiz_phase_index": -1,
	"quiz_listen_phase": {},
	"quiz_listen_token": {},
	"quiz_guessed_players": {},
	"quiz_artist_hint_players": {},
	"quiz_wrong_players": {},
	"quiz_wrong_guesses": {},
	"quiz_guess_history": {},
	"quiz_skips_used": {},
	"quiz_round_limit": 0,
	"quiz_rounds_played": 0,
	"quiz_used_track_ids": [],
	"quiz_session_id": 1,
	"quiz_ready_players": {},
	"scores": _default_scores(),
	"player_names": _default_player_names(),
	"player_avatars": _default_player_avatars(),
	"last_update_ms": 0,
	"quiz_reveal_pending_auto_next": False,
}

_QUIZ_AUTO_NEXT_TIMER = None


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
		if isinstance(value, int) and value in (0, 1):
			return bool(value)
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

	def _reset_full_quiz_session(self):
		# Najważniejsze: zeruje punkty, limit rund, „już grane” utwory i stan quizu — nowy quizSessionId zsynchronizuje klientów (tokeny odsłuchu).
		cancel_quiz_auto_next_timer()
		self._ensure_quiz_state()
		self._ensure_scores_and_names()
		for i in range(1, MAX_PLAYERS + 1):
			key = str(i)
			BUZZER_STATE["scores"][key] = 0
		BUZZER_STATE["quiz_round_limit"] = 0
		BUZZER_STATE["quiz_rounds_played"] = 0
		qu = BUZZER_STATE.get("quiz_used_track_ids")
		if not isinstance(qu, list):
			BUZZER_STATE["quiz_used_track_ids"] = []
		else:
			qu[:] = []
		BUZZER_STATE["quiz_reveal_pending_auto_next"] = False
		BUZZER_STATE["quiz_session_id"] = int(BUZZER_STATE.get("quiz_session_id") or 1) + 1
		self._new_round()
		BUZZER_STATE["last_update_ms"] = self._now_ms()

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
		cancel_quiz_auto_next_timer()
		self._ensure_quiz_state()
		for i in range(1, MAX_PLAYERS + 1):
			# Najważniejsze: po resecie kolejna runda wymaga ponownego Gotowy (unikamy podwójnego autostartu).
			BUZZER_STATE["quiz_ready_players"][str(i)] = False
			BUZZER_STATE["quiz_artist_hint_players"][str(i)] = False
			BUZZER_STATE["quiz_guessed_players"][str(i)] = False
			BUZZER_STATE["quiz_wrong_players"][str(i)] = False
			BUZZER_STATE["quiz_wrong_guesses"][str(i)] = []
			BUZZER_STATE["quiz_guess_history"][str(i)] = []
			BUZZER_STATE["quiz_listen_phase"][str(i)] = 0
			BUZZER_STATE["quiz_listen_token"][str(i)] = 0
			BUZZER_STATE["quiz_skips_used"][str(i)] = 0

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

	def _assign_random_avatar_for_player_key(self, key):
		# Najważniejsze: przy zajęciu slotu — losowy awatar z avatar_presets (gdy pole puste; bez kolizji z innymi zajętymi).
		self._ensure_player_avatars()
		k = str(key)
		cur = str(BUZZER_STATE["player_avatars"].get(k, "")).strip()
		if cur:
			return
		ensure_dirs()
		all_presets = []
		if os.path.isdir(AVATAR_PRESET_DIR):
			for name in os.listdir(AVATAR_PRESET_DIR):
				fn = self._sanitize_avatar_preset_filename(name)
				if fn:
					all_presets.append(fn)
		if not all_presets:
			return
		random.shuffle(all_presets)
		for fn in all_presets:
			public_url = self._avatar_preset_public_url(fn)
			if not self._is_avatar_preset_taken(public_url, k):
				self._delete_legacy_uploaded_avatar_file(k)
				BUZZER_STATE["player_avatars"][k] = public_url
				return
		fn = random.choice(all_presets)
		self._delete_legacy_uploaded_avatar_file(k)
		BUZZER_STATE["player_avatars"][k] = self._avatar_preset_public_url(fn)

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
		# Najważniejsze: jedna kategoria serwera — wylacznie polska muzyka (nadpisuje stare zapisy stanu).
		BUZZER_STATE["quiz_music_query"] = QUIZ_MUSIC_FIXED_POLISH
		if "quiz_reveal_active" not in BUZZER_STATE:
			BUZZER_STATE["quiz_reveal_active"] = False
		if "quiz_reveal_seek_middle" not in BUZZER_STATE:
			BUZZER_STATE["quiz_reveal_seek_middle"] = False
		if "quiz_reveal_pending_auto_next" not in BUZZER_STATE:
			BUZZER_STATE["quiz_reveal_pending_auto_next"] = False
		lp = BUZZER_STATE.get("quiz_listen_phase")
		if not isinstance(lp, dict):
			BUZZER_STATE["quiz_listen_phase"] = {}
			lp = BUZZER_STATE["quiz_listen_phase"]
		ltok = BUZZER_STATE.get("quiz_listen_token")
		if not isinstance(ltok, dict):
			BUZZER_STATE["quiz_listen_token"] = {}
			ltok = BUZZER_STATE["quiz_listen_token"]
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
		gh = BUZZER_STATE.get("quiz_guess_history")
		if not isinstance(gh, dict):
			BUZZER_STATE["quiz_guess_history"] = {}
			gh = BUZZER_STATE["quiz_guess_history"]
		for i in range(1, MAX_PLAYERS + 1):
			key = str(i)
			if key not in wrong:
				wrong[key] = False
			if key not in wg or not isinstance(wg.get(key), list):
				wg[key] = []
			if key not in gh or not isinstance(gh.get(key), list):
				gh[key] = []
			if key not in lp:
				lp[key] = 0
			if key not in ltok:
				ltok[key] = 0
		su = BUZZER_STATE.get("quiz_skips_used")
		if not isinstance(su, dict):
			BUZZER_STATE["quiz_skips_used"] = {}
			su = BUZZER_STATE["quiz_skips_used"]
		for i in range(1, MAX_PLAYERS + 1):
			key = str(i)
			if key not in su:
				su[key] = 0
		if "quiz_round_limit" not in BUZZER_STATE:
			BUZZER_STATE["quiz_round_limit"] = 0
		if "quiz_rounds_played" not in BUZZER_STATE:
			BUZZER_STATE["quiz_rounds_played"] = 0
		if "quiz_session_id" not in BUZZER_STATE:
			BUZZER_STATE["quiz_session_id"] = 1
		qu = BUZZER_STATE.get("quiz_used_track_ids")
		if not isinstance(qu, list):
			BUZZER_STATE["quiz_used_track_ids"] = []
			qu = BUZZER_STATE["quiz_used_track_ids"]

	def _append_quiz_guess_history(self, key, text, kind):
		# Najważniejsze: lista prób — pelny tekst + rodzaj: correct | artist_hint | wrong | skip (kolory na kliencie).
		self._ensure_quiz_state()
		gh = BUZZER_STATE.get("quiz_guess_history")
		if not isinstance(gh, dict):
			BUZZER_STATE["quiz_guess_history"] = {}
			gh = BUZZER_STATE["quiz_guess_history"]
		prev = gh.get(key)
		if not isinstance(prev, list):
			prev = []
		line = str(text or "").strip()[:200]
		if not line:
			return
		k = str(kind or "").strip().lower()
		if k not in ("artist_hint", "wrong", "correct", "skip"):
			k = "wrong"
		if k != "skip" and prev and isinstance(prev[-1], dict):
			last = prev[-1]
			if str(last.get("text") or "").strip() == line and str(last.get("kind") or "").lower() == k:
				# Najważniejsze: ten sam wpis pod rząd (np. podwójne wysłanie zgadnięcia) — nie duplikuj listy; skip zawsze osobno.
				return
		prev.append({"text": line, "kind": k})
		gh[key] = prev[-40:]

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

	def _count_finished_quiz_players(self):
		# Najważniejsze: zajęty gracz „zakończył” utwór po pełnym trafieniu albo po odpadnięciu na ostatnim tierze.
		self._ensure_quiz_state()
		total = 0
		for i in range(1, MAX_PLAYERS + 1):
			if not self._is_player_occupied(i):
				continue
			key = str(i)
			if bool(BUZZER_STATE["quiz_guessed_players"].get(key)) or bool(BUZZER_STATE["quiz_wrong_players"].get(key)):
				total = total + 1
		return total

	def _all_occupied_finished_song(self):
		occupied = self._count_occupied_players()
		if occupied <= 0:
			return False
		return self._count_finished_quiz_players() >= occupied

	def _max_listen_sec_still_in_round(self):
		# Najważniejsze: długość „wspólnego” timera admina = max sekund słuchania wśród graczy jeszcze w grze.
		self._ensure_quiz_state()
		lp = BUZZER_STATE.get("quiz_listen_phase")
		if not isinstance(lp, dict):
			lp = {}
		mx = 0
		still = False
		for i in range(1, MAX_PLAYERS + 1):
			if not self._is_player_occupied(i):
				continue
			key = str(i)
			if bool(BUZZER_STATE["quiz_guessed_players"].get(key)):
				continue
			if bool(BUZZER_STATE["quiz_wrong_players"].get(key)):
				continue
			still = True
			idx = int(lp.get(key, 0))
			if idx < 0:
				idx = 0
			if idx >= len(QUIZ_PHASE_DURATIONS):
				idx = len(QUIZ_PHASE_DURATIONS) - 1
			sec = QUIZ_PHASE_DURATIONS[idx]
			if sec > mx:
				mx = sec
		if not still:
			return QUIZ_PHASE_DURATIONS[0]
		return mx

	def _bump_quiz_listen_clip(self):
		# Najważniejsze: globalny token — wszyscy zsynchronizowani (start rundy, ostatnia faza / eliminacja, sobik „następna faza”).
		self._ensure_quiz_state()
		BUZZER_STATE["quiz_command_token"] = int(BUZZER_STATE["quiz_command_token"]) + 1
		BUZZER_STATE["quiz_command_duration_sec"] = self._max_listen_sec_still_in_round()
		BUZZER_STATE["quiz_command_issued_ms"] = self._now_ms()

	def _refresh_quiz_listen_duration_no_token(self):
		# Najważniejsze: przelicz max czas słuchu bez podbijania quiz_command_token — bez ponownego startu klipu u wszystkich.
		self._ensure_quiz_state()
		BUZZER_STATE["quiz_command_duration_sec"] = self._max_listen_sec_still_in_round()
		BUZZER_STATE["quiz_command_issued_ms"] = self._now_ms()
		BUZZER_STATE["last_update_ms"] = self._now_ms()

	def _bump_quiz_listen_for_player(self, key):
		# Najważniejsze: tylko ten gracz dostaje nowy odsłuch (wyższy tier) — bez przerywania pozostałym.
		self._ensure_quiz_state()
		k = str(key)
		ltok = BUZZER_STATE.get("quiz_listen_token")
		if not isinstance(ltok, dict):
			BUZZER_STATE["quiz_listen_token"] = {}
			ltok = BUZZER_STATE["quiz_listen_token"]
		ltok[k] = int(ltok.get(k, 0)) + 1
		BUZZER_STATE["quiz_command_duration_sec"] = self._max_listen_sec_still_in_round()
		BUZZER_STATE["quiz_command_issued_ms"] = self._now_ms()
		BUZZER_STATE["last_update_ms"] = self._now_ms()

	def _quiz_get_listen_phase_and_last(self, key):
		# Najważniejsze: indeks 0..3 = 4 fazy (0,5 s / 2 / 4 / 6 s); poza zakresem — clamp do stanu.
		self._ensure_quiz_state()
		lp = BUZZER_STATE.get("quiz_listen_phase")
		if not isinstance(lp, dict):
			BUZZER_STATE["quiz_listen_phase"] = {}
			lp = BUZZER_STATE["quiz_listen_phase"]
		k = str(key)
		last_i = len(QUIZ_PHASE_DURATIONS) - 1
		try:
			cur = int(lp.get(k, 0))
		except (TypeError, ValueError):
			cur = 0
		if cur < 0:
			cur = 0
		if cur > last_i:
			cur = last_i
		lp[k] = cur
		return lp, cur, last_i

	def _quiz_points_for_player_key(self, key):
		_, cur, _ = self._quiz_get_listen_phase_and_last(key)
		if cur < 0 or cur >= len(QUIZ_PHASE_POINTS):
			return QUIZ_PHASE_POINTS[0]
		return QUIZ_PHASE_POINTS[cur]

	def _sanitize_music_query(self, raw):
		text = str(raw or "").strip()
		if len(text) < 2:
			return None
		if len(text) > 120:
			text = text[:120]
		return text

	def _current_quiz_music_query(self):
		self._ensure_quiz_state()
		return QUIZ_MUSIC_FIXED_POLISH

	def _quiz_music_query_is_hiphop_year_range(self, q):
		s = str(q or "").strip()
		if s == QUIZ_HIPHOP_YEAR_RANGE_QUERY:
			return True
		if s == QUIZ_HIPHOP_YEAR_QUERY_LEGACY:
			return True
		return False

	def _build_quiz_track_pool_for_query(self, query_raw):
		# Najważniejsze: pula z Deezera — polskie utwory; krotka budowa (malo HTTP) + cache w pamieci zeby kolejne rundy nie czekaly na Deezer.
		global _DEEZER_LAST_FETCH_ERR, _QUIZ_TRACK_POOL_CACHE, _QUIZ_TRACK_POOL_CACHE_MS
		now = self._now_ms()
		if _QUIZ_TRACK_POOL_CACHE and (now - _QUIZ_TRACK_POOL_CACHE_MS) < QUIZ_POOL_CACHE_TTL_MS:
			return list(_QUIZ_TRACK_POOL_CACHE)
		_DEEZER_LAST_FETCH_ERR = ""
		if self._quiz_music_query_is_hiphop_year_range(query_raw):
			year_filter = (QUIZ_HIPHOP_YEAR_MIN, QUIZ_HIPHOP_YEAR_MAX)
		else:
			year_filter = (QUIZ_MODERN_POP_YEAR_MIN, QUIZ_MODERN_POP_YEAR_MAX)
		seen_ids = set()
		tracks = []

		def add_batch(batch):
			for t in batch or []:
				tid = str(t.get("id", "")).strip()
				if not tid or tid in seen_ids:
					continue
				seen_ids.add(tid)
				tracks.append(t)

		add_batch(
			self._fetch_deezer_quiz_whitelist_artist_pool(
				200,
				year_filter,
				max_artists=int(QUIZ_POOL_BUILD_MAX_DEEZER_HTTP),
			)
		)
		if not tracks:
			add_batch(
				self._fetch_deezer_chart_tracks(
					100,
					year_filter=year_filter,
					quiz_pool_whitelist=True,
				)
			)
		if tracks:
			# Najważniejsze: ucinamy dominację jednego artysty z jednego zapytania Deezera.
			tracks = self._quiz_pool_limit_per_artist(tracks, int(QUIZ_POOL_MAX_TRACKS_PER_ARTIST))
			# Najważniejsze: sort po rank Deezera — tylko top N do cache (losowanie dalej z tej listy).
			tracks.sort(key=lambda t: int(t.get("rank") or 0), reverse=True)
			topn = max(1, int(QUIZ_POOL_TOP_BY_RANK_COUNT))
			tracks = tracks[:topn]
			_QUIZ_TRACK_POOL_CACHE = tracks
			_QUIZ_TRACK_POOL_CACHE_MS = self._now_ms()
		return tracks

	def _quiz_pool_limit_per_artist(self, tracks, max_per_artist):
		# Najważniejsze: po złożeniu puli — max N pozycji na znormalizowanego artystę (losowa kolejność przed ucinaniem).
		if not tracks or max_per_artist <= 0:
			return tracks
		shuffled = list(tracks)
		random.shuffle(shuffled)
		counts = {}
		out = []
		for t in shuffled:
			a = _fold_text_answer(str(t.get("artist") or "")).strip() or "_"
			n = counts.get(a, 0)
			if n >= max_per_artist:
				continue
			counts[a] = n + 1
			out.append(t)
		return out

	def _pick_quiz_track_unique_random(self, query_raw, used_ids_list, last_exclude_id):
		# Najważniejsze: każdy track_id max raz na cykl — po wyczerpaniu puli reset „już grane” + shuffle zamiast wag rank.
		tracks = self._build_quiz_track_pool_for_query(query_raw)
		if not tracks:
			return None

		def tidof(t):
			return str(t.get("id", "")).strip()

		ex = str(last_exclude_id or "").strip()
		used_set = set(str(x).strip() for x in used_ids_list if str(x).strip())
		cands = []
		for t in tracks:
			tid = tidof(t)
			if not tid:
				continue
			if tid in used_set:
				continue
			if tid == ex:
				continue
			cands.append(t)
		if not cands:
			used_ids_list[:] = []
			for t in tracks:
				tid = tidof(t)
				if not tid:
					continue
				if tid == ex:
					continue
				cands.append(t)
		if not cands:
			cands = [t for t in tracks if tidof(t)]
		if not cands:
			return None
		random.shuffle(cands)
		ch = cands[0]
		tid = tidof(ch)
		if tid:
			used_ids_list.append(tid)
		return ch

	def _pick_random_quiz_track(self):
		# Najważniejsze: multiplayer — losowo z puli bez powtórek do końca cyklu.
		self._ensure_quiz_state()
		used = BUZZER_STATE.get("quiz_used_track_ids")
		if not isinstance(used, list):
			BUZZER_STATE["quiz_used_track_ids"] = []
			used = BUZZER_STATE["quiz_used_track_ids"]
		last_id = str(BUZZER_STATE.get("quiz_track_id", "")).strip()
		return self._pick_quiz_track_unique_random(self._current_quiz_music_query(), used, last_id)

	def _pick_random_quiz_track_excluding(self, query_raw, exclude_id, used_ids_list):
		# Najważniejsze: solo — ta sama rotacja co multiplayer (lista used w sesji).
		if not isinstance(used_ids_list, list):
			return self._pick_quiz_track_unique_random(query_raw, [], exclude_id)
		return self._pick_quiz_track_unique_random(query_raw, used_ids_list, exclude_id)

	def _quiz_round_limit_reached(self):
		# Najważniejsze: sesja quizu z limitem — nie startuj kolejnego utworu gdy wykorzystano pulę rund.
		self._ensure_quiz_state()
		limit = int(BUZZER_STATE.get("quiz_round_limit") or 0)
		if limit <= 0:
			return False
		played = int(BUZZER_STATE.get("quiz_rounds_played") or 0)
		return played >= limit

	def _start_quiz_round(self):
		self._ensure_quiz_state()
		su = BUZZER_STATE.get("quiz_skips_used")
		if not isinstance(su, dict):
			BUZZER_STATE["quiz_skips_used"] = {}
			su = BUZZER_STATE["quiz_skips_used"]
		for i in range(1, MAX_PLAYERS + 1):
			key = str(i)
			BUZZER_STATE["quiz_guessed_players"][key] = False
			BUZZER_STATE["quiz_artist_hint_players"][key] = False
			BUZZER_STATE["quiz_wrong_players"][key] = False
			BUZZER_STATE["quiz_wrong_guesses"][key] = []
			BUZZER_STATE["quiz_guess_history"][key] = []
			BUZZER_STATE["quiz_listen_phase"][key] = 0
			BUZZER_STATE["quiz_listen_token"][key] = 0
			su[key] = 0
		BUZZER_STATE["quiz_round_active"] = True
		BUZZER_STATE["quiz_phase_index"] = 0
		BUZZER_STATE["quiz_command_token"] = int(BUZZER_STATE["quiz_command_token"]) + 1
		BUZZER_STATE["quiz_command_duration_sec"] = self._max_listen_sec_still_in_round()
		BUZZER_STATE["quiz_command_issued_ms"] = self._now_ms()

	def _start_quiz_round_with_random_track(self):
		# Najważniejsze: wspólna logika losowania utworu i startu fazy 1 (reczny start i auto-start).
		cancel_quiz_auto_next_timer()
		self._ensure_quiz_state()
		if self._quiz_round_limit_reached():
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			return False
		random_track = self._pick_random_quiz_track()
		if random_track is None:
			return False
		BUZZER_STATE["quiz_track_id"] = str(random_track.get("id", "")).strip()
		BUZZER_STATE["quiz_track_label"] = str(random_track.get("label", "")).strip()[:120]
		BUZZER_STATE["quiz_track_title"] = str(random_track.get("title", "") or "").strip()[:120]
		BUZZER_STATE["quiz_track_artist"] = str(random_track.get("artist", "") or "").strip()[:120]
		deezer_preview = str(random_track.get("previewUrl", "")).strip()
		it_preview = self._itunes_preview_url_for_title_artist(
			BUZZER_STATE["quiz_track_title"],
			BUZZER_STATE["quiz_track_artist"],
		)
		BUZZER_STATE["quiz_preview_url"] = it_preview if it_preview else deezer_preview
		BUZZER_STATE["quiz_reveal_active"] = False
		BUZZER_STATE["quiz_reveal_seek_middle"] = False
		self._start_quiz_round()
		BUZZER_STATE["quiz_rounds_played"] = int(BUZZER_STATE.get("quiz_rounds_played") or 0) + 1
		BUZZER_STATE["last_update_ms"] = self._now_ms()
		return True

	def _maybe_auto_start_quiz_when_all_ready(self):
		# Najważniejsze: gdy sobik ustawi typ muzyki — start bez przycisku Gotowy (UI go nie ma).
		self._ensure_scores_and_names()
		self._ensure_quiz_state()
		if bool(BUZZER_STATE.get("quiz_reveal_active")):
			return False
		if bool(BUZZER_STATE.get("quiz_round_active")):
			return False
		if self._count_occupied_players() <= 0:
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
		if bool(BUZZER_STATE.get("quiz_reveal_active")):
			return
		cancel_quiz_auto_next_timer()
		BUZZER_STATE["quiz_round_active"] = False
		BUZZER_STATE["quiz_reveal_active"] = True
		BUZZER_STATE["quiz_phase_index"] = -1
		guessed = self._count_guessed_players()
		occupied = self._count_occupied_players()
		# Najważniejsze: refren (koniec próbki Deezer) tylko gdy ktoś w rundzie nie zgadł; gdy wszyscy trafili — krótki klip od początku preview.
		BUZZER_STATE["quiz_reveal_seek_middle"] = bool(occupied > 0 and guessed < occupied)
		BUZZER_STATE["quiz_command_token"] = int(BUZZER_STATE["quiz_command_token"]) + 1
		BUZZER_STATE["quiz_command_duration_sec"] = QUIZ_REVEAL_CLIP_SEC
		BUZZER_STATE["quiz_command_issued_ms"] = self._now_ms()
		for i in range(1, MAX_PLAYERS + 1):
			# Najważniejsze: po ujawnieniu trzeba znowu zaznaczyc Gotowy przed kolejna piosenka.
			BUZZER_STATE["quiz_ready_players"][str(i)] = False
			BUZZER_STATE["quiz_artist_hint_players"][str(i)] = False
		BUZZER_STATE["last_update_ms"] = self._now_ms()
		# Najważniejsze: po każdym ujawnieniu (pełne trafienia, eliminacje lub mix) — po klipie automatycznie losujemy kolejny utwór (nie tylko gdy wszyscy zgadli).
		if self._count_occupied_players() > 0:
			schedule_quiz_auto_next_after_reveal()

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
			"quizMusicQuery": QUIZ_MUSIC_FIXED_POLISH_LABEL,
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
			"quizGuessHistory": BUZZER_STATE["quiz_guess_history"],
			"quizGuessedCount": self._count_guessed_players(),
			"quizFinishedCount": self._count_finished_quiz_players(),
			"quizListenPhases": dict(BUZZER_STATE.get("quiz_listen_phase") or {}),
			"quizListenTokens": dict(BUZZER_STATE.get("quiz_listen_token") or {}),
			"quizSkipsUsed": dict(BUZZER_STATE.get("quiz_skips_used") or {}),
			"quizRoundLimit": int(BUZZER_STATE.get("quiz_round_limit") or 0),
			"quizRoundsPlayed": int(BUZZER_STATE.get("quiz_rounds_played") or 0),
			"quizSessionId": int(BUZZER_STATE.get("quiz_session_id") or 1),
			"quizRoundsExhausted": bool(
				int(BUZZER_STATE.get("quiz_round_limit") or 0) > 0
				and int(BUZZER_STATE.get("quiz_rounds_played") or 0)
				>= int(BUZZER_STATE.get("quiz_round_limit") or 0)
			),
			"quizListenMaxSec": float(BUZZER_STATE.get("quiz_command_duration_sec") or 0),
			"quizReadyPlayers": BUZZER_STATE["quiz_ready_players"],
			"quizReadyCount": self._count_ready_players(),
			"quizOccupiedCount": self._count_occupied_players(),
			"videoControllerName": VIDEO_CONTROLLER_NAME,
			"scores": BUZZER_STATE["scores"],
			"playerNames": BUZZER_STATE["player_names"],
			"playerAvatars": BUZZER_STATE["player_avatars"],
			"lastUpdateMs": BUZZER_STATE["last_update_ms"],
		}

	def _client_ip(self):
		xff = str(self.headers.get("X-Forwarded-For") or "").strip()
		if xff:
			return xff.split(",")[0].strip()[:80]
		try:
			return str(self.client_address[0])[:80]
		except Exception:
			return ""

	def _prune_solo_sessions_unlocked(self):
		now = self._now_ms()
		todel = [
			k
			for k, s in SOLO_QUIZ_SESSIONS.items()
			if now - int(s.get("created_ms", 0)) > SOLO_SESSION_TTL_MS
		]
		for k in todel:
			del SOLO_QUIZ_SESSIONS[k]

	def _solo_get_session(self, token):
		with SOLO_QUIZ_LOCK:
			self._prune_solo_sessions_unlocked()
			return SOLO_QUIZ_SESSIONS.get(str(token or "").strip())

	def _solo_start_round_with_track(self, sess, tr):
		sess["track_id"] = str(tr.get("id", "")).strip()
		sess["label"] = str(tr.get("label", "")).strip()[:120]
		sess["title"] = str(tr.get("title", "") or "").strip()[:120]
		sess["artist"] = str(tr.get("artist", "") or "").strip()[:120]
		deezer_preview = str(tr.get("previewUrl", "")).strip()
		it_preview = self._itunes_preview_url_for_title_artist(sess.get("title"), sess.get("artist"))
		sess["preview_url"] = it_preview if it_preview else deezer_preview
		sess["round_active"] = True
		sess["reveal_active"] = False
		sess["reveal_seek_middle"] = False
		sess["listen_phase"] = 0
		sess["guessed"] = False
		sess["wrong"] = False
		sess["artist_hint"] = False
		sess["skips_used"] = 0
		sess["guess_history"] = []
		sess["command_token"] = int(sess.get("command_token", 0)) + 1
		sess["listen_token"] = int(sess.get("listen_token", 0)) + 1
		idx = 0
		sess["command_duration_sec"] = float(QUIZ_PHASE_DURATIONS[idx])
		sess["issued_ms"] = self._now_ms()
		with SOLO_QUIZ_LOCK:
			SOLO_QUIZ_SESSIONS[sess["token"]] = sess

	def _solo_begin_reveal(self, sess):
		sess["round_active"] = False
		sess["reveal_active"] = True
		sess["reveal_seek_middle"] = bool(not sess.get("guessed"))
		sess["command_token"] = int(sess.get("command_token", 0)) + 1
		sess["command_duration_sec"] = float(QUIZ_REVEAL_CLIP_SEC)
		sess["issued_ms"] = self._now_ms()
		with SOLO_QUIZ_LOCK:
			SOLO_QUIZ_SESSIONS[sess["token"]] = sess

	def _public_solo_state(self, sess):
		reveal = bool(sess.get("reveal_active"))
		idx = int(sess.get("listen_phase", 0))
		last_i = len(QUIZ_PHASE_DURATIONS) - 1
		if idx < 0:
			idx = 0
		if idx > last_i:
			idx = last_i
		cmd_dur = float(QUIZ_REVEAL_CLIP_SEC) if reveal else float(QUIZ_PHASE_DURATIONS[idx])
		show = reveal
		ql = sess.get("label", "") if show else ""
		qt = sess.get("title", "") if show else ""
		qa = sess.get("artist", "") if show else ""
		return {
			"sessionId": sess["token"],
			"quizMusicQuery": sess.get("music_query", ""),
			"quizPreviewUrl": sess.get("preview_url", ""),
			"quizTrackLabel": ql,
			"quizTrackTitle": qt,
			"quizTrackArtist": qa,
			"quizTrackId": sess.get("track_id", ""),
			"quizRevealActive": reveal,
			"quizRevealSeekMiddle": bool(sess.get("reveal_seek_middle")),
			"quizRoundActive": bool(sess.get("round_active")),
			"quizCommandToken": int(sess.get("command_token", 0)),
			"quizCommandDurationSec": cmd_dur,
			"quizCommandIssuedMs": int(sess.get("issued_ms", 0)),
			"quizPhaseDurations": QUIZ_PHASE_DURATIONS,
			"quizPhasePoints": QUIZ_PHASE_POINTS,
			"quizPhaseIndex": -1,
			"quizListenPhases": {"1": idx},
			"quizListenTokens": {"1": int(sess.get("listen_token", 0))},
			"quizSkipsUsed": {"1": int(sess.get("skips_used", 0))},
			"quizGuessHistory": {"1": list(sess.get("guess_history", []))},
			"quizGuessedPlayers": {"1": bool(sess.get("guessed"))},
			"quizWrongPlayers": {"1": bool(sess.get("wrong"))},
			"scores": {"1": int(sess.get("total_score", 0))},
			"soloMode": True,
			"soloScore": int(sess.get("total_score", 0)),
			"lastUpdateMs": int(sess.get("issued_ms", 0)),
		}

	def _solo_new_game(self, music_query_raw):
		with SOLO_QUIZ_LOCK:
			self._prune_solo_sessions_unlocked()
			_ = music_query_raw
			q = QUIZ_MUSIC_FIXED_POLISH_LABEL
			tok = secrets.token_hex(20)
			sess = {
				"token": tok,
				"music_query": q,
				"created_ms": self._now_ms(),
				"issued_ms": 0,
				"command_token": 0,
				"listen_token": 0,
				"total_score": 0,
				"used_track_ids": [],
			}
			SOLO_QUIZ_SESSIONS[tok] = sess
		tr = self._pick_random_quiz_track_excluding(sess["music_query"], "", sess["used_track_ids"])
		if not tr:
			with SOLO_QUIZ_LOCK:
				if tok in SOLO_QUIZ_SESSIONS:
					del SOLO_QUIZ_SESSIONS[tok]
			return None, "Brak utworow (Deezer niedostepny lub pusta pula)"
		self._solo_start_round_with_track(sess, tr)
		return sess, None

	def _solo_next_round(self, sess):
		if not isinstance(sess.get("used_track_ids"), list):
			sess["used_track_ids"] = []
		tr = self._pick_random_quiz_track_excluding(
			sess.get("music_query"),
			sess.get("track_id"),
			sess.get("used_track_ids"),
		)
		if not tr:
			return False
		self._solo_start_round_with_track(sess, tr)
		return True

	def _mask_ip_for_display(self, ip):
		s = str(ip or "").strip()
		if s.count(".") == 3:
			parts = s.split(".")
			return "•••.•••.•••." + parts[-1]
		if ":" in s and len(s) > 4:
			return "••••" + s[-4:]
		return s[:24] if s else "?"

	def _read_solo_leaderboard(self):
		try:
			with open(QUIZ_SOLO_LEADERBOARD_FILE, "r", encoding="utf-8") as f:
				d = json.load(f)
			if not isinstance(d, dict):
				return {"byIp": {}}
			by_ip = d.get("byIp")
			if not isinstance(by_ip, dict):
				return {"byIp": {}}
			return {"byIp": by_ip}
		except Exception:
			return {"byIp": {}}

	def _write_solo_leaderboard(self, data):
		os.makedirs(DATA_DIR, exist_ok=True)
		tmp = QUIZ_SOLO_LEADERBOARD_FILE + ".tmp"
		with open(tmp, "w", encoding="utf-8") as f:
			json.dump(data, f, ensure_ascii=False, indent=2)
		os.replace(tmp, QUIZ_SOLO_LEADERBOARD_FILE)

	def handle_quiz_solo_leaderboard_get(self):
		try:
			data = self._read_solo_leaderboard()
			by_ip = data.get("byIp") or {}
			rows = []
			for ip, rec in by_ip.items():
				if not isinstance(rec, dict):
					continue
				best = int(rec.get("bestScore", 0))
				rows.append(
					{
						"label": self._mask_ip_for_display(ip),
						"bestScore": best,
						"updatedMs": int(rec.get("updatedMs", 0)),
					}
				)
			rows.sort(key=lambda r: (-r["bestScore"], -r["updatedMs"]))
			self.json_response({"entries": rows[:50]}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_solo_new_post(self):
		try:
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			sess, err = self._solo_new_game(parsed.get("musicQuery"))
			if not sess:
				self.json_response({"error": err or "Brak utworow"}, 500)
				return
			self.json_response({"ok": True, "state": self._public_solo_state(sess)}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_solo_next_round_post(self):
		try:
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			sid = str(parsed.get("sessionId") or "").strip()
			sess = self._solo_get_session(sid)
			if not sess:
				self.json_response({"error": "Nieprawidlowa lub wygasla sesja"}, 400)
				return
			if bool(sess.get("round_active")):
				self.json_response({"error": "Najpierw dokoncz runde"}, 400)
				return
			if not bool(sess.get("reveal_active")):
				self.json_response({"error": "Brak fazy ujawnienia"}, 400)
				return
			if not self._solo_next_round(sess):
				msg = "No Deezer tracks available"
				detail = str(_DEEZER_LAST_FETCH_ERR or "").strip()
				if detail:
					msg = "%s — %s" % (msg, detail[:220])
				self.json_response({"error": msg}, 500)
				return
			self.json_response({"ok": True, "state": self._public_solo_state(sess)}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_solo_guess_post(self):
		try:
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			sid = str(parsed.get("sessionId") or "").strip()
			sess = self._solo_get_session(sid)
			if not sess:
				self.json_response({"error": "Nieprawidlowa lub wygasla sesja"}, 400)
				return
			if bool(sess.get("reveal_active")) or not bool(sess.get("round_active")):
				self.json_response({"error": "Runda nieaktywna"}, 400)
				return
			if sess.get("guessed") or sess.get("wrong"):
				self.json_response({"ok": True, "state": self._public_solo_state(sess)}, 200)
				return
			guess = str(parsed.get("guess", "")).strip()
			if len(guess) < 3:
				self.json_response({"error": "Za krotka odpowiedz"}, 400)
				return
			title = str(sess.get("title", "") or "")
			artist = str(sess.get("artist", "") or "")
			if self._guess_matches_deezer(guess, title, artist):
				sess["artist_hint"] = False
				idx = int(sess.get("listen_phase", 0))
				if idx < 0:
					idx = 0
				if idx >= len(QUIZ_PHASE_POINTS):
					idx = len(QUIZ_PHASE_POINTS) - 1
				points = QUIZ_PHASE_POINTS[idx]
				sess["total_score"] = int(sess.get("total_score", 0)) + int(points)
				sess["guessed"] = True
				sess.setdefault("guess_history", []).append({"text": guess, "kind": "correct"})
				self._solo_begin_reveal(sess)
				self.json_response({"ok": True, "state": self._public_solo_state(sess)}, 200)
				return
			if self._artist_only_matches_round(guess, title, artist):
				sess.setdefault("guess_history", []).append({"text": guess, "kind": "artist_hint"})
				sess["artist_hint"] = True
				cur = int(sess.get("listen_phase", 0))
				last_i = len(QUIZ_PHASE_DURATIONS) - 1
				if cur < last_i:
					sess["listen_phase"] = cur + 1
					nidx = int(sess["listen_phase"])
					sess["command_duration_sec"] = float(QUIZ_PHASE_DURATIONS[nidx])
					sess["listen_token"] = int(sess.get("listen_token", 0)) + 1
					sess["issued_ms"] = self._now_ms()
					with SOLO_QUIZ_LOCK:
						SOLO_QUIZ_SESSIONS[sess["token"]] = sess
					self.json_response({"ok": True, "artistHintOnly": True, "state": self._public_solo_state(sess)}, 200)
					return
				sess["artist_hint"] = False
				sess["wrong"] = True
				self._solo_begin_reveal(sess)
				self.json_response({"ok": True, "guessWrong": True, "artistHintLastPhase": True, "state": self._public_solo_state(sess)}, 200)
				return
			sess["artist_hint"] = False
			cur = int(sess.get("listen_phase", 0))
			last_i = len(QUIZ_PHASE_DURATIONS) - 1
			sess.setdefault("guess_history", []).append({"text": guess, "kind": "wrong"})
			if cur < last_i:
				sess["listen_phase"] = cur + 1
				nidx = int(sess["listen_phase"])
				sess["command_duration_sec"] = float(QUIZ_PHASE_DURATIONS[nidx])
				sess["listen_token"] = int(sess.get("listen_token", 0)) + 1
				sess["issued_ms"] = self._now_ms()
				with SOLO_QUIZ_LOCK:
					SOLO_QUIZ_SESSIONS[sess["token"]] = sess
				self.json_response({"ok": True, "guessWrong": True, "state": self._public_solo_state(sess)}, 200)
				return
			sess["wrong"] = True
			self._solo_begin_reveal(sess)
			self.json_response({"ok": True, "guessWrong": True, "state": self._public_solo_state(sess)}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_solo_skip_post(self):
		try:
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			sid = str(parsed.get("sessionId") or "").strip()
			sess = self._solo_get_session(sid)
			if not sess:
				self.json_response({"error": "Nieprawidlowa lub wygasla sesja"}, 400)
				return
			if bool(sess.get("reveal_active")) or not bool(sess.get("round_active")):
				self.json_response({"error": "Runda nieaktywna"}, 400)
				return
			if sess.get("guessed") or sess.get("wrong"):
				self.json_response({"ok": True, "state": self._public_solo_state(sess)}, 200)
				return
			if int(sess.get("skips_used", 0)) >= QUIZ_MAX_SKIPS_PER_ROUND:
				self.json_response({"error": "Wykorzystales juz max skipow (4) w tej rundzie"}, 400)
				return
			cur = int(sess.get("listen_phase", 0))
			last_i = len(QUIZ_PHASE_DURATIONS) - 1
			if cur < 0:
				cur = 0
			if cur > last_i:
				cur = last_i
			# Najważniejsze: na ostatniej fazie SKIP zablokowany — trzeba zgadnąć (spójnie z trybem wieloosobowym).
			if cur >= last_i:
				self.json_response(
					{"error": "Na ostatniej szansie nie mozna uzyc SKIP — trzeba zgadnac."},
					400,
				)
				return
			sess["skips_used"] = int(sess.get("skips_used", 0)) + 1
			sess["artist_hint"] = False
			sess.setdefault("guess_history", []).append({"text": "SKIP", "kind": "skip"})
			sess["listen_phase"] = cur + 1
			nidx = int(sess["listen_phase"])
			sess["command_duration_sec"] = float(QUIZ_PHASE_DURATIONS[nidx])
			sess["listen_token"] = int(sess.get("listen_token", 0)) + 1
			sess["issued_ms"] = self._now_ms()
			with SOLO_QUIZ_LOCK:
				SOLO_QUIZ_SESSIONS[sess["token"]] = sess
			self.json_response({"ok": True, "skippedPhase": True, "state": self._public_solo_state(sess)}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_solo_leaderboard_submit_post(self):
		try:
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			sid = str(parsed.get("sessionId") or "").strip()
			sess = self._solo_get_session(sid)
			if not sess:
				self.json_response({"error": "Nieprawidlowa lub wygasla sesja"}, 400)
				return
			score = int(sess.get("total_score", 0))
			ip = self._client_ip()
			if not ip:
				self.json_response({"error": "Brak adresu IP"}, 400)
				return
			data = self._read_solo_leaderboard()
			by_ip = data.setdefault("byIp", {})
			prev = by_ip.get(ip, {})
			if not isinstance(prev, dict):
				prev = {}
			best = int(prev.get("bestScore", 0))
			new_best = max(best, score)
			by_ip[ip] = {
				"bestScore": new_best,
				"lastScore": score,
				"updatedMs": self._now_ms(),
			}
			self._write_solo_leaderboard(data)
			self.json_response({"ok": True, "saved": True, "bestScore": new_best, "submittedScore": score}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

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
		if parsed.path == "/api/quiz-solo/leaderboard":
			self.handle_quiz_solo_leaderboard_get()
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
		if parsed.path == "/api/quiz-round-limit":
			self.handle_quiz_round_limit_post()
			return
		if parsed.path == "/api/quiz-full-reset":
			self.handle_quiz_full_reset_post()
			return
		if parsed.path == "/api/quiz-next-phase":
			self.handle_quiz_next_phase_post()
			return
		if parsed.path == "/api/quiz-guess":
			self.handle_quiz_guess_post()
			return
		if parsed.path == "/api/quiz-skip-phase":
			self.handle_quiz_skip_phase_post()
			return
		if parsed.path == "/api/quiz-solo/new-game":
			self.handle_quiz_solo_new_post()
			return
		if parsed.path == "/api/quiz-solo/next-round":
			self.handle_quiz_solo_next_round_post()
			return
		if parsed.path == "/api/quiz-solo/guess":
			self.handle_quiz_solo_guess_post()
			return
		if parsed.path == "/api/quiz-solo/skip-phase":
			self.handle_quiz_solo_skip_post()
			return
		if parsed.path == "/api/quiz-solo/leaderboard-submit":
			self.handle_quiz_solo_leaderboard_submit_post()
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
			self._assign_random_avatar_for_player_key(str(player))
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
			BUZZER_STATE["quiz_guess_history"][str(assigned_player)] = []
			self._assign_random_avatar_for_player_key(str(assigned_player))
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
			BUZZER_STATE["quiz_guess_history"][key] = []
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
		global _DEEZER_LAST_FETCH_ERR
		ctx = _deezer_ssl_context()
		req = Request(
			url,
			headers={
				"User-Agent": DEEZER_HTTP_UA,
				"Accept": "application/json",
			},
		)
		try:
			with urlopen(req, timeout=22, context=ctx) as response:
				raw = response.read().decode("utf-8", errors="replace")
			parsed = json.loads(raw)
			if isinstance(parsed, dict) and parsed.get("error") is not None:
				_DEEZER_LAST_FETCH_ERR = "Deezer API: %s" % str(parsed.get("error"))[:200]
				return {}
			return parsed
		except (HTTPError, URLError, OSError, TimeoutError, ValueError) as ex:
			extra = ""
			if isinstance(ex, HTTPError):
				try:
					if ex.fp is not None:
						extra = (ex.fp.read() or b"").decode("utf-8", errors="replace")[:240]
				except Exception:
					extra = ""
			_DEEZER_LAST_FETCH_ERR = ("%s %s" % (str(ex), extra)).strip()[:300]
			return {}

	def _fetch_itunes_url_json(self, url):
		# Najważniejsze: iTunes Search API — previewUrl to zwykle początek utworu (Deezer preview często wycinek ze środka).
		ctx = _deezer_ssl_context()
		req = Request(
			url,
			headers={
				"User-Agent": DEEZER_HTTP_UA,
				"Accept": "application/json",
			},
		)
		try:
			with urlopen(req, timeout=18, context=ctx) as response:
				raw = response.read().decode("utf-8", errors="replace")
			parsed = json.loads(raw)
			return parsed if isinstance(parsed, dict) else {}
		except (HTTPError, URLError, OSError, TimeoutError, ValueError):
			return {}

	def _itunes_pick_best_preview(self, parsed, want_title, want_artist):
		# Najważniejsze: wybór wyniku iTunes zgodnego z tytułem/artystą z Deezera (unikamy pomyłki utworu).
		if not isinstance(parsed, dict):
			return ""
		results = parsed.get("results")
		if not isinstance(results, list) or not results:
			return ""
		ft = _fold_text_answer(want_title)
		fa = _fold_text_answer(want_artist)
		if len(ft) < 2 or len(fa) < 2:
			return ""
		best_url = ""
		best_score = -1
		for r in results:
			if not isinstance(r, dict):
				continue
			purl = str(r.get("previewUrl") or "").strip()
			if not purl.startswith("http"):
				continue
			rn = _fold_text_answer(str(r.get("trackName") or ""))
			ran = _fold_text_answer(str(r.get("artistName") or ""))
			score = 0
			if fa and ran:
				if fa == ran:
					score += 45
				elif fa in ran or ran in fa:
					score += 36
				else:
					faw = [w for w in fa.split() if len(w) > 2]
					hits_a = sum(1 for w in faw if w in ran)
					if faw and hits_a >= min(2, len(faw)):
						score += max(22, hits_a * 10)
					elif faw and hits_a == 1:
						score += 12
			if ft and rn:
				if ft == rn:
					score += 45
				elif ft in rn or rn in ft:
					score += 36
				else:
					ftw = [w for w in ft.split() if len(w) > 2]
					hits_t = sum(1 for w in ftw if w in rn)
					if ftw and hits_t >= min(2, len(ftw)):
						score += max(20, hits_t * 9)
					elif ftw and hits_t == 1:
						score += 10
			if score > best_score:
				best_score = score
				best_url = purl
		if best_score >= 55 and best_url:
			return best_url
		return ""

	def _itunes_preview_url_for_title_artist(self, title, artist):
		# Najważniejsze: gdy iTunes ma ten sam utwór, używamy preview od początku; gdy brak pewnego dopasowania — Deezer.
		t = str(_strip_title_feat(str(title or ""))).strip()
		a = str(artist or "").strip()
		if len(t) < 2 or len(a) < 2:
			return ""
		term = (t + " " + a)[:200]
		for country in ("pl", "us"):
			url = "https://itunes.apple.com/search?" + urlencode(
				{
					"term": term,
					"media": "music",
					"entity": "song",
					"limit": 15,
					"country": country,
				}
			)
			parsed = self._fetch_itunes_url_json(url)
			got = self._itunes_pick_best_preview(parsed, t, a)
			if got:
				return got
		return ""

	def _parse_year_from_date_str(self, raw):
		st = str(raw or "").strip()
		if len(st) >= 4 and st[:4].isdigit():
			try:
				y = int(st[:4])
				if 1990 <= y <= 2100:
					return y
			except Exception:
				return None
		return None

	def _deezer_track_release_year(self, item):
		# Najważniejsze: Deezer czesto zwraca date na utworze, czasem tylko na albumie — probuj oba.
		if not isinstance(item, dict):
			return None
		y = self._parse_year_from_date_str(item.get("release_date"))
		if y is not None:
			return y
		album = item.get("album") or {}
		if isinstance(album, dict):
			for akey in ("release_date", "release_date_original"):
				y = self._parse_year_from_date_str(album.get(akey))
				if y is not None:
					return y
		return None

	def _deezer_raw_items_artist_top_or_track(self, name, limit):
		# Najważniejsze: endpoint /artist/{id}/top czesto zwraca pustą listę (region/API) — stabilniejsze jest search/track.
		out = []
		seen_ids = set()
		lim = min(50, max(10, int(limit)))

		def _push_items(items):
			for it in items or []:
				if not isinstance(it, dict):
					continue
				try:
					tid = int(it.get("id") or 0)
				except Exception:
					continue
				if tid <= 0 or tid in seen_ids:
					continue
				seen_ids.add(tid)
				out.append(it)
				if len(out) >= lim:
					break

		try:
			turl = "https://api.deezer.com/search/track?" + urlencode({"q": name, "limit": lim})
			tp = self._fetch_deezer_url_json(turl)
			_push_items(tp.get("data") or [])
		except Exception:
			pass
		preview_ok = sum(1 for x in out if str((x or {}).get("preview") or "").strip())
		if len(out) < 4 or preview_ok < 4:
			try:
				surl = "https://api.deezer.com/search/artist?" + urlencode({"q": name, "limit": 5})
				sp = self._fetch_deezer_url_json(surl)
				data = sp.get("data") or []
				if data:
					aid = int(data[0].get("id") or 0)
					if aid > 0:
						turl = "https://api.deezer.com/artist/%d/top?limit=%d" % (aid, lim)
						tp = self._fetch_deezer_url_json(turl)
						_push_items(tp.get("data") or [])
			except Exception:
				pass
		return out[:lim]

	def _deezer_raw_item_year_ok_quiz(self, item, year_filter):
		# Najważniejsze: okno lat dla quizu; brak roku w API — nie odrzucamy (żeby pula nie pustnia).
		if not year_filter:
			return True
		try:
			ymin, ymax = int(year_filter[0]), int(year_filter[1])
		except Exception:
			return True
		y = self._deezer_track_release_year(item)
		if y is None:
			return True
		return ymin <= y <= ymax

	def _deezer_quiz_whitelist_artist_blob(self, item):
		# Najważniejsze: wykonawca główny + contributors (featy) — żeby whitelist łapał kolaże.
		parts = []
		am = item.get("artist") or {}
		parts.append(str(am.get("name") or ""))
		for c in item.get("contributors") or []:
			if isinstance(c, dict):
				parts.append(str(c.get("name") or ""))
		return _fold_text_answer(" ".join(parts))

	def _deezer_raw_item_quiz_whitelist_artist_ok(self, item):
		# Najważniejsze: dopasowanie po znormalizowanej nazwie z QUIZ_POOL_WHITELIST_ARTISTS (krótkie nicki jak tokeny).
		blob = self._deezer_quiz_whitelist_artist_blob(item)
		if not blob.strip():
			return False
		tokens = set(re.split(r"[^a-z0-9]+", blob))
		tokens.discard("")
		for seed in QUIZ_POOL_WHITELIST_ARTISTS:
			fs = _fold_text_answer(seed).strip()
			if len(fs) < 2:
				continue
			if len(fs) <= 4:
				if fs in tokens:
					return True
			else:
				if fs in blob:
					return True
		return False

	def _fetch_deezer_quiz_whitelist_artist_pool(self, cap, year_filter, max_artists=None):
		# Najważniejsze: tylko utwory z whitelisty — osobne zapytania Deezer po każdym artyście (rotacja nazw).
		out = []
		seen = set()
		names = list(QUIZ_POOL_WHITELIST_ARTISTS)
		random.shuffle(names)
		ma = int(QUIZ_POOL_BUILD_MAX_DEEZER_HTTP) if max_artists is None else int(max_artists)
		ma = max(4, min(ma, len(names)))
		for name in names[:ma]:
			if len(out) >= cap:
				break
			for item in self._deezer_raw_items_artist_top_or_track(name, 45):
				if not self._deezer_raw_item_year_ok_quiz(item, year_filter):
					continue
				if self._deezer_raw_item_quiz_block_foreign_classical(item):
					continue
				if not self._deezer_raw_item_quiz_whitelist_artist_ok(item):
					continue
				rec = self._deezer_track_to_suggest_dict(item)
				if not rec:
					continue
				tid = str(rec.get("id") or "").strip()
				if not tid or tid in seen:
					continue
				seen.add(tid)
				out.append(rec)
		return out

	def _fetch_deezer_polish_scene_artist_pool(self, cap, year_filter, max_artists=None):
		# Najważniejsze: PL scena — losowa podzbior artystow (szybciej niz cala lista przy kazdym losowaniu).
		out = []
		seen = set()
		names = list(QUIZ_MODERN_POOL_ARTIST_SEEDS)
		random.shuffle(names)
		if max_artists is not None:
			names = names[: max(1, int(max_artists))]
		for name in names:
			if len(out) >= cap:
				break
			for item in self._deezer_raw_items_artist_top_or_track(name, 40):
				if not self._deezer_raw_item_year_ok_quiz(item, year_filter):
					continue
				if self._deezer_raw_item_quiz_block_foreign_classical(item):
					continue
				if not self._deezer_raw_item_quiz_whitelist_artist_ok(item):
					continue
				rec = self._deezer_track_to_suggest_dict(item)
				if not rec:
					continue
				tid = str(rec.get("id") or "").strip()
				if not tid or tid in seen:
					continue
				seen.add(tid)
				out.append(rec)
		return out

	def _fetch_deezer_polish_popular_leading_pool(self, cap, year_filter, max_fetches=6):
		# Najważniejsze: zapytania pod „hity” + order=RANKING_DESC — wyniki bliżej przebojów niż losowa kolejność wyszukiwania.
		out = []
		seen = set()
		fetches = 0
		mf = max(1, min(int(max_fetches), 20))
		terms = list(QUIZ_POLISH_POPULAR_LEADING_TERMS)
		random.shuffle(terms)
		for term in terms:
			if len(out) >= cap or fetches >= mf:
				return out
			fetches = fetches + 1
			url = "https://api.deezer.com/search/track?" + urlencode(
				{"q": term, "limit": 50, "index": 0, "order": "RANKING_DESC"}
			)
			try:
				parsed = self._fetch_deezer_url_json(url)
			except Exception:
				continue
			for item in parsed.get("data") or []:
				if not self._deezer_raw_item_year_ok_quiz(item, year_filter):
					continue
				if not self._deezer_raw_item_accept_polish_quiz_pool(item):
					continue
				rec = self._deezer_track_to_suggest_dict(item)
				if not rec:
					continue
				tid = str(rec.get("id") or "").strip()
				if not tid or tid in seen:
					continue
				seen.add(tid)
				out.append(rec)
		return out

	def _fetch_deezer_polish_diverse_quiz_pool(self, cap, year_filter, max_fetches=18, search_indices=None):
		# Najważniejsze: rozne gatunki — kilka zapytan Deezer (limit HTTP, jedna strona wynikow na zapytanie).
		out = []
		seen = set()
		bases = ("https://api.deezer.com/search?", "https://api.deezer.com/search/track?")
		indices = search_indices if search_indices is not None else (0,)
		fetches = 0
		mf = max(6, min(int(max_fetches), 40))
		terms = list(QUIZ_POLISH_DIVERSE_DEEZER_QUERIES)
		random.shuffle(terms)
		for term in terms:
			for index in indices:
				for base in bases:
					if len(out) >= cap or fetches >= mf:
						return out
					fetches = fetches + 1
					url = base + urlencode({"q": term, "limit": 50, "index": index, "order": "RANKING_DESC"})
					try:
						parsed = self._fetch_deezer_url_json(url)
					except Exception:
						continue
					for item in parsed.get("data") or []:
						if not self._deezer_raw_item_year_ok_quiz(item, year_filter):
							continue
						if not self._deezer_raw_item_accept_polish_quiz_pool(item):
							continue
						rec = self._deezer_track_to_suggest_dict(item)
						if not rec:
							continue
						tid = str(rec.get("id") or "").strip()
						if not tid or tid in seen:
							continue
						seen.add(tid)
						out.append(rec)
		return out

	def _deezer_track_to_suggest_dict(self, item):
		preview = str(item.get("preview") or "").strip()
		if not preview:
			return None
		title = str(item.get("title") or "").strip()
		artist_name = str((item.get("artist") or {}).get("name") or "").strip()
		label = title
		if artist_name:
			label = title + " - " + artist_name
		try:
			rank_val = int(item.get("rank"))
		except Exception:
			rank_val = 0
		return {
			"id": str(item.get("id") or ""),
			"label": label[:120],
			"previewUrl": preview,
			"title": title[:80],
			"artist": artist_name[:80],
			"rank": rank_val,
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

	def _deezer_raw_item_likely_polish(self, item):
		# Najważniejsze: w podpowiedziach tylko polska scena — ISRC, polskie znaki, znani z puli lub z hints.
		try:
			isrc = str(item.get("isrc") or "").strip().upper()
		except Exception:
			isrc = ""
		if isrc.startswith("PL"):
			return True
		title = str(item.get("title") or "")
		artist_name = str((item.get("artist") or {}).get("name") or "")
		alb = str((item.get("album") or {}).get("title") or "")
		blob = title + " " + artist_name + " " + alb
		if _POLISH_DIACRITICS_RE.search(blob):
			return True
		an = _fold_text_answer(artist_name)
		ti = _fold_text_answer(title)
		comb = an + " " + ti
		for seed in POLISH_SCENE_ARTIST_SEEDS:
			fs = _fold_text_answer(seed)
			if len(fs) >= 3 and fs in an:
				return True
		for hint in SEARCH_POLISH_NAME_HINTS:
			fh = _fold_text_answer(hint)
			if len(fh) >= 5 and (fh in an or fh in ti or fh in comb):
				return True
		return False

	def _deezer_raw_item_quiz_block_foreign_classical(self, item):
		# Najważniejsze: wytnij zachodnią klasykę / „Danses roumaines” itp. (fałszywe trafienia z kompilacji PL).
		blob = _fold_text_answer(
			(str(item.get("title") or "")
			 + " "
			 + str((item.get("artist") or {}).get("name") or "")
			 + " "
			 + str((item.get("album") or {}).get("title") or ""))
		).lower()
		for needle in QUIZ_BLOCK_FOREIGN_CLASSICAL_NEEDLES:
			fn = _fold_text_answer(needle).lower()
			if len(fn) >= 4 and fn in blob:
				return True
		try:
			gid = int(item.get("genre_id") or 0)
		except Exception:
			gid = 0
		if gid == 132:
			return True
		return False

	def _deezer_raw_item_accept_polish_quiz_pool(self, item):
		# Najważniejsze: twardsza reguła niż wyszukiwarka — bez „polskości” tylko z pola album (importy z PL ISRC).
		if self._deezer_raw_item_quiz_block_foreign_classical(item):
			return False
		try:
			isrc = str(item.get("isrc") or "").strip().upper()
		except Exception:
			isrc = ""
		title = str(item.get("title") or "")
		artist_name = str((item.get("artist") or {}).get("name") or "")
		an = _fold_text_answer(artist_name)
		ti = _fold_text_answer(title)
		if _POLISH_DIACRITICS_RE.search(title + artist_name):
			return True
		if isrc.startswith("PL"):
			for seed in POLISH_SCENE_ARTIST_SEEDS:
				fs = _fold_text_answer(seed)
				if len(fs) >= 3 and fs in an:
					return True
			for hint in SEARCH_POLISH_NAME_HINTS:
				fh = _fold_text_answer(hint)
				if len(fh) >= 5 and (fh in an or fh in ti):
					return True
			return False
		for seed in POLISH_SCENE_ARTIST_SEEDS:
			fs = _fold_text_answer(seed)
			if len(fs) >= 3 and fs in an:
				return True
		for hint in SEARCH_POLISH_NAME_HINTS:
			fh = _fold_text_answer(hint)
			if len(fh) >= 5 and (fh in an or fh in ti):
				return True
		return False

	def _deezer_search_rank_score(self, term, item):
		# Najważniejsze: wyżej wyniki zgodne z tym, co wpisuje użytkownik (np. ten sam tytuł + rok w nazwie).
		ft = _fold_text_answer(term)
		if not ft:
			return 0
		title = _fold_text_answer(str(item.get("title") or ""))
		art = _fold_text_answer(str((item.get("artist") or {}).get("name") or ""))
		label = (title + " " + art).strip()
		score = 0
		if title.startswith(ft):
			score += 8000
		elif ft in title:
			score += 5000
		if ft in label:
			score += 2500
		prefix = ft[: min(len(ft), 14)]
		if len(prefix) >= 4 and title.startswith(prefix):
			score += 3500
		if not re.search(r"\d{4}", term) and re.search(r"20[12][0-9]", str(item.get("title") or "")):
			score += 400
		try:
			score += min(int(item.get("rank") or 0), 800000) // 2000
		except Exception:
			pass
		return score

	def _deezer_search_total_score(self, term, item):
		# Najważniejsze: polska scena na górze listy, ale bez odrzucania reszty wyników Deezera.
		boost = 400000 if self._deezer_raw_item_likely_polish(item) else 0
		return boost + self._deezer_search_rank_score(term, item)

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
			st_lim = min(100, max(50, limit * 4))
			search_url = "https://api.deezer.com/search/track?" + urlencode({"q": term, "limit": st_lim})
			search_parsed = self._fetch_deezer_url_json(search_url)
			for item in search_parsed.get("data") or []:
				push_item(item)
				if len(out) >= limit:
					return out[:limit]
		except Exception:
			pass
		try:
			top_url = "https://api.deezer.com/artist/%d/top?limit=50" % aid
			top_parsed = self._fetch_deezer_url_json(top_url)
			for item in top_parsed.get("data") or []:
				push_item(item)
				if len(out) >= limit:
					break
		except Exception:
			pass
		return out[:limit]

	def _fetch_deezer_tracks(self, term, limit, polish_only=False, order="RANKING_DESC", year_filter=None, quiz_pool_polish=False):
		out = []
		seen = set()
		lim = min(50, max(10, int(limit)))
		params = {"q": term, "limit": lim}
		if order:
			params["order"] = order
		for base in ("https://api.deezer.com/search?", "https://api.deezer.com/search/track?"):
			url = base + urlencode(params)
			try:
				parsed = self._fetch_deezer_url_json(url)
			except Exception:
				continue
			for item in parsed.get("data") or []:
				if not self._deezer_raw_item_year_ok_quiz(item, year_filter):
					continue
				if polish_only:
					if quiz_pool_polish:
						if not self._deezer_raw_item_accept_polish_quiz_pool(item):
							continue
					elif not self._deezer_raw_item_likely_polish(item):
						continue
				rec = self._deezer_track_to_suggest_dict(item)
				if not rec:
					continue
				tid = str(rec.get("id") or "").strip()
				if tid in seen:
					continue
				seen.add(tid)
				out.append(rec)
				if len(out) >= limit:
					return out
		return out

	def _fetch_deezer_chart_tracks(self, limit, polish_only=False, year_filter=None, quiz_pool_polish=False, quiz_pool_whitelist=False):
		# Najważniejsze: gdy search/pl scena nie zwraca nic (SSL/siec/region), chart 0 zwykle nadal ma preview.
		out = []
		seen = set()
		lim = min(100, max(5, int(limit)))
		parsed = self._fetch_deezer_url_json("https://api.deezer.com/chart/0/tracks?limit=%d" % lim)
		for item in parsed.get("data") or []:
			if not self._deezer_raw_item_year_ok_quiz(item, year_filter):
				continue
			if quiz_pool_whitelist:
				if self._deezer_raw_item_quiz_block_foreign_classical(item):
					continue
				if not self._deezer_raw_item_quiz_whitelist_artist_ok(item):
					continue
			elif polish_only:
				if quiz_pool_polish:
					if not self._deezer_raw_item_accept_polish_quiz_pool(item):
						continue
				elif not self._deezer_raw_item_likely_polish(item):
					continue
			rec = self._deezer_track_to_suggest_dict(item)
			if not rec:
				continue
			tid = str(rec.get("id") or "").strip()
			if not tid or tid in seen:
				continue
			seen.add(tid)
			out.append(rec)
			if len(out) >= lim:
				break
		return out

	def _deezer_search_push_unique_raw(self, item, seen_ids, bucket, max_total):
		tid = str(item.get("id") or "").strip()
		if not tid or tid in seen_ids:
			return False
		seen_ids.add(tid)
		bucket.append(item)
		return len(bucket) >= max_total

	def _deezer_search_fetch_track_query_pages(self, q, seen_ids, bucket, max_total, indexes):
		if len(bucket) >= max_total:
			return
		for index in indexes:
			if len(bucket) >= max_total:
				return
			url = "https://api.deezer.com/search/track?" + urlencode({"q": q, "limit": 50, "index": int(index)})
			try:
				parsed = self._fetch_deezer_url_json(url)
			except Exception:
				continue
			for item in parsed.get("data") or []:
				if self._deezer_search_push_unique_raw(item, seen_ids, bucket, max_total):
					return

	def handle_deezer_search_get(self, query_text):
		try:
			parsed_query = parse_qs(query_text or "")
			term = str((parsed_query.get("q") or [""])[0]).strip()
			if not term:
				self.json_response({"tracks": []}, 200)
				return
			limit = self._get_limit_from_query(query_text, 18)
			limit = min(max(int(limit), 5), 30)
			seen_ids = set()
			raw_bucket = []
			max_raw = 100

			# Najważniejsze: mało requestów do Deezera — druga strona i „polska” tylko gdy pierwsza strona jest uboga.
			self._deezer_search_fetch_track_query_pages(term, seen_ids, raw_bucket, max_raw, (0,))
			if len(raw_bucket) < 22:
				self._deezer_search_fetch_track_query_pages(term, seen_ids, raw_bucket, max_raw, (25,))
			if re.search(r"\d{4}", term) is None and len(raw_bucket) < 30:
				self._deezer_search_fetch_track_query_pages(term + " polska", seen_ids, raw_bucket, max_raw, (0,))
			if " - " in term:
				parts = term.split(" - ", 1)
				if len(parts) == 2:
					left = parts[0].strip()
					right = parts[1].strip()
					if left and right and len(raw_bucket) < 35:
						self._deezer_search_fetch_track_query_pages(right + " " + left, seen_ids, raw_bucket, max_raw, (0,))

			if len(raw_bucket) < 15 and " - " not in term:
				artist_id = self._deezer_try_resolve_artist_id(term)
				if artist_id is not None:
					try:
						top_url = "https://api.deezer.com/artist/%d/top?limit=40" % int(artist_id)
						top_parsed = self._fetch_deezer_url_json(top_url)
						for item in top_parsed.get("data") or []:
							self._deezer_search_push_unique_raw(item, seen_ids, raw_bucket, max_raw)
					except Exception:
						pass

			try:
				raw_bucket.sort(key=lambda it: self._deezer_search_total_score(term, it), reverse=True)
			except Exception:
				pass
			wl_raw = (parsed_query.get("whitelistOnly") or parsed_query.get("whitelist") or [""])[0]
			whitelist_only = str(wl_raw).strip().lower() in ("1", "true", "yes", "on")
			out = []
			for item in raw_bucket:
				if whitelist_only and not self._deezer_raw_item_quiz_whitelist_artist_ok(item):
					continue
				rec = self._deezer_track_to_suggest_dict(item)
				if not rec:
					continue
				out.append(rec)
				if len(out) >= limit:
					break
			self.json_response({"tracks": out}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_deezer_polish_hiphop_get(self, query_text):
		try:
			limit = self._get_limit_from_query(query_text, 30)
			tracks = self._fetch_deezer_tracks(DEEZER_POLISH_HIPHOP_QUERY, max(limit * 2, 30), polish_only=True)
			random.shuffle(tracks)
			self.json_response({"tracks": tracks[:limit]}, 200)
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
			if not raw:
				self.json_response({"error": "Empty body"}, 400)
				return
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
				self.json_response({"error": "Player identity mismatch — odswiez strone lub wybierz gracza ponownie"}, 403)
				return
			ready = self._sanitize_ready(parsed.get("ready"))
			if ready is None:
				self.json_response({"error": "Invalid ready value"}, 400)
				return
			BUZZER_STATE["quiz_ready_players"][key] = ready
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			# Najważniejsze: auto-start nie może zablokować zapisania Gotowy (Deezer / wyjątki).
			try:
				self._maybe_auto_start_quiz_when_all_ready()
			except Exception:
				pass
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
			# Najważniejsze: start reczny bez Gotowy; auto-start gdy wszyscy gotowi (_maybe_auto_start_quiz_when_all_ready).
			if not self._start_quiz_round_with_random_track():
				if self._quiz_round_limit_reached():
					self.json_response({"error": "Osiagnieto limit rund quizu (zwieksz limit lub zapisz ponownie)"}, 400)
					return
				msg = "No Deezer tracks available"
				detail = str(_DEEZER_LAST_FETCH_ERR or "").strip()
				if detail:
					msg = "%s — %s" % (msg, detail[:220])
				self.json_response({"error": msg}, 500)
				return
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_full_reset_post(self):
		# Najważniejsze: sobik — pełny reset quizu (punkty, limity, zawieszone tokeny); klient dostaje nowy quizSessionId.
		try:
			length = int(self.headers.get("Content-Length", "0"))
			raw = self.rfile.read(length)
			parsed = json.loads(raw.decode("utf-8"))
			if not isinstance(parsed, dict):
				self.json_response({"error": "Payload must be an object"}, 400)
				return
			name = self._sanitize_name(parsed.get("name"), "")
			if not self._is_video_controller(name):
				self.json_response({"error": "Only sobik can reset the full quiz session"}, 403)
				return
			with BUZZER_QUIZ_LOCK:
				self._ensure_round_started()
				self._ensure_scores_and_names()
				self._ensure_quiz_state()
				self._reset_full_quiz_session()
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_round_limit_post(self):
		# Najważniejsze: sobik ustawia ile utworów ma trwać sesja (0 = bez limitu); zapis zeruje licznik zagranych w tej sesji.
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
				self.json_response({"error": "Only sobik can set quiz round limit"}, 403)
				return
			try:
				n = int(parsed.get("roundLimit"))
			except (TypeError, ValueError):
				self.json_response({"error": "Invalid round limit"}, 400)
				return
			if n < 0:
				n = 0
			if n > 9999:
				n = 9999
			BUZZER_STATE["quiz_round_limit"] = n
			BUZZER_STATE["quiz_rounds_played"] = 0
			BUZZER_STATE["quiz_used_track_ids"] = []
			BUZZER_STATE["last_update_ms"] = self._now_ms()
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
			occupied = self._count_occupied_players()
			if occupied > 0 and self._count_finished_quiz_players() >= occupied:
				self._begin_quiz_reveal()
				BUZZER_STATE["last_update_ms"] = self._now_ms()
				self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
				return
			self._bump_quiz_listen_clip()
			BUZZER_STATE["last_update_ms"] = self._now_ms()
			self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_skip_phase_post(self):
		# Najważniejsze: gracz dobrowolnie przechodzi do dłuższej fazy bez wpisywania odpowiedzi (jak zła odpowiedź przed ostatnią fazą).
		try:
			with BUZZER_QUIZ_LOCK:
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
				if bool(BUZZER_STATE.get("quiz_reveal_active")):
					self.json_response({"error": "Reveal is active"}, 400)
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
				lp, cur, last_i = self._quiz_get_listen_phase_and_last(key)
				# Najważniejsze: na ostatniej fazie słuchania SKIP jest zablokowany — gracz musi zgadnąć (bez odpadu przez SKIP).
				if cur >= last_i:
					self.json_response(
						{"error": "Na ostatniej szansie nie mozna uzyc SKIP — trzeba zgadnac."},
						400,
					)
					return
				su = BUZZER_STATE.get("quiz_skips_used")
				if not isinstance(su, dict):
					BUZZER_STATE["quiz_skips_used"] = {}
					su = BUZZER_STATE["quiz_skips_used"]
				prev_skip = int(su.get(key, 0))
				if prev_skip >= QUIZ_MAX_SKIPS_PER_ROUND:
					self.json_response({"error": "Wykorzystales juz max skipow (4) w tej rundzie"}, 400)
					return
				su[key] = prev_skip + 1
				BUZZER_STATE["quiz_artist_hint_players"][key] = False
				self._append_quiz_guess_history(key, "SKIP", "skip")
				lp[key] = cur + 1
				self._bump_quiz_listen_for_player(key)
				if self._all_occupied_finished_song():
					self._begin_quiz_reveal()
				self.json_response({"ok": True, "skippedPhase": True, "state": self._public_buzzer_state()}, 200)
				return
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)

	def handle_quiz_guess_post(self):
		try:
			with BUZZER_QUIZ_LOCK:
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
					points = self._quiz_points_for_player_key(key)
					BUZZER_STATE["quiz_guessed_players"][key] = True
					BUZZER_STATE["scores"][key] = int(BUZZER_STATE["scores"].get(key, 0)) + points
					self._append_quiz_guess_history(key, guess, "correct")
					BUZZER_STATE["last_update_ms"] = self._now_ms()
					if self._all_occupied_finished_song():
						self._begin_quiz_reveal()
					self.json_response({"ok": True, "state": self._public_buzzer_state()}, 200)
					return
				if self._artist_only_matches_round(guess, title, artist):
					self._append_quiz_guess_history(key, guess, "artist_hint")
					BUZZER_STATE["quiz_artist_hint_players"][key] = True
					lp, cur, last_i = self._quiz_get_listen_phase_and_last(key)
					if cur < last_i:
						lp[key] = cur + 1
						self._bump_quiz_listen_for_player(key)
						if self._all_occupied_finished_song():
							self._begin_quiz_reveal()
						self.json_response({"ok": True, "artistHintOnly": True, "state": self._public_buzzer_state()}, 200)
						return
					# Najważniejsze: na ostatniej fazie sam artysta = odpad (wcześniej każde wysłanie podbijało listen_token w nieskończoność).
					BUZZER_STATE["quiz_artist_hint_players"][key] = False
					BUZZER_STATE["quiz_wrong_players"][key] = True
					prev = BUZZER_STATE["quiz_wrong_guesses"].get(key)
					if not isinstance(prev, list):
						prev = []
						BUZZER_STATE["quiz_wrong_guesses"][key] = prev
					prev.append(guess[:200])
					self._refresh_quiz_listen_duration_no_token()
					if self._all_occupied_finished_song():
						self._begin_quiz_reveal()
					self.json_response({"ok": True, "guessWrong": True, "artistHintLastPhase": True, "state": self._public_buzzer_state()}, 200)
					return
				BUZZER_STATE["quiz_artist_hint_players"][key] = False
				lp, cur, last_i = self._quiz_get_listen_phase_and_last(key)
				self._append_quiz_guess_history(key, guess, "wrong")
				if cur < last_i:
					lp[key] = cur + 1
					prev = BUZZER_STATE["quiz_wrong_guesses"].get(key)
					if not isinstance(prev, list):
						prev = []
						BUZZER_STATE["quiz_wrong_guesses"][key] = prev
					prev.append(guess[:200])
					self._bump_quiz_listen_for_player(key)
					if self._all_occupied_finished_song():
						self._begin_quiz_reveal()
					self.json_response({"ok": True, "guessWrong": True, "state": self._public_buzzer_state()}, 200)
					return
				BUZZER_STATE["quiz_wrong_players"][key] = True
				prev = BUZZER_STATE["quiz_wrong_guesses"].get(key)
				if not isinstance(prev, list):
					prev = []
					BUZZER_STATE["quiz_wrong_guesses"][key] = prev
				prev.append(guess[:200])
				BUZZER_STATE["last_update_ms"] = self._now_ms()
				self._bump_quiz_listen_clip()
				if self._all_occupied_finished_song():
					self._begin_quiz_reveal()
				self.json_response({"ok": True, "guessWrong": True, "state": self._public_buzzer_state()}, 200)
				return
		except Exception as ex:
			self.json_response({"error": str(ex)}, 500)


def _cancel_quiz_auto_next_timer_thread():
	global _QUIZ_AUTO_NEXT_TIMER
	if _QUIZ_AUTO_NEXT_TIMER is not None:
		try:
			_QUIZ_AUTO_NEXT_TIMER.cancel()
		except Exception:
			pass
	_QUIZ_AUTO_NEXT_TIMER = None


def cancel_quiz_auto_next_timer():
	_cancel_quiz_auto_next_timer_thread()
	BUZZER_STATE["quiz_reveal_pending_auto_next"] = False


def _quiz_auto_next_tick():
	global _QUIZ_AUTO_NEXT_TIMER
	_QUIZ_AUTO_NEXT_TIMER = None
	if not bool(BUZZER_STATE.get("quiz_reveal_pending_auto_next")):
		return
	BUZZER_STATE["quiz_reveal_pending_auto_next"] = False
	try:
		h = AppHandler.__new__(AppHandler)
		h._ensure_quiz_state()
		if not bool(BUZZER_STATE.get("quiz_reveal_active")):
			return
		if bool(BUZZER_STATE.get("quiz_round_active")):
			return
		if not h._start_quiz_round_with_random_track():
			BUZZER_STATE["last_update_ms"] = h._now_ms()
			# Najważniejsze: bez kolejnego utworu zamykamy ujawnienie, żeby UI nie zostawało na starym ekranie.
			BUZZER_STATE["quiz_reveal_active"] = False
			BUZZER_STATE["quiz_reveal_seek_middle"] = False
			BUZZER_STATE["quiz_phase_index"] = -1
			try:
				if h._quiz_round_limit_reached():
					sys.stderr.write("quiz_auto_next: osiagnieto limit rund quizu\n")
				else:
					sys.stderr.write(
						"quiz_auto_next: nie udalo sie wylosowac utworu (Deezer). Ostatni blad: %s\n"
						% (str(_DEEZER_LAST_FETCH_ERR or "").strip()[:300],)
					)
			except Exception:
				pass
			return
		BUZZER_STATE["last_update_ms"] = h._now_ms()
	except Exception as ex:
		try:
			sys.stderr.write("quiz_auto_next: %s\n" % (ex,))
		except Exception:
			pass


def schedule_quiz_auto_next_after_reveal():
	_cancel_quiz_auto_next_timer_thread()
	BUZZER_STATE["quiz_reveal_pending_auto_next"] = True
	delay = float(QUIZ_REVEAL_CLIP_SEC) + float(QUIZ_AFTER_REVEAL_NEXT_SEC)
	t = threading.Timer(delay, _quiz_auto_next_tick)
	t.daemon = True
	global _QUIZ_AUTO_NEXT_TIMER
	_QUIZ_AUTO_NEXT_TIMER = t
	t.start()


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
