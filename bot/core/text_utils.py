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

    async def get_description(self):
        """Get anime description"""
        if not self.adata or not self.adata.get('description'):
            return "No description available."
        
        # Clean HTML tags from description
        description = re.sub(r'<[^>]+>', '', self.adata['description'])
        
        # Truncate if too long
        if len(description) > 300:
            description = description[:300] + "..."
        
        return description

    async def get_studio(self):
        """Get anime studio"""
        if not self.adata or not self.adata.get('studios', {}).get('nodes'):
            return "Unknown Studio"
        
        studios = [node['name'] for node in self.adata['studios']['nodes']]
        return ", ".join(studios[:2])  # Show max 2 studios

    async def get_status(self):
        """Get anime status"""
        if not self.adata:
            return "Unknown"
        
        status = self.adata.get('status', 'Unknown')
        status_map = {
            'FINISHED': 'Completed',
            'RELEASING': 'Ongoing',
            'NOT_YET_RELEASED': 'Upcoming',
            'CANCELLED': 'Cancelled',
            'HIATUS': 'Hiatus'
        }
        
        return status_map.get(status, status)

    async def get_year(self):
        """Get anime release year"""
        if not self.adata or not self.adata.get('startDate'):
            return None
        
        return self.adata['startDate'].get('year')

    async def get_full_info(self):
        """Get comprehensive anime info"""
        if not self.adata:
            return {"title": self.name, "poster": await self.get_poster()}
        
        titles = self.adata.get("title", {})
        
        return {
            "id": self.adata.get('id'),
            "title": {
                "english": titles.get('english'),
                "romaji": titles.get('romaji'),
                "native": titles.get('native')
            },
            "poster": await self.get_poster(),
            "banner": await self.get_banner(),
            "description": await self.get_description(),
            "episodes": self.adata.get('episodes'),
            "duration": self.adata.get('duration'),
            "status": await self.get_status(),
            "genres": self.adata.get('genres', []),
            "score": self.adata.get('averageScore'),
            "year": await self.get_year(),
            "studio": await self.get_studio(),
            "episode_info": self.pdata
        }
