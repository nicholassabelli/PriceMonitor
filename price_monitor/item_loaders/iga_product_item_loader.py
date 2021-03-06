# -*- coding: utf-8 -*-

from scrapy.loader.processors import MapCompose
from w3lib.html import replace_entities, replace_escape_chars, remove_tags
from price_monitor.item_loaders import product_item_loader
from price_monitor.helpers import input_processor_helper

class IGAProductItemLoader(product_item_loader.ProductItemLoader):
    default_input_processor = MapCompose(remove_tags, replace_escape_chars, replace_entities, input_processor_helper.InputProcessorHelper.remove_latin_space, lambda x: ' '.join(x.split()))