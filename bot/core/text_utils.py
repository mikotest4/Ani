from calendar import month_name
from datetime import datetime
from random import choice
from asyncio import sleep as asleep
from aiohttp import ClientSession
from anitopy import parse
import re

from bot import Var, bot
from .database import db
from .ffencoder import ffargs
from .func_utils import handle_logs
from .reporter import rep

CAPTION_FORMAT = """
<b>{title} </b>
<b>──────────────────────────── </b>
<b>➤ Season - 01 </b>
<b>➤ Episode - {ep_no} </b>
<b>➤ Quality: Multi [Sub] </b>
<b>──────────────────────────── </b>
"""
GENRES_EMOJI = {"Action": "👊", "Adventure": choice(['🪂', '🧗‍♀']), "Comedy": "🤣", "Drama": " 🎭", "Ecchi": choice(['💋', '🥵']), "Fantasy": choice(['🧞', '🧞‍♂', '🧞‍♀','🌗']), "Hentai": "🔞", "Horror": "☠", "Mahou Shoujo": "☯", "Mecha": "🤖", "Music": "🎸", "Mystery": "🔮", "Psychological": "♟", "Romance": "💞", "Sci-Fi": "🛸", "Slice of Life": choice(['☘','🍁']), "Sports": "⚽️", "Supernatural": "🫧", "Thriller": choice(['🗡', '🗂']), "School": choice(['🎒']), "Seinen": choice(['🧠', '🤔']), "Police": choice(['👮', '🚓']), "Shounen": "👦", "Shoujo": "👧", "Harem": choice(['💗', '😍']), "Reverse Harem": "💝", "Demons": "😈", "Vampire": "🧛", "Historical": "🏺", "Magic": "🪄"}

ANIME_GRAPHQL_QUERY = """
query ($id: Int, $search: String, $seasonYear: Int) {
  Media(id: $id, type: ANIME, format_not_in: [MOVIE, MUSIC, MANGA, NOVEL, ONE_SHOT], search: $search, seasonYear: $seasonYear) {
    id
    idMal
    title {
      romaji
      english
      native
    }
    type
    format
    status(version: 2)
    description(asHtml: false)
    startDate {
      year
      month
      day
    }
    endDate {
      year
      month
      day
    }
    season
    seasonYear
    episodes
    duration
    chapters
    volumes
    countryOfOrigin
    source
    hashtag
    trailer {
      id
      site
      thumbnail
    }
    updatedAt
    coverImage {
      large
    }
    bannerImage
    genres
    synonyms
    averageScore
    meanScore
    popularity
    trending
    favourites
    studios {
      nodes {
         name
         siteUrl
      }
    }
    isAdult
    nextAiringEpisode {
      airingAt
      timeUntilAiring
      episode
    }
    airingSchedule {
      edges {
        node {
          airingAt
          timeUntilAiring
          episode
        }
      }
    }
    externalLinks {
      url
      site
    }
    siteUrl
  }
}
"""

def format_custom_filename(custom_format: str, original_filename: str, anime_name: str) -> str:
    """
    Format custom filename using variables from the original filename
    
    Available variables:
    {season} - Season number (01, 02, etc.)
    {episode} - Episode number (01, 02, etc.)
    {title} - Clean anime title
    {quality} - Video quality (480, 720, 1080, Hdrip)
    {codec} - Video codec (HEVC, AV1, H.264, etc.)
    {lang} - Audio language (Sub, Multi-Audio, Dual, etc.)
    """
    try:
        # Parse the original filename to extract data
        pdata = parse(original_filename)
        
        # Extract information from original filename
        data = {
            'title': anime_name.replace(' ', '.'),
            'season': '01',
            'episode': '01',
            'quality': '1080',
            'codec': 'H.264',
            'lang': 'Sub'
        }
        
        # Use anitopy parsed data if available
        if pdata:
            if pdata.get('anime_season'):
                season_val = pdata.get('anime_season')
                if isinstance(season_val, list):
                    data['season'] = str(season_val[-1]).zfill(2)
                else:
                    data['season'] = str(season_val).zfill(2)
            
            if pdata.get('episode_number'):
                data['episode'] = str(pdata.get('episode_number')).zfill(2)
            
            if pdata.get('video_resolution'):
                resolution = pdata.get('video_resolution')
                data['quality'] = resolution.replace('p', '') if 'p' in resolution else resolution
        
        # Fallback: Extract season number from filename
        season_match = re.search(r'[Ss](\d{1,2})', original_filename)
        if season_match:
            data['season'] = season_match.group(1).zfill(2)
        
        # Fallback: Extract episode number from filename
        episode_patterns = [
            r'[Ee](\d{1,3})',  # E01, e12
            r'[Ee]pisode[.\s]*(\d{1,3})',  # Episode 01
            r'EP(\d{1,3})',  # EP01
        ]
        
        for pattern in episode_patterns:
            episode_match = re.search(pattern, original_filename)
            if episode_match:
                data['episode'] = episode_match.group(1).zfill(2)
                break
        
        # Extract quality
        quality_patterns = [
            r'(\d{3,4}p)',  # 1080p, 720p, 480p
            r'(HDRip|HDRIP)',  # HDRip
        ]
        
        for pattern in quality_patterns:
            quality_match = re.search(pattern, original_filename, re.IGNORECASE)
            if quality_match:
                quality = quality_match.group(1)
                if quality.lower() == 'hdrip':
                    data['quality'] = 'HDRip'
                else:
                    data['quality'] = quality.replace('p', '')
                break
        
        # Extract codec
        if 'HEVC' in original_filename or 'H.265' in original_filename or 'x265' in original_filename:
            data['codec'] = 'HEVC'
        elif 'H.264' in original_filename or 'x264' in original_filename:
            data['codec'] = 'H.264'
        elif 'AV1' in original_filename:
            data['codec'] = 'AV1'
        
        # Extract language/audio info
        if 'DUAL' in original_filename.upper() or 'Multi-Audio' in original_filename:
            data['lang'] = 'Multi-Audio'
        elif 'Multi' in original_filename and 'Sub' in original_filename:
            data['lang'] = 'Multi-Subs'
        
        # Replace variables in custom format
        formatted = custom_format
        for key, value in data.items():
            placeholder = "{" + key + "}"
            formatted = formatted.replace(placeholder, str(value))
        
        # Clean up any remaining placeholders that weren't replaced
        formatted = re.sub(r'\{[^}]+\}', '', formatted)
        
        # Clean up multiple spaces and special characters
        formatted = re.sub(r'\s+', ' ', formatted).strip()
        formatted = re.sub(r'[<>:"/\\|?*]', '', formatted)  # Remove invalid filename chars
        
        return formatted
        
    except Exception as e:
        # If formatting fails, return original filename
        return original_filename

class AniLister:
    def __init__(self, anime_name: str, year: int) -> None:
        self.__api = "https://graphql.anilist.co"
        self.__ani_name = anime_name
        self.__ani_year = year
        self.__vars = {'search' : self.__ani_name, 'seasonYear': self.__ani_year}
    
    def __update_vars(self, year=True) -> None:
        if year:
            self.__ani_year -= 1
            self.__vars['seasonYear'] = self.__ani_year
        else:
            self.__vars = {'search' : self.__ani_name}
    
    async def post_data(self):
        async with ClientSession() as sess:
            async with sess.post(self.__api, json={'query': ANIME_GRAPHQL_QUERY, 'variables': self.__vars}) as resp:
                return (resp.status, await resp.json(), resp.headers)
        
    async def get_anidata(self):
        res_code, resp_json, res_heads = await self.post_data()
        while res_code == 404 and self.__ani_year > 2020:
            self.__update_vars()
            await rep.report(f"AniList Query Name: {self.__ani_name}, Retrying with {self.__ani_year}", "warning", log=False)
            res_code, resp_json, res_heads = await self.post_data()
        
        if res_code == 404:
            self.__update_vars(year=False)
            res_code, resp_json, res_heads = await self.post_data()
        
        if res_code == 200:
            return resp_json.get('data', {}).get('Media', {}) or {}
        elif res_code == 429:
            f_timer = int(res_heads['Retry-After'])
            await rep.report(f"AniList API FloodWait: {res_code}, Sleeping for {f_timer} !!", "error")
            await asleep(f_timer)
            return await self.get_anidata()
        elif res_code in [500, 501, 502]:
            await rep.report(f"AniList Server API Error: {res_code}, Waiting 5s to Try Again !!", "error")
            await asleep(5)
            return await self.get_anidata()
        else:
            await rep.report(f"AniList API Error: {res_code}", "error", log=False)
            return {}
    
class TextEditor:
    def __init__(self, name):
        self.__name = name
        self.adata = {}
        self.pdata = parse(name)

    async def load_anilist(self):
        cache_names = []
        for option in [(False, False), (False, True), (True, False), (True, True)]:
            ani_name = await self.parse_name(*option)
            if ani_name in cache_names:
                continue
            cache_names.append(ani_name)
            self.adata = await AniLister(ani_name, datetime.now().year).get_anidata()
            if self.adata:
                break

    @handle_logs
    async def get_id(self):
        if (ani_id := self.adata.get('id')) and str(ani_id).isdigit():
            return ani_id
            
    @handle_logs
    async def parse_name(self, no_s=False, no_y=False):
        anime_name = self.pdata.get("anime_title")
        anime_season = self.pdata.get("anime_season")
        anime_year = self.pdata.get("anime_year")
        if anime_name:
            pname = anime_name
            if not no_s and self.pdata.get("episode_number") and anime_season:
                pname += f" {anime_season}"
            if not no_y and anime_year:
                pname += f" {anime_year}"
            return pname
        return anime_name
        
    @handle_logs
    async def get_poster(self):
        try:
            # Get all custom banners
            all_banners = await db.get_all_custom_banners()
            
            # Check if any custom banner name matches this torrent
            for banner in all_banners:
                banner_name = banner['anime_name']
                
                # Check if banner name is in torrent name OR torrent name is in banner name
                if (banner_name.lower() in self.__name.lower()) or (self.__name.lower() in banner_name.lower()):
                    await rep.report(f"✅ Using custom banner for: {banner_name}", "info")
                    return banner['banner_file_id']
            
            # Fallback to AniList poster
            if anime_id := await self.get_id():
                await rep.report(f"🎨 Using AniList poster for: {self.__name}", "info")
                return f"https://img.anili.st/media/{anime_id}"
            
            # Default fallback
            return "https://telegra.ph/file/112ec08e59e73b6189a20.jpg"
            
        except Exception as e:
            await rep.report(f"❌ Error getting poster: {str(e)}", "error")
            # Return default on error
            if anime_id := await self.get_id():
                return f"https://img.anili.st/media/{anime_id}"
            return "https://telegra.ph/file/112ec08e59e73b6189a20.jpg"
        
    @handle_logs
    async def get_upname(self, qual=""):
        try:
            # Check for custom filename format first
            custom_format = await db.get_custom_filename(self.__name)
            
            if custom_format:
                # Parse data for custom format
                anime_name = self.pdata.get("anime_title")
                titles = self.adata.get('title', {})
                clean_title = titles.get('english') or titles.get('romaji') or titles.get('native') or anime_name
                
                codec = 'HEVC' if 'libx265' in ffargs[qual] else 'AV1' if 'libaom-av1' in ffargs[qual] else ''
                lang = 'Multi-Audio' if 'multi-audio' in self.__name.lower() else 'Sub'
                anime_season = str(ani_s[-1]) if (ani_s := self.pdata.get('anime_season', '01')) and isinstance(ani_s, list) else str(ani_s or '01')
                episode_number = str(self.pdata.get("episode_number", "01")).zfill(2)
                
                # Replace variables in custom format
                formatted_name = custom_format.format(
                    season=anime_season.zfill(2),
                    episode=episode_number,
                    title=clean_title,
                    quality=qual,
                    codec=codec.upper(),
                    lang=lang,
                    brand=Var.BRAND_UNAME
                )
                
                await rep.report(f"✅ Using custom filename for: {anime_name}", "info")
                return formatted_name
            
            # Default filename format
            anime_name = self.pdata.get("anime_title")
            codec = 'HEVC' if 'libx265' in ffargs[qual] else 'AV1' if 'libaom-av1' in ffargs[qual] else ''
            lang = 'Multi-Audio' if 'multi-audio' in self.__name.lower() else 'Sub'
            anime_season = str(ani_s[-1]) if (ani_s := self.pdata.get('anime_season', '01')) and isinstance(ani_s, list) else str(ani_s or '01')
            
            if anime_name and self.pdata.get("episode_number"):
                titles = self.adata.get('title', {})
                clean_title = titles.get('english') or titles.get('romaji') or titles.get('native') or anime_name
                episode_number = str(self.pdata.get("episode_number")).zfill(2)
                
                return f"""[S{anime_season.zfill(2)}-E{episode_number}] {clean_title} {'['+qual+'p]' if qual else ''} {'['+codec.upper()+'] ' if codec else ''}{'['+lang+']'} {Var.BRAND_UNAME}.mkv"""
            
            # Fallback
            return f"{anime_name or 'Unknown'} [{qual}p] {Var.BRAND_UNAME}.mkv"
            
        except Exception as e:
            await rep.report(f"❌ Error generating filename: {str(e)}", "error")
            # Fallback to simple name
            anime_name = self.pdata.get("anime_title", "Unknown")
            return f"{anime_name} [{qual}p] {Var.BRAND_UNAME}.mkv"

    @handle_logs
    async def get_caption(self):
        sd = self.adata.get('startDate', {})
        startdate = f"{month_name[sd['month']]} {sd['day']}, {sd['year']}" if sd.get('day') and sd.get('year') else ""
        ed = self.adata.get('endDate', {})
        enddate = f"{month_name[ed['month']]} {ed['day']}, {ed['year']}" if ed.get('day') and ed.get('year') else ""
        titles = self.adata.get("title", {})
        
        return CAPTION_FORMAT.format(
                title=titles.get('english') or titles.get('romaji') or titles.get('native'),
                form=self.adata.get("format") or "N/A",
                genres=", ".join(f"{GENRES_EMOJI[x]} #{x.replace(' ', '_').replace('-', '_')}" for x in (self.adata.get('genres') or [])),
                avg_score=f"{sc}%" if (sc := self.adata.get('averageScore')) else "N/A",
                status=self.adata.get("status") or "N/A",
                start_date=startdate or "N/A",
                end_date=enddate or "N/A",
                t_eps=self.adata.get("episodes") or "N/A",
                plot= (desc if (desc := self.adata.get("description") or "N/A") and len(desc) < 200 else desc[:200] + "..."),
                ep_no=self.pdata.get("episode_number"),
                cred=Var.BRAND_UNAME,
            )
