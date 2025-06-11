import csv
import logging
from typing import Dict, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import httpx

BASE_URL = "https://ru.wikipedia.org/wiki/Категория:Животные_по_алфавиту"
TIMEOUT = 30
LOGGER_NAME = "ParseWikiLogger"
russian_letters = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class ParseWikiAnimals:
    def __init__(self, parse_only_russian_letters: bool = False):
        self.base_url: str = BASE_URL
        self.client = httpx.Client()
        self.logger = logging.getLogger(LOGGER_NAME)
        self.timeout: int = TIMEOUT

        self.pages_processed: int = 0
        self.letters_result: Dict[str, int] = {}

        # _only_russian отвечает за парсинг только русских животных
        # без латинских наименований
        self._only_russian = parse_only_russian_letters
        self._russian_letters = russian_letters

    def _get_soup(self, url: str) -> BeautifulSoup:
        response = self.client.get(url=url, timeout=self.timeout)
        response.raise_for_status()
        soup = BeautifulSoup(markup=response.text, features="lxml")
        return soup

    def _parse_page(self, soup: BeautifulSoup) -> None:
        """
        Парсинг страницы
        """
        category_div = soup.find("div", id="mw-pages")
        if not category_div:
            self.logger.warning("Не найден <div id='mw-pages'>")
            return

        content_div = category_div.find("div", class_="mw-content-ltr")
        if not content_div:
            self.logger.warning("Не найден блок .mw-content-ltr")
            return

        category_groups = content_div.find_all("div", attrs={"class": "mw-category-group"})

        for group in category_groups:
            letter_tag = group.find("h3")
            ul_tag = group.find("ul")
            if not (letter_tag and ul_tag):
                continue

            letter = letter_tag.text.strip()  # Получение буквы животного
            if self._only_russian:
                if letter.lower() not in self._russian_letters:
                    continue
            count = len(ul_tag.find_all("li"))  # Подсчёта количества

            self.letters_result[letter] = (
                self.letters_result.get(letter, 0) + count
            )

    def _next_page_url(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Получение ссылки на следующую страницу
        """
        link = soup.find('a', string='Следующая страница')
        if link and link.has_attr("href"):
            next_url = urljoin(self.base_url, link["href"])
            self.logger.debug("Следующая страница: %s", next_url)
            return next_url
        self.logger.debug("Ссылка «Следующая страница» не найдена")
        return None

    @property
    def total_animals(self) -> int:
        return sum(self.letters_result.values())

    def parse(self) -> None:
        """
        Парсинг каждой страницы и запись результатов в словарь
        """
        url = self.base_url
        while url:
            soup = self._get_soup(url=url)
            self._parse_page(soup=soup)
            self.pages_processed += 1
            url = self._next_page_url(soup)

        self.logger.info(
            "Готово: %d страниц, всего статей %d",
            self.pages_processed,
            self.total_animals,
        )

    def save_to_csv(self, path: str = "beasts.csv") -> None:
        """
        Сохраняем результат в CSV формате
        """
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for letter, count in self.letters_result.items():
                writer.writerow([letter, count])
        self.logger.info("Результат сохранён в %s", path)

class TestParseWikiAnimals:
    HTML_PARSE_1 = """
    <div id="mw-pages">
      <div class="mw-content-ltr">
        <div class="mw-category-group">
          <h3>А</h3>
          <ul>
            <li><a href="/wiki/Акула">Акула</a></li>
            <li><a href="/wiki/Амурский_тигр">Амурский тигр</a></li>
          </ul>
        </div>
        <div class="mw-category-group">
          <h3>Б</h3>
          <ul><li><a href="/wiki/Бобр">Бобр</a></li></ul>
        </div>
      </div>
    </div>
    """

    HTML_PARSE_ONLY_RU = """
    <div id="mw-pages">
      <div class="mw-content-ltr">
        <div class="mw-category-group">
          <h3>Б</h3>
          <ul><li><a href="/wiki/Бобр">Бобр</a></li></ul>
        </div>
        <div class="mw-category-group">
          <h3>C</h3>
          <ul><li><a href="/wiki/Camel">Camel</a></li></ul>
        </div>
      </div>
    </div>
    """

    HTML_NEXT_LINK = """
    <a href="/wiki/Категория:Животные_по_алфавиту?pagefrom=Page2">Следующая страница</a>
    """

    HTML_NO_NEXT = "<p>Конец списка</p>"

    @classmethod
    def test_parse_page(cls):
        tests_parse_page = [
            {
                'html': cls.HTML_PARSE_1,
                'kwargs': {'parse_only_russian_letters': False},
                'expected': {'А': 2, 'Б': 1},
            },
            {
                'html': cls.HTML_PARSE_ONLY_RU,
                'kwargs': {'parse_only_russian_letters': True},
                'expected': {'Б': 1},
            },
        ]

        for i, case in enumerate(tests_parse_page, 1):
            parser = ParseWikiAnimals(**case['kwargs'])
            soup = BeautifulSoup(case['html'], 'lxml')
            parser._parse_page(soup)
            assert parser.letters_result == case['expected'], (
                f'parse_page test {i} failed: {parser.letters_result=} != {case["expected"]=}'
            )
        print("parse_page: все тесты пройдены")

    @classmethod
    def test_next_link(cls):
        tests_next_link = [
            {
                'html': cls.HTML_NEXT_LINK,
                'expected': urljoin(
                    BASE_URL,
                    "/wiki/Категория:Животные_по_алфавиту?pagefrom=Page2",
                ),
            },
            {
                'html': cls.HTML_NO_NEXT,
                'expected': None,
            },
        ]

        for i, case in enumerate(tests_next_link, 1):
            parser = ParseWikiAnimals()
            soup = BeautifulSoup(case['html'], 'lxml')
            result = parser._next_page_url(soup)
            assert result == case['expected'], (
                f'next_page_url test {i} failed: {result=} != {case["expected"]=}'
            )
        print("next_page_url: все тесты пройдены")


if __name__ == "__main__":
    # setup_logging(logging.INFO)  # Настройка логгера
    #
    # parser = ParseWikiAnimals()  # Создание объекта парсера
    # parser.parse()  # Парсинг
    # parser.save_to_csv()  # Сохранение в csv
    #
    # print(f"Всего животных: {parser.total_animals}")


    # Тесты
    TestParseWikiAnimals.test_parse_page()
    TestParseWikiAnimals.test_next_link()
