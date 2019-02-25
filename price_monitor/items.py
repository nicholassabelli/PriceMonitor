# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field
from scrapy.loader import ItemLoader
from scrapy.loader.processors import Identity, Join, MapCompose, TakeFirst
from w3lib.html import replace_escape_chars, remove_tags

class PriceCheckerItem(Item):
    # define the fields for your item here like:
    # name = Field()
    pass

class Price(Item):
    # Array indexes.
    KEY_AMOUNT = 'amount'
    KEY_CURRENCY = 'currency'

    # Fields.
    amount = Field()
    currency = Field()

class Product(Item):
    # Array indexes.
    KEY_NAME = 'name'
    KEY_DESCRIPTION = 'description'
    KEY_CURRENT_PRICE = 'currentPrice'
    KEY_URL = 'url'
    KEY_RELEASE_DATE = 'releaseDate'
    KEY_AVAILABILITY = 'availability'
    KEY_UPC = 'upc'
    KEY_TAGS = 'tags'
    KEY_BRAND = 'brand'
    KEY_LENGTH = 'length'
    KEY_WIDTH = 'width'
    KEY_HEIGHT = 'height'
    KEY_WEIGHT_OR_VOLUME = 'weightOrVolume'
    KEY_SIZE = 'size'

    # Fields.
    name = Field()
    description = Field()
    currentPrice = Field()
    url = Field()
    releaseDate = Field()
    availability = Field()
    upc = Field()
    tags = Field()
    brand = Field()
    length = Field()
    width = Field()
    height = Field()
    weightOrVolume = Field()
    size = Field()
    # soldby
    # images

class Food(Product):
    pass

class VideoGame(Product):
    # Fields.
    developers = Field()
    publishers = Field()
    platforms = Field()
    genres = Field()
    modes = Field()

def filter_price(value):
    if value.isdigit():
        return value

class PriceItemLoader(ItemLoader):
    default_input_processor = MapCompose(remove_tags)
    default_output_processor = TakeFirst()
    default_item_class = Price

class ProductItemLoader(ItemLoader):
    default_input_processor = MapCompose(remove_tags, replace_escape_chars)
    default_output_processor = TakeFirst()       # move to property to allow again
    default_item_class = Product
    currentPrice_in = Identity() # handle quebec prices
    # idk what that means

class IGAProductItemLoader(ProductItemLoader):
    default_input_processor = MapCompose(remove_tags, replace_escape_chars, lambda x: ' '.join(x.split()))

class MetroProductItemLoader(ProductItemLoader):
    tags_in = None
    tags_out = Identity()