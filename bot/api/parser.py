import sys
from os import environ
from typing import Any, List, Dict, Optional, Union
from datetime import datetime, timezone
import time
from copy import copy

import aiohttp
import aiohttp.client_exceptions
import aiohttp.client_reqrep
from discord.ext.commands.bot import Bot
from dotenv import load_dotenv
import asyncio

from bot.colors import red, purple, yellow
from bot.constants import URL, timeout
from discord import Game,Status
OK=1
WARN=2
ERR=3


load_dotenv()
response_profile = Optional[List[Dict[str, Any]]]
response_profile_complete = Optional[Dict[str, Any]]
bot:Bot=None

ROOTME_ACCOUNT_LOGIN = environ.get('ROOTME_ACCOUNT_LOGIN')
ROOTME_ACCOUNT_PASSWORD = environ.get('ROOTME_ACCOUNT_PASSWORD')
ROOTME_API_KEY = environ.get('ROOTME_API_KEY')
SLEEP = int(environ.get('SLEEP_TIME'))

cookie_jar = aiohttp.CookieJar()
cookie_jar.update_cookies({"api_key": ROOTME_API_KEY})

current_status = ("",Status.offline)
latestchange= 0.0

async def get_cookies():
    async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
        await asyncio.sleep(SLEEP)
        data = dict(login=ROOTME_ACCOUNT_LOGIN, password=ROOTME_ACCOUNT_PASSWORD)
        try:
            async with session.post(f'{URL}/login', data=data, timeout=timeout) as response:
                print(response)
                if response.status == 200:
                    content = await response.json(content_type=None)
                    await bot_status(OK,"hacker Root-me")
                    return "Logged in"
                elif response.status == 429:   # Too Many requests
                    return await get_cookies()
                red('Wrong credentials.')
                sys.exit(0)
        except asyncio.TimeoutError:
            return await get_cookies()
        except:
            await bot_status(ERR,"💀 Unable to log-in")
            return await get_cookies()


async def get_status():
    await asyncio.sleep(SLEEP)
    async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
        try:
            async with session.get(f'{URL}/challenges', timeout=timeout) as response:
                if response.status == 429:
                    await bot_status(ERR,"kill le daemon discord en boucle")
                    return await get_status()
                await bot_status(OK,"Connecté")
                return response.status
        except asyncio.TimeoutError:
            await bot_status(ERR,"kill le daemon discord en boucle")
            return await get_status()
        except:
            await bot_status(ERR,"kill le daemon discord en boucle")
            return await get_status()


async def request_to(url: str) -> response_profile:
    await asyncio.sleep(SLEEP)
    async with aiohttp.ClientSession(cookie_jar=cookie_jar) as session:
        try:
            async with session.get(url, timeout=timeout) as response:
                print(response)
                #yellow("Session : " + str([c for c in session.cookie_jar]))
                if response.url.host not in URL:  # website page is returned not API (api.www.root-me.org / www.root-me.org)
                    return None
                #  purple(f'[{response.status}] {url}')
                if response.status == 200:
                    await bot_status(OK,"hacker Root-me")
                    return await response.json()
                elif response.status == 401:
                    await bot_status(ERR,"kill le daemon discord en boucle")
                    if await get_status() == 200:
                        purple(f'{url} -> probably a premium challenge')
                        return None
                    await get_cookies()
                    return await request_to(url)
                elif response.status == 429:   # Too Many requests
                    await bot_status(ERR,"kill le daemon discord en boucle")
                    return await request_to(url)
                else:
                    await bot_status(ERR,"Wtf ?")
                    return None
        except asyncio.TimeoutError:
            await bot_status(ERR,"kill le daemon discord en boucle")
            return await request_to(url)
        except Exception as e:
            print(e)
            await bot_status(ERR,"kill le daemon discord en boucle")
            return await request_to(url)


async def extract_json(url: str) -> response_profile:
    data = await request_to(url)
    if data is None:
        red(url)
    return data


class Parser:

    @staticmethod
    async def extract_rootme_profile(user: str, lang: str) -> response_profile:
        return await extract_json(f'{URL}/auteurs?nom={user}&lang={lang}')

    @staticmethod
    async def extract_rootme_profile_complete(id_user: int) -> response_profile_complete:
        return await extract_json(f'{URL}/auteurs/{id_user}')

    @staticmethod
    async def extract_challenges(lang: str) -> response_profile:
        return await extract_json(f'{URL}/challenges?lang={lang}')

    @staticmethod
    async def extract_challenges_by_page(page_num: int) -> response_profile:
        return await extract_json(f'{URL}/challenges?debut_challenges={page_num}')

    @staticmethod
    async def extract_challenge_info(id_challenge: Union[int, str]) -> response_profile_complete:
        return await extract_json(f'{URL}/challenges/{id_challenge}')

    @staticmethod
    async def find_challenge(challenge_title: str) -> response_profile_complete:
        return await extract_json(f'{URL}/challenges?titre={challenge_title}')

    @staticmethod
    async def make_custom_query(path: str) -> Any:
        return await extract_json(f'{URL}{path}')

    @staticmethod
    async def set_bot(b:Bot):
        global bot
        bot = b

async def bot_status(status:int, message: str):
    if bot is not None:
        global current_status
        global latestchange
        if current_status != (message,get_status(status)) and time.time()- latestchange > 10:
            current_status = (message,get_status(status))
            latestchange = time.time()
            try:
                await bot.change_presence(activity=Game(name=message, type=1),status=get_status(status))
            except:
                try:
                    await bot.change_presence(activity=Game(name=message, type=1),status=get_status(status))
                except:
                    return # anyway no updates
        

def get_status(status:int):
    if status == OK:
        return Status.online
    elif status == WARN:
        return Status.idle
    elif status == ERR:
        return Status.do_not_disturb