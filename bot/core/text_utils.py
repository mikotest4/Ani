import asyncio
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta
from time import time
import re
import json
import aiohttp

from bot import Var
from bot.core.database import db
from .reporter import rep

class TextEditor:
    def __init__(self, name):
        self.name = name
        self.info = {}
        self.adata = {}
        self.pdata = self.parse_name(name)

    async def load_anilist(self):
        """Load AniList data for the anime"""
        if self.pdata.get("episode_number"):
            self.adata = await self.get_ani_info()
        else:
            self.adata = {}

    def parse_name(self, name):
        """Parse anime name to extract episode and season info"""
        pdata = {"episode_number": None, "season": None}
        
        # Remove release group tags and quality info
        name = re.sub(r'\[.*?\]', '', name)
        name = re.sub(r'\(.*?\)', '', name)
        
        # Extract episode number
        episode_patterns = [
            r'[Ee](\d+)',
            r'Episode[\s\-]*(\d+)',
            r'Ep[\s\-]*(\d+)',
            r'\s(\d+)(?=\s|$|\.)',
            r'-\s*(\d+)\s*(?=\.|$)'
        ]
        
        for pattern in episode_patterns:
            episode_match = re.search(pattern, name)
            if episode_match:
                pdata["episode_number"] = int(episode_match.group(1))
                break
        
        # Extract season number
        season_patterns = [
            r'[Ss](\d+)',
            r'Season[\s\-]*(\d+)',
            r'S(\d+)E\d+'
        ]
        
        for pattern in season_patterns:
            season_match = re.search(pattern, name)
            if season_match:
                pdata["season"] = int(season_match.group(1))
                break
        
        # Default to season 1 if not found
        if not pdata["season"]:
            pdata["season"] = 1
            
        return pdata

    async def get_ani_info(self):
        """Get anime info from AniList API"""
        clean_name = self.clean_anime_name(self.name)
        
        query = """
        query ($search: String) {
            Media (search: $search, type: ANIME) {
                id
                title {
                    romaji
                    english
                    native
                }
                coverImage {
                    large
                    medium
                }
                bannerImage
                description
                episodes
                duration
                status
                genres
                averageScore
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
                studios {
                    nodes {
                        name
                    }
                }
            }
        }
        """
        
        variables = {"search": clean_name}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://graphql.anilist.co',
                    json={'query': query, 'variables': variables},
                    headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data', {}).get('Media', {})
                    else:
                        await rep.report(f"AniList API Error: {response.status}", "error")
                        return {}
        except Exception as e:
            await rep.report(f"AniList API Exception: {str(e)}", "error")
            return {}

    def clean_anime_name(self, name):
        """Clean anime name for AniList search"""
        # Remove common release group tags
        name = re.sub(r'\[.*?\]', '', name)
        name = re.sub(r'\(.*?\)', '', name)
        
        # Remove quality indicators
        name = re.sub(r'\b(1080p|720p|480p|HEVC|x264|x265|WEB-DL|BluRay|BDRip|DVDRip)\b', '', name, flags=re.IGNORECASE)
        
        # Remove episode/season info
        name = re.sub(r'[Ss]\d+[Ee]\d+', '', name)
        name = re.sub(r'[Ee]pisode?\s*\d+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[Ee]p?\s*\d+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'Season\s*\d+', '', name, flags=re.IGNORECASE)
        
        # Remove extra info
        name = re.sub(r'\b(DUAL|Multi|Sub|Dub|RAW)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\b(AAC|AC3|FLAC|DTS)\b', '', name, flags=re.IGNORECASE)
        
        # Clean up spaces and dashes
        name = re.sub(r'[-_\.]+', ' ', name)
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip()

    async def get_poster(self):
        """Get custom banner if available, otherwise AniList poster"""
        try:
            # First check for custom banner
            custom_banner = await db.get_custom_banner_by_name(self.name)
            if custom_banner:
                await rep.report(f"✅ Using custom banner for: {self.name}", "info")
                return custom_banner
            
            # Fallback to AniList poster
            if self.adata and self.adata.get('coverImage'):
                poster_url = self.adata['coverImage'].get('large') or self.adata['coverImage'].get('medium')
                if poster_url:
                    await rep.report(f"🎨 Using AniList poster for: {self.name}", "info")
                    return poster_url
            
            # Default fallback
            await rep.report(f"⚠️ No poster found for: {self.name}, using default", "warning")
            return "https://via.placeholder.com/400x600/1a1a1a/ffffff?text=No+Poster"
            
        except Exception as e:
            await rep.report(f"❌ Error getting poster: {str(e)}", "error")
            return "https://via.placeholder.com/400x600/1a1a1a/ffffff?text=Error"

    async def get_banner(self):
        """Get custom banner if available, otherwise AniList banner"""
        try:
            # First check for custom banner
            custom_banner = await db.get_custom_banner_by_name(self.name)
            if custom_banner:
                return custom_banner
            
            # Fallback to AniList banner
            if self.adata and self.adata.get('bannerImage'):
                return self.adata['bannerImage']
            
            # Fallback to poster if no banner
            return await self.get_poster()
            
        except Exception as e:
            await rep.report(f"Error getting banner: {str(e)}", "error")
            return await self.get_poster()

    async def get_caption(self):
        """Generate caption for anime post"""
        if not self.adata:
            return f"<b>{self.name}</b>"
        
        titles = self.adata.get("title", {})
        title = titles.get('english') or titles.get('romaji') or titles.get('native') or "Unknown Title"
        
        # Format episode info
        episode_info = f"Episode {self.pdata.get('episode_number', 1):02d}"
        if self.pdata.get('season') and self.pdata['season'] > 1:
            episode_info = f"S{self.pdata['season']:02d}E{self.pdata.get('episode_number', 1):02d}"
        
        # Get additional info
        genres = ", ".join(self.adata.get('genres', [])[:3])
        score = self.adata.get('averageScore', 0)
        
        # Build caption
        caption = f"<b>{title}</b>\n"
        caption += f"<b>──────────────────────────────</b>\n"
        caption += f"<b>➤ {episode_info}</b>\n"
        if genres:
            caption += f"<b>➤ Genres:</b> {genres}\n"
        if score:
            caption += f"<b>➤ Score:</b> {score}/100\n"
        caption += f"<b>────────────────────────────</b>"
        
        return caption

    async def get_upname(self, quality):
        """Generate upload filename"""
        if not self.adata:
            return f"{self.name} [{quality}].mkv"
        
        titles = self.adata.get("title", {})
        title = titles.get('english') or titles.get('romaji') or "Unknown"
        
        # Clean title for filename
        title = re.sub(r'[<>:"/\\|?*]', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Format episode
        episode = f"E{self.pdata.get('episode_number', 1):02d}"
        if self.pdata.get('season') and self.pdata['season'] > 1:
            episode = f"S{self.pdata['season']:02d}E{self.pdata.get('episode_number', 1):02d}"
        
        return f"{title} {episode} [{quality}].mkv"

    def get_episode_info(self):
        """Get formatted episode information"""
        info = {
            'season': f"{self.pdata.get('season', 1):02d}",
            'episode': f"{self.pdata.get('episode_number', 1):02d}",
            'quality': 'Multi [Sub]',
            'codec': 'H.264'
        }
        
        # Extract quality from name
        if '1080p' in self.name.upper():
            info['quality'] = '1080p [Sub]'
        elif '720p' in self.name.upper():
            info['quality'] = '720p [Sub]'
        elif '480p' in self.name.upper():
            info['quality'] = '480p [Sub]'
        elif 'HEVC' in self.name.upper():
            info['quality'] = 'HEVC [Sub]'
            info['codec'] = 'H.265'
        
        return info

    def get_clean_title(self):
        """Get clean anime title from AniList data or cleaned name"""
        if self.adata:
            titles = self.adata.get("title", {})
            return titles.get('english') or titles.get('romaji') or titles.get('native') or self.clean_anime_name(self.name)
        return self.clean_anime_name(self.name)

    def extract_episode_info_from_name(self, anime_title):
        """Extract episode, season and quality info from anime title"""
        info = {
            'season': '01',
            'episode': '01',
            'quality': 'Multi [Sub]',
            'codec': 'H.264'
        }
        
        # Extract season
        season_match = re.search(r'[Ss](\d+)', anime_title)
        if season_match:
            info['season'] = season_match.group(1).zfill(2)
        
        # Extract episode
        episode_patterns = [
            r'[Ee](\d+)',
            r'Episode[\s\-]*(\d+)',
            r'Ep[\s\-]*(\d+)',
            r'\s(\d+)\s',
            r'-\s*(\d+)\s*-'
        ]
        
        for pattern in episode_patterns:
            episode_match = re.search(pattern, anime_title)
            if episode_match:
                info['episode'] = episode_match.group(1).zfill(2)
                break
        
        # Extract quality
        if '1080p' in anime_title.upper():
            info['quality'] = '1080p [Sub]'
        elif '720p' in anime_title.upper():
            info['quality'] = '720p [Sub]'
        elif '480p' in anime_title.upper():
            info['quality'] = '480p [Sub]'
        elif 'HEVC' in anime_title.upper():
            info['quality'] = 'HEVC [Sub]'
            info['codec'] = 'H.265'
        
        return info

    async def get_description(self):
        """Get anime description"""
        if self.adata and self.adata.get('description'):
            # Clean HTML tags from description
            description = re.sub('<.*?>', '', self.adata['description'])
            # Limit description length
            if len(description) > 200:
                description = description[:200] + "..."
            return description
        return "No description available."

    async def get_studio(self):
        """Get anime studio"""
        if self.adata and self.adata.get('studios') and self.adata['studios'].get('nodes'):
            studios = [studio['name'] for studio in self.adata['studios']['nodes']]
            return ", ".join(studios[:2])  # Limit to 2 studios
        return "Unknown Studio"

    async def get_status(self):
        """Get anime status"""
        if self.adata:
            return self.adata.get('status', 'Unknown').replace('_', ' ').title()
        return "Unknown"

    async def get_year(self):
        """Get anime year"""
        if self.adata and self.adata.get('startDate') and self.adata['startDate'].get('year'):
            return str(self.adata['startDate']['year'])
        return "Unknown"

    async def format_summary_caption(self):
        """Format caption for main channel summary"""
        try:
            # Get clean title
            clean_title = self.get_clean_title()
            
            # Get episode info
            episode_info = self.get_episode_info()
            
            # Create summary caption
            caption = f"<b>{clean_title}</b>\n"
            caption += f"<b>──────────────────────────────</b>\n"
            caption += f"<b>➤ Season - {episode_info['season']}</b>\n"
            caption += f"<b>➤ Episode - {episode_info['episode']}</b>\n"
            caption += f"<b>➤ Quality: {episode_info['quality']}</b>\n"
            caption += f"<b>────────────────────────────</b>"
            
            return caption
            
        except Exception as e:
            await rep.report(f"Error formatting summary caption: {str(e)}", "error")
            return f"<b>{self.name}</b>"
