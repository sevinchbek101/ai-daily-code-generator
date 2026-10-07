"""Har kuni yetti tilda o'quv kodlari yaratib, yopiq GitHub reposiga yuklaydi."""

from __future__ import annotations

import base64
import contextlib
import datetime as dt
import json
import os
import re
import secrets
import socket
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parent
CREDENTIALS_FILE = ROOT / "credentials.txt"
REPOSITORY_FILE = ROOT / "repository.txt"
LOCK_FILE = ROOT / ".dailycodeagent.lock"
CACHE_DIR = ROOT / ".dailycodeagent-cache"
GITHUB_API = "https://api.github.com"
GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GITHUB_API_VERSION = "2026-03-10"
FILES = {
    "php": ("php/main.php", "PHP"),
    "python": ("python/main.py", "Python"),
    "java": ("java/Main.java", "Java"),
    "javascript": ("javascript/main.js", "JavaScript"),
    "c": ("c/main.c", "C"),
    "csharp": ("csharp/Program.cs", "C#"),
    "cpp": ("cpp/main.cpp", "C++"),
}
TOPICS = ("algoritmlar", "ma'lumot tuzilmalari", "matn bilan ishlash", "kichik hisoblash dasturlari")
REQUIRED_SETTINGS = ("GITHUB_USERNAME", "GITHUB_TOKEN", "GEMINI_API_KEY", "COMMIT_EMAIL")


class AgentError(Exception):
    """Foydalanuvchiga xavfsiz ko'rsatiladigan xato."""


class HttpError(AgentError):
    def __init__(self, service: str, status: int, message: str):
        super().__init__(f"{service} xatosi ({status}): {message}")
        self.status = status


def load_credentials() -> dict[str, str]:
    if not CREDENTIALS_FILE.exists():
        raise AgentError("credentials.txt topilmadi.")
    values: dict[str, str] = {}
    for number, raw in enumerate(CREDENTIALS_FILE.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise AgentError(f"credentials.txt faylining {number}-qatori noto'g'ri.")
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    missing = [key for key in REQUIRED_SETTINGS if not values.get(key)]
    if missing:
        raise AgentError("credentials.txt faylida quyidagilarni to'ldiring: " + ", ".join(missing))
    values.setdefault("GEMINI_MODEL", "gemini-3.5-flash-lite")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", values["GITHUB_USERNAME"]):
        raise AgentError("GITHUB_USERNAME formati noto'g'ri.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", values["COMMIT_EMAIL"]):
        raise AgentError("COMMIT_EMAIL formati noto'g'ri.")
    return values


@contextlib.contextmanager
def single_instance() -> Iterator[None]:
    LOCK_FILE.touch(exist_ok=True)
    handle = LOCK_FILE.open("r+b")
    try:
        if os.name == "nt":
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise AgentError("Agentning boshqa nusxasi hozir ishlayapti.") from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise AgentError("Agentning boshqa nusxasi hozir ishlayapti.") from exc
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_UN)
        except OSError:
            pass
        handle.close()


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def safe_message(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"][:300]
        if isinstance(payload.get("message"), str):
            return payload["message"][:300]
    return fallback


def request_json(url: str, *, service: str, headers: dict[str, str], method: str = "GET",
                 payload: dict[str, Any] | None = None, allowed: tuple[int, ...] = (200, 201)) -> tuple[int, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
            result = json.loads(raw) if raw else {}
            if response.status not in allowed:
                raise HttpError(service, response.status, safe_message(result, "Noma'lum javob"))
            return response.status, result
    except urllib.error.HTTPError as exc:
        try:
            result = json.loads(exc.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            result = {}
        raise HttpError(service, exc.code, safe_message(result, exc.reason or "HTTP so'rovi bajarilmadi")) from None
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        reason = getattr(exc, "reason", exc)
        raise AgentError(f"{service} bilan aloqa o'rnatilmadi. Internetni tekshiring ({reason}).") from None
    except json.JSONDecodeError:
        raise AgentError(f"{service} tushunarsiz javob qaytardi.") from None


def github_request(config: dict[str, str], path: str, **kwargs: Any) -> tuple[int, Any]:
    headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {config['GITHUB_TOKEN']}",
               "X-GitHub-Api-Version": GITHUB_API_VERSION, "User-Agent": "DailyCodeAgent/1.0",
               "Content-Type": "application/json"}
    return request_json(GITHUB_API + path, service="GitHub API", headers=headers, **kwargs)


def verify_github_user(config: dict[str, str]) -> None:
    try:
        _, user = github_request(config, "/user")
    except HttpError as exc:
        if exc.status == 401:
            raise AgentError("GitHub tokeni noto'g'ri yoki muddati tugagan.") from None
        raise
    login = user.get("login", "")
    if login.casefold() != config["GITHUB_USERNAME"].casefold():
        raise AgentError(f"GitHub tokeni '{login}' egasiga tegishli, GITHUB_USERNAME esa boshqa foydalanuvchi.")


def parse_repository_url(text: str, username: str) -> tuple[str, str]:
    match = re.fullmatch(r"https://github\.com/([A-Za-z0-9-]+)/([A-Za-z0-9._-]+)", text.strip())
    if not match or match.group(1).casefold() != username.casefold():
        raise AgentError("repository.txt ichidagi GitHub manzili noto'g'ri.")
    return match.group(1), match.group(2)


def ensure_repository(config: dict[str, str]) -> tuple[str, str, str]:
    username = config["GITHUB_USERNAME"]
    if REPOSITORY_FILE.exists() and REPOSITORY_FILE.read_text(encoding="utf-8").strip():
        url = REPOSITORY_FILE.read_text(encoding="utf-8").strip()
        owner, repo = parse_repository_url(url, username)
    else:
        repo = "daily-code-" + secrets.token_hex(5)
        owner, url = username, f"https://github.com/{username}/{repo}"
        atomic_write(REPOSITORY_FILE, url + "\n")
    owner_q, repo_q = urllib.parse.quote(owner, safe=""), urllib.parse.quote(repo, safe="")
    try:
        _, info = github_request(config, f"/repos/{owner_q}/{repo_q}")
    except HttpError as exc:
        if exc.status != 404:
            raise
        try:
            _, info = github_request(config, "/user/repos", method="POST", payload={"name": repo,
                "description": "Har kunlik kichik dasturlash mashqlari", "private": True, "auto_init": False})
            print(f"Yopiq repozitoriy yaratildi: {url}")
        except HttpError as create_exc:
            if create_exc.status != 422:
                if create_exc.status == 403:
                    raise AgentError("GitHub tokenida private repo yaratish ruxsati yetarli emas.") from None
                raise
            _, info = github_request(config, f"/repos/{owner_q}/{repo_q}")
    if info.get("owner", {}).get("login", "").casefold() != username.casefold():
        raise AgentError("repository.txt dagi repo boshqa GitHub egasiga tegishli.")
    if info.get("private") is not True:
        raise AgentError("Xavfsizlik uchun to'xtatildi: GitHub repozitoriysi private emas.")
    return owner, repo, info.get("default_branch") or "main"


def generation_schema() -> dict[str, Any]:
    return {"type": "object", "properties": {key: {"type": "string"} for key in FILES},
            "required": list(FILES), "additionalProperties": False}


def extract_output_text(response: dict[str, Any]) -> str:
    candidates = response.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if isinstance(part.get("text"), str):
                return part["text"]
    block_reason = response.get("promptFeedback", {}).get("blockReason")
    if block_reason:
        raise AgentError(f"Gemini so'rovni xavfsizlik sababi bilan blokladi: {block_reason}.")
    raise AgentError("Gemini javobida yaratilgan kod topilmadi.")


def generate_codes(config: dict[str, str], date: dt.date) -> dict[str, str]:
    topic = TOPICS[date.toordinal() % len(TOPICS)]
    languages = ", ".join(label for _, label in FILES.values())
    prompt = f"""Sana: {date.isoformat()}. Mavzu: {topic}.
{languages} tillarining har biri uchun bittadan kichik va foydali o'quv dasturi yarating.
Har bir dastur mustaqil, to'liq ishlaydigan, tushunarli izohli va faqat standart kutubxonalarga asoslangan bo'lsin.
Har tilda bir xil vazifani ko'chirmang; mavzu doirasida turli kichik misollar bering.
Java kodi public class Main, C# kodi class Program bilan ishlasin.
Hech qanday API kaliti, token, parol yoki tashqi URL kiritmang.
JSON qiymatlarida faqat xom manba kodini qaytaring; Markdown code fence ishlatmang."""
    model = urllib.parse.quote(config["GEMINI_MODEL"], safe="-._")
    headers = {"x-goog-api-key": config["GEMINI_API_KEY"], "Content-Type": "application/json",
               "User-Agent": "DailyCodeAgent/1.0"}
    try:
        _, response = request_json(GEMINI_API.format(model=model), service="Gemini API", headers=headers,
            method="POST", payload={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseJsonSchema": generation_schema(),
                    "maxOutputTokens": 12000,
                    "thinkingConfig": {"thinkingLevel": "MINIMAL"},
                },
            })
    except HttpError as exc:
        if exc.status in (400, 401, 403):
            raise AgentError("Gemini API kaliti noto'g'ri, cheklangan yoki tanlangan modelga ruxsat yo'q.") from None
        if exc.status == 429:
            raise AgentError("Gemini bepul kunlik yoki tezlik limiti tugagan; keyinroq qayta urinib ko'ring.") from None
        raise
    try:
        codes = json.loads(extract_output_text(response))
    except json.JSONDecodeError:
        raise AgentError("Gemini kerakli JSON formatini qaytarmadi; keyinroq qayta urinib ko'ring.") from None
    validate_codes(codes)
    return codes


def validate_codes(codes: Any) -> None:
    if not isinstance(codes, dict) or set(codes) != set(FILES):
        raise AgentError("Gemini yetti tilning barchasi uchun kod qaytarmadi.")
    for key, code in codes.items():
        if not isinstance(code, str) or len(code.strip()) < 20:
            raise AgentError(f"Gemini {FILES[key][1]} uchun yaroqli kod qaytarmadi.")
        if "```" in code:
            raise AgentError(f"Gemini {FILES[key][1]} kodini noto'g'ri Markdown formatida qaytardi.")
    if not re.search(r"\bclass\s+Main\b", codes["java"]):
        raise AgentError("Java kodi Main klassini o'z ichiga olmaydi.")
    if not re.search(r"\bclass\s+Program\b", codes["csharp"]):
        raise AgentError("C# kodi Program klassini o'z ichiga olmaydi.")


def daily_paths(date: dt.date) -> dict[str, Path]:
    base = ROOT / "daily" / date.isoformat()
    return {key: base / relative for key, (relative, _) in FILES.items()}


def ensure_local_codes(config: dict[str, str], date: dt.date) -> dict[str, Path]:
    paths = daily_paths(date)
    present = {key for key, path in paths.items() if path.is_file() and path.stat().st_size > 0}
    if len(present) == len(paths):
        print("Bugungi kodlar mahalliy diskda mavjud; qayta generatsiya qilinmadi.")
        return paths
    cache_file = CACHE_DIR / f"{date.isoformat()}.json"
    if cache_file.exists():
        try:
            codes = json.loads(cache_file.read_text(encoding="utf-8"))
            validate_codes(codes)
        except (OSError, json.JSONDecodeError, AgentError):
            raise AgentError("Bugungi tiklash cache fayli yaroqsiz; uni qo'lda tekshiring.") from None
        print("Uzilishdan qolgan mahalliy cache ishlatildi; Gemini qayta chaqirilmadi.")
    elif present:
        missing = ", ".join(FILES[key][1] for key in paths if key not in present)
        raise AgentError("Bugungi mahalliy fayllar qisman mavjud, ammo tiklash cache topilmadi. "
                         f"Yetishmayotganlar: {missing}")
    else:
        print("Gemini orqali bugungi yetti dastur yaratilmoqda...")
        codes = generate_codes(config, date)
        atomic_write(cache_file, json.dumps(codes, ensure_ascii=False))
    for key, path in paths.items():
        if key not in present:
            atomic_write(path, codes[key].rstrip() + "\n")
    print("Bugungi 7 ta kod fayli mahalliy diskka saqlandi.")
    return paths


def contains_secret(content: str, config: dict[str, str]) -> bool:
    return any(value and len(value) >= 8 and value in content for key, value in config.items()
               if key.endswith("TOKEN") or key.endswith("KEY"))


def remote_content(config: dict[str, str], owner: str, repo: str, path: str) -> str | None:
    encoded = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
    try:
        _, item = github_request(config, f"/repos/{owner}/{repo}/contents/{encoded}")
    except HttpError as exc:
        if exc.status == 404:
            return None
        raise
    if item.get("type") != "file" or item.get("encoding") != "base64":
        raise AgentError(f"GitHub'dagi {path} oddiy fayl emas.")
    try:
        return base64.b64decode(item["content"], validate=True).decode("utf-8").replace("\r\n", "\n")
    except (KeyError, ValueError, UnicodeDecodeError):
        raise AgentError(f"GitHub'dagi {path} faylini tekshirib bo'lmadi.") from None


def remote_branch_exists(config: dict[str, str], owner: str, repo: str, branch: str) -> bool:
    encoded = urllib.parse.quote(branch, safe="")
    try:
        github_request(config, f"/repos/{owner}/{repo}/branches/{encoded}")
        return True
    except HttpError as exc:
        if exc.status == 404:
            return False
        raise


def upload_missing(config: dict[str, str], owner: str, repo: str, branch: str,
                   date: dt.date, paths: dict[str, Path]) -> int:
    uploaded = 0
    for key, local_path in paths.items():
        relative = f"daily/{date.isoformat()}/{FILES[key][0]}"
        content = local_path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if contains_secret(content, config):
            raise AgentError(f"Xavfsizlik uchun {relative} yuklanmadi: unda maxfiy qiymat topildi.")
        remote = remote_content(config, owner, repo, relative)
        if remote == content:
            continue
        if remote is not None:
            raise AgentError(f"GitHub'dagi {relative} mahalliy fayldan farq qiladi; avtomatik almashtirilmadi.")
        encoded = "/".join(urllib.parse.quote(part, safe="") for part in relative.split("/"))
        payload: dict[str, Any] = {
            "message": f"Add {FILES[key][1]} exercise for {date.isoformat()}",
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "committer": {"name": config["GITHUB_USERNAME"], "email": config["COMMIT_EMAIL"]},
            "author": {"name": config["GITHUB_USERNAME"], "email": config["COMMIT_EMAIL"]},
        }
        if uploaded or remote_branch_exists(config, owner, repo, branch):
            payload["branch"] = branch
        try:
            github_request(config, f"/repos/{owner}/{repo}/contents/{encoded}", method="PUT", payload=payload)
        except HttpError as exc:
            if exc.status == 422 and remote_content(config, owner, repo, relative) == content:
                continue
            if exc.status == 403:
                raise AgentError("GitHub tokenida repository Contents: write ruxsati yetarli emas.") from None
            raise
        uploaded += 1
        print(f"Yuklandi: {relative}")
    return uploaded


def run() -> None:
    with single_instance():
        config = load_credentials()
        verify_github_user(config)
        owner, repo, branch = ensure_repository(config)
        today = dt.datetime.now().astimezone().date()
        paths = ensure_local_codes(config, today)
        uploaded = upload_missing(config, owner, repo, branch, today, paths)
        if uploaded:
            print(f"Tayyor: {uploaded} ta yangi fayl GitHub'ga yuklandi.")
        else:
            print("Tayyor: bugungi barcha fayllar avval yuklangan, yangi commit yaratilmadi.")


def main() -> int:
    try:
        run()
        return 0
    except AgentError as exc:
        print(f"XATO: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("To'xtatildi.", file=sys.stderr)
        return 130
    except Exception:
        print("XATO: kutilmagan ichki xato. Maxfiy ma'lumotlarni himoyalash uchun tafsilotlar chiqarilmadi.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
