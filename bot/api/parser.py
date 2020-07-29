import sys
from os import environ
from typing import Any, List, Dict, Optional, Union
from datetime import datetime, timezone
from dateutil import parser as dateutil
from copy import copy

import aiohttp
import aiohttp.client_exceptions
import aiohttp.client_reqrep
from dotenv import load_dotenv
import asyncio

from bot.colors import red, purple, yellow
from bot.constants import URL, timeout

load_dotenv()
response_profile = Optional[List[Dict[str, Any]]]
response_profile_complete = Optional[Dict[str, Any]]

ROOTME_ACCOUNT_LOGIN = environ.get('ROOTME_ACCOUNT_LOGIN')
ROOTME_ACCOUNT_PASSWORD = environ.get('ROOTME_ACCOUNT_PASSWORD')
cookies = {}


client_session = None
def get_client_session():
    global client_session
    if client_session is None or type(client_session) != aiohttp.ClientSession:
        client_session = aiohttp.ClientSession()
    else:
        exp = None
        for c in client_session.cookie_jar:
            if c.key == "uid":
                exp = c["expires"]
                cookie = c
        
        client_session = aiohttp.ClientSession()
        if exp is not None:
            exp = dateutil.parse(exp)
            if exp > datetime.now(timezone.utc):
                client_session.cookie_jar.update_cookies({"uid": cookie})

    return client_session


async def get_cookies():
    async with get_client_session() as session:
        await asyncio.sleep(1.2)
        data = dict(login=ROOTME_ACCOUNT_LOGIN, password=ROOTME_ACCOUNT_PASSWORD)
        try:
            async with session.post(f'{URL}/login', data=data, timeout=timeout) as response:
                print(response)
                if response.status == 200:
                    content = await response.json(content_type=None)
                    return dict(spip_session=content[0]['info']['spip_session'])
                elif response.status == 429:   # Too Many requests
                    return await get_cookies()
                red('Wrong credentials.')
                sys.exit(0)
        except asyncio.TimeoutError:
            return await get_cookies()


async def get_status():
    global cookies
    await asyncio.sleep(1.2)
    async with get_client_session() as session:
        try:
            async with session.get(f'{URL}/challenges', cookies=cookies, timeout=timeout) as response:
                if response.status == 429:
                    return await get_status()
                return response.status
        except asyncio.TimeoutError:
            return await get_status()


async def request_to(url: str) -> response_profile:
    global cookies
    print(cookies)
    
    await asyncio.sleep(1.2)
    async with get_client_session() as session:
        try:
            async with session.get(url, cookies=cookies, timeout=timeout) as response:
                print(response)
                yellow("Session : " + str([c for c in session.cookie_jar]))
                if response.url.host not in URL:  # website page is returned not API (api.www.root-me.org / www.root-me.org)
                    return None
                #  purple(f'[{response.status}] {url}')
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    if await get_status() == 200:
                        purple(f'{url} -> probably a premium challenge')
                        return None
                    cookies = await get_cookies()
                    return await request_to(url)
                elif response.status == 429:   # Too Many requests
                    return await request_to(url)
                else:
                    return None
        except asyncio.TimeoutError:
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
