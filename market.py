from collections import defaultdict
from enum import Enum
from typing import List

import pandas as pd
from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

AUCTIONS_URL_TEMPLATE = 'https://www.ezodus.net/auction'


class Skill(Enum):
    MAGIC = 'Magic'
    SHIELDING = 'Shielding'
    DISTANCE = 'Distance'
    CLUB = 'Club'
    SWORD = 'Sword'
    AXE = 'Axe'


class Profession(Enum):
    KNIGHT = 'Knight'
    SORCERER = 'Sorcerer'
    DRUID = 'Druid'
    PALADIN = 'Paladin'

    @staticmethod
    def find(text: str) -> 'Profession':
        return next(filter(lambda p: p.value in text, Profession.values()))

    @staticmethod
    def values():
        return [Profession.KNIGHT, Profession.SORCERER, Profession.DRUID, Profession.PALADIN]


class Character:
    def __init__(self, name: str, profession: Profession, lvl: int):
        self.name = name
        self.profession = profession
        self.lvl = lvl
        self.skills = {}

    def __str__(self):
        return f"Character({self.name}, {self.profession.value}, lvl={self.lvl}, skills={self.skills})"


class Auction:
    _NAME_ID = 0
    _LVL_PROFESSION_ID = 1
    _PRICE_ID = 2

    def __init__(self, character: Character, price: int):
        self.character = character
        self.price = price

    @staticmethod
    def create(row: WebElement) -> 'Auction':
        cols = row.find_elements_by_tag_name('td')
        name = cols[Auction._NAME_ID].text
        lvl_profession_raw: str = cols[Auction._LVL_PROFESSION_ID].text
        lvl = int(lvl_profession_raw.split(' ')[0])
        profession = Profession.find(lvl_profession_raw)
        character = Character(name, profession, lvl)
        price = int(str(cols[Auction._PRICE_ID].text).split(' ')[0])
        return Auction(character, price)


def find_auctions(browser: WebDriver) -> List[Auction]:
    browser.get(AUCTIONS_URL_TEMPLATE)
    table = browser.find_element_by_id('sellCharList')
    tbody = table.find_element_by_tag_name('tbody')
    rows = tbody.find_elements_by_tag_name('tr')
    return [Auction.create(row) for row in rows]


PROFESSION_SKILL_MAP = {
    Profession.DRUID: [Skill.MAGIC],
    Profession.SORCERER: [Skill.MAGIC],
    Profession.KNIGHT: [Skill.SWORD, Skill.AXE, Skill.CLUB],
    Profession.PALADIN: [Skill.DISTANCE, Skill.MAGIC],
}

SKILL_URL_MAP = {
    Skill.MAGIC: 'https://www.ezodus.net/charts/highscores/magic/all/{page}',
    Skill.SHIELDING: 'https://www.ezodus.net/charts/highscores/shielding/all/{page}',
    Skill.DISTANCE: 'https://www.ezodus.net/charts/highscores/distance/all/{page}',
    Skill.SWORD: 'https://www.ezodus.net/charts/highscores/sword/knight/{page}',
    Skill.AXE: 'https://www.ezodus.net/charts/highscores/axe/knight/{page}',
    Skill.CLUB: 'https://www.ezodus.net/charts/highscores/club/knight/{page}',
}

HIGHSCORES_NAME_ID = 1
HIGHSCORES_VALUE_ID = 2


def find_highscores_rows(browser: WebDriver) -> List[WebElement]:
    table = browser.find_element_by_class_name('gunz-table')
    tbody = table.find_element_by_tag_name('tbody')
    return tbody.find_elements_by_tag_name('tr')


def update_skills(browser: WebDriver, characters: List[Character]):
    character_map = {}
    character_skill_map = {}
    skill_character_map = defaultdict(set)
    for character in characters:
        character_map[character.name] = character
        skills = PROFESSION_SKILL_MAP.get(character.profession)
        character_skill_map[character.name] = skills
        for skill in skills:
            skill_character_map[skill].add(character.name)

    for skill, url in SKILL_URL_MAP.items():
        characters_to_update = skill_character_map.get(skill)
        if not characters_to_update:
            continue
        page_number = 0
        while True:
            page_url = url.replace('{page}', str(page_number))
            browser.get(page_url)
            rows = find_highscores_rows(browser)[1:]
            if len(rows) == 0:
                break
            for row in rows:
                cols = row.find_elements_by_tag_name('td')
                name = cols[HIGHSCORES_NAME_ID].find_element_by_tag_name('a').text
                value = int(cols[HIGHSCORES_VALUE_ID].text)
                if name in characters_to_update:
                    character = character_map.get(name)
                    character.skills[skill] = value
            page_number += 1


def save_auctions_to(auctions: List[Auction], excel_file: str = None, csv_file: str = None):
    headers = ['name', 'price', 'profession', 'lvl', 'sword', 'axe', 'club', 'dist', 'magic', 'shielding']

    def map_auction(auction: Auction) -> list:
        character = auction.character
        skills = character.skills
        return [
            character.name,
            auction.price,
            character.profession.name,
            character.lvl,
            skills.get(Skill.SWORD),
            skills.get(Skill.AXE),
            skills.get(Skill.CLUB),
            skills.get(Skill.DISTANCE),
            skills.get(Skill.MAGIC),
            skills.get(Skill.SHIELDING)
        ]

    data_frame = pd.DataFrame(
        list(map(map_auction, auctions)),
        columns=headers
    )
    if excel_file:
        data_frame.to_excel(excel_file)
    if csv_file:
        data_frame.to_csv(csv_file)
    if not csv_file and not excel_file:
        print(data_frame)


def main():
    browser = webdriver.Firefox(executable_path='geckodriver.exe')
    try:
        auctions = find_auctions(browser)
        characters = list(map(lambda a: a.character, auctions))
        update_skills(browser, characters)
        save_auctions_to(auctions, excel_file='auctions.xlsx', csv_file='auctions.csv')
    finally:
        browser.quit()


if __name__ == '__main__':
    main()
