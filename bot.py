from io import BytesIO

from PIL import Image
from discord.ext import commands
from discord.ext.commands import CommandError
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

import utils
from config import ADMINS_PATH, BLACKLIST_PATH, CMD_PREFIX


def load_blacklist() -> dict:
    return utils.load_json(BLACKLIST_PATH, {})


class Blacklist:
    blacklist = load_blacklist()

    def __init__(self, bot):
        self.bot = bot

    def save_blacklist(self):
        utils.save_json(self.blacklist, BLACKLIST_PATH)

    def reload(self):
        self.blacklist = load_blacklist()

    def get_blacklist_for_guild(self, guild_id: str) -> list:
        return self.blacklist.get(str(guild_id), [])

    def add_user_to_blacklist(self, user_id: str, guild_id: str):
        self.blacklist[str(guild_id)] = self.blacklist.get(str(guild_id), []) + [str(user_id)]
        self.save_blacklist()

    def remove_user_from_blacklist(self, user_id: str, guild_id: str):
        self.blacklist[str(guild_id)] = [x for x in self.blacklist.get(str(guild_id)) if x != str(user_id)]
        self.save_blacklist()

    async def is_blacklisted(self, ctx):
        is_blacklisted = str(ctx.author.id) in self.get_blacklist_for_guild(ctx.guild.id)
        if not await self.bot.is_owner(ctx.author) and is_blacklisted:
            raise CommandError("You are blacklisted.")

        return True


def load_admins() -> dict:
    return utils.load_json(ADMINS_PATH, {})


class Admins:
    admins = load_admins()

    def __init__(self, bot):
        self.bot = bot

    def save_admins(self):
        utils.save_json(self.admins, ADMINS_PATH)

    def reload(self):
        self.admins = load_admins()

    def get_admins_for_guild(self, guild_id: str) -> list:
        return self.admins.get(str(guild_id), [])

    def add_user_to_admins(self, user_id: str, guild_id: str):
        self.admins[str(guild_id)] = self.admins.get(str(guild_id), []) + [str(user_id)]
        self.save_admins()

    def remove_user_from_admins(self, user_id: str, guild_id: str):
        self.admins[str(guild_id)] = [x for x in self.admins.get(str(guild_id)) if x != str(user_id)]
        self.save_admins()

    async def verify_admin(self, ctx):
        is_admin = str(ctx.author.id) in self.get_admins_for_guild(ctx.guild.id)
        if not await self.bot.is_owner(ctx.author) and not is_admin:
            raise CommandError("You need to be an admin to use this command.")

        return True


class Driver:
    def __init__(self):
        # Setup chrome options
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')

        # Remove unwanted logs
        # chrome_options.add_argument("--log-level=3")
        self.driver = webdriver.Chrome(options = chrome_options)

    def get(self, url: str) -> None:
        """ Loads a given url with the chromedriver. """
        self.driver.get(url)

    def get_html(self, url: str = None) -> str:
        """ Gets the page source of a given url or the current page. """
        if url is not None:
            self.driver.get(url)

        return self.driver.page_source

    def wait_for(self, css_selector: str, wait_time: int) -> bool:
        """ Waits for an element to be loaded or become visible on the webpage.

        :param css_selector: The css selector to locate the target element.
        """
        try:
            wait = WebDriverWait(self.driver, wait_time)
            wait.until(ec.visibility_of_element_located((By.CSS_SELECTOR, css_selector)))
            return True

        except TimeoutException:
            return False

    def find_element(self, css_selector: str, wait_time: int = 10):
        """ Finds a single element on a webpage using a css selector.

        :param css_selector: The css selector to locate the target element.
        :param wait_time: The time for the driver to wait for the element to load.
        :return: Single html element that matches the provided css selector.
        """
        # Wait for the element to be loaded
        wait = self.wait_for(css_selector, wait_time)

        return self.driver.find_element_by_css_selector(css_selector) if wait else None

    def load_html_content(self, html_content: str):
        self.driver.get("data:text/html;charset=utf-8,{html_content}".format(html_content = html_content))

    def screenshot_element(self, css_selector: str):
        element = self.find_element(css_selector)  # find part of the page you want image of
        location, size = element.location, element.size
        png = self.driver.get_screenshot_as_png()  # saves screenshot of entire page

        im = Image.open(BytesIO(png))  # uses PIL library to open image in memory
        left, top = location['x'], location['y']
        right, bottom = left + size['width'], top + size['height']

        im = im.crop((left, top, right, bottom))  # defines crop points
        im.save('screenshot.png')  # saves new cropped image


class Bot(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(commands.when_mentioned_or(CMD_PREFIX))
        self.driver = Driver()
        self.blacklist = Blacklist(self)
        self.admins = Admins(self)