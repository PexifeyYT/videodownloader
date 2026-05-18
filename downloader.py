import requests
import os
import re
import pathlib

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    import instaloader
except ImportError:
    instaloader = None

try:
    import imageio_ffmpeg
    _FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    _FFMPEG = None


# ── Platform detection ────────────────────────────────────────────────────────

def detect_platform(url: str) -> str:
    if any(d in url for d in ("tiktok.com", "vm.tiktok.com", "vt.tiktok.com")):
        return "tiktok"
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "instagram.com" in url:
        return "instagram"
    return "unknown"


# ── TikTok ────────────────────────────────────────────────────────────────────

def _clean_name(title: str) -> str:
    cleaned = re.sub(r'[\\/*?:"<>|]', "", title).strip().replace(" ", "_")
    return cleaned[:100] if cleaned else "tiktok_video"


def download_tiktok(url: str, output_folder: str) -> tuple[bool, str, str]:
    try:
        resp = requests.get(f"https://www.tikwm.com/api/?url={url}", timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("data"):
            return False, f"API error: {data.get('msg', 'Unknown error')}", ""

        video_url = data["data"]["play"]
        title     = data["data"].get("title", "tiktok_video")
        filename  = _clean_name(title) + ".mp4"
        filepath  = os.path.join(output_folder, filename)

        counter = 1
        base = filepath
        while os.path.exists(filepath):
            name, ext = os.path.splitext(base)
            filepath = f"{name}_{counter}{ext}"
            counter += 1

        video_resp = requests.get(video_url, stream=True, timeout=60)
        video_resp.raise_for_status()

        os.makedirs(output_folder, exist_ok=True)
        with open(filepath, "wb") as f:
            for chunk in video_resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return True, os.path.basename(filepath), os.path.basename(filepath)

    except requests.exceptions.ConnectionError:
        return False, "Connection error — check internet", ""
    except requests.exceptions.Timeout:
        return False, "Request timed out", ""
    except requests.exceptions.HTTPError as e:
        return False, f"HTTP error: {e}", ""
    except KeyError as e:
        return False, f"Unexpected API response — missing key: {e}", ""
    except Exception as e:
        return False, f"Error: {e}", ""


# ── YouTube ───────────────────────────────────────────────────────────────────

def download_youtube(url: str, output_folder: str) -> tuple[bool, str, str]:
    if yt_dlp is None:
        return False, "yt-dlp not installed — run: pip install yt-dlp", ""
    try:
        os.makedirs(output_folder, exist_ok=True)
        before = set(os.listdir(output_folder))

        if _FFMPEG:
            fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        else:
            fmt = "best[ext=mp4]/best"

        ydl_opts = {
            "format": fmt,
            "outtmpl": os.path.join(output_folder, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
        }
        if _FFMPEG:
            ydl_opts["ffmpeg_location"] = _FFMPEG

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        after    = set(os.listdir(output_folder))
        new_files = [f for f in (after - before) if not f.endswith((".part", ".ytdl"))]
        mp4_files = [f for f in new_files if f.endswith(".mp4")]

        if mp4_files:
            return True, mp4_files[0], mp4_files[0]
        if new_files:
            return True, new_files[0], new_files[0]
        return False, "Download failed — no output file created", ""

    except yt_dlp.utils.DownloadError as e:
        return False, f"yt-dlp: {str(e)[:200]}", ""
    except Exception as e:
        return False, f"Error: {e}", ""


# ── Instagram ─────────────────────────────────────────────────────────────────

def download_instagram(url: str, output_folder: str) -> tuple[bool, str, str]:
    if instaloader is None:
        return False, "instaloader not installed — run: pip install instaloader", ""
    try:
        match = re.search(r"/(?:p|reel|tv)/([A-Za-z0-9_-]+)", url)
        if not match:
            return False, "Cannot parse Instagram URL — expected /p/, /reel/, or /tv/", ""
        shortcode = match.group(1)

        os.makedirs(output_folder, exist_ok=True)
        before = set(os.listdir(output_folder))

        L = instaloader.Instaloader(
            dirname_pattern=output_folder,
            filename_pattern=f"{shortcode}_{{date_utc}}_UTC",
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
        )

        post = instaloader.Post.from_shortcode(L.context, shortcode)
        L.download_post(post, target=pathlib.Path(output_folder))

        after    = set(os.listdir(output_folder))
        new_files = after - before
        videos    = [f for f in new_files if f.endswith(".mp4")]

        if videos:
            return True, videos[0], videos[0]
        if new_files:
            return True, list(new_files)[0], list(new_files)[0]
        return False, "No files downloaded", ""

    except instaloader.exceptions.InstaloaderException as e:
        return False, f"Instagram error: {e}", ""
    except Exception as e:
        return False, f"Error: {e}", ""


# ── Unified entry point ───────────────────────────────────────────────────────

def download_video(url: str, output_folder: str) -> tuple[tuple[bool, str, str], str]:
    platform = detect_platform(url)

    if platform == "tiktok":
        return download_tiktok(url, output_folder), platform
    if platform == "youtube":
        return download_youtube(url, output_folder), platform
    if platform == "instagram":
        return download_instagram(url, output_folder), platform

    return (False, "Unsupported URL — paste TikTok, YouTube, or Instagram link", ""), platform
