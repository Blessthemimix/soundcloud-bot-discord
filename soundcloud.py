import discord
from discord.ext import commands
import yt_dlp
import asyncio
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ======================= НАСТРОЙКИ =======================
# !!! ЗАМЕНИТЕ ЭТО СВОИМ ТОКЕНОМ БОТА !!!
TOKEN = 'discord_token_bot'

# Префикс команды
PREFIX = '!self' 
# =========================================================

# Настройки для yt-dlp: максимально тихий поиск
ydl_opts = {
    # Мы не просим yt-dlp ничего скачивать, только извлекать информацию
    'quiet': True,
    'default_search': 'scsearch1', # Искать 1 результат на SoundCloud
    'extract_flat': True, # Быстрое извлечение, чтобы избежать ошибок 401 на первом этапе
    'skip_download': True,
    # Мы не указываем 'format' или 'bestaudio', чтобы не смущать yt-dlp
}

# Инициализация бота
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents) 

@bot.event
async def on_ready():
    print(f'Бот {bot.user} запущен и готов искать музыку! 🎧')

def get_soundcloud_link(query):
    """
    Выполняет поиск и возвращает URL страницы трека, используя yt-dlp в режиме поиска.
    """
    try:
        # В этом режиме yt-dlp гарантированно возвращает 'webpage_url'
        # который является чистым URL страницы трека.
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Используем extract_info для поиска
            info = ydl.extract_info(f"scsearch1:{query}", download=False)

        if 'entries' in info and len(info['entries']) > 0:
            first_result = info['entries'][0]
            
            # Мы берем 'webpage_url', потому что это URL страницы
            track_url = first_result.get('webpage_url') 
            
            # Если 'webpage_url' пуст (что маловероятно после поиска), пробуем 'url'
            if not track_url:
                track_url = first_result.get('url')
            
            track_title = first_result.get('title', 'Неизвестный трек')
            
            if track_url and "api.soundcloud.com" not in track_url:
                return track_title, track_url
            
            # Если даже так возвращается API-ссылка, это критическая проблема конфигурации
            if "api.soundcloud.com" in track_url:
                logging.error(f"yt-dlp вернул API-ссылку: {track_url}. Проблема в настройках extractor'а.")
                return track_title, None

        return None, None
        
    except Exception as e:
        logging.error(f"Ошибка в get_soundcloud_link: {e}")
        return None, None


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith(PREFIX):
        query = message.content[len(PREFIX):].strip() 
        
        if not query:
            return 

        status_msg = await message.channel.send(f"🔍 Ищу *{query}* на SoundCloud...")

        try:
            loop = asyncio.get_event_loop()
            track_title, track_url = await loop.run_in_executor(None, get_soundcloud_link, query)

            if track_url:
                await status_msg.delete()
                # Мы форсируем использование чистого URL страницы
                await message.channel.send(f"🎧 **Найдено:** {track_title}\n{track_url}")
            else:
                await status_msg.edit(content=f"❌ Ничего не найдено для '{query}' или произошла ошибка извлечения URL.")

        except Exception as e:
            logging.error(f"Критическая ошибка при обработке сообщения: {e}")
            await status_msg.edit(content="❌ Критическая ошибка при поиске. Проверьте консоль.")

    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(TOKEN)
