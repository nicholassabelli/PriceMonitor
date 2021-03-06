import logging
import pymongo
import re
from datetime import datetime
from scrapy.utils.project import get_project_settings
from typing import (
    Dict, 
    List,
    Optional,
    Union,
)
from price_monitor.items import (
    offer,
    product,
    product_data,
    store_item,
)
from price_monitor.models import (
    language,
)

class MongoDBPipeline(object):
    def __init__(self):
        settings = get_project_settings()
        connection = pymongo.MongoClient(
            settings.get('MONGODB_SERVER'),
            settings.get('MONGODB_PORT'),
        )
        db = connection[settings.get('MONGODB_DB')]
        self.products_collection = db[settings.get('MONGODB_COLLECTION_PRODUCTS')]
        self.offers_collection = db[settings.get('MONGODB_COLLECTION_OFFERS')]
        self.stores_collection = db[settings.get('MONGODB_COLLECTION_STORES')]

    def process_item(self, item, spider):
        product_dictionary = item.get_dictionary()
    
        # TODO: Add methods to item.

        # TODO: Handle errors.

        # Extract sub dictionaries to new collections and modify dictionaries.
        offer_dictionary = product_dictionary.pop(
            product.Product.KEY_CURRENT_OFFER,
            None,
        )
        store_dictionary = product_dictionary.pop(
            product.Product.KEY_STORE,
            None,
        )
        product_data_dictionary = product_dictionary.pop(
            product.Product.KEY_PRODUCT_DATA,
            None,
        )
        store_seller_key = list(product_data_dictionary.keys())[0]
        product_data_store_dictionary = product_data_dictionary.get(
            store_seller_key
        )
        supported_languages = product_dictionary.get(
            product.Product.KEY_SUPPORTED_LANGUAGES
        )
        lang = list(supported_languages)[0]
        product_data_store_dictionary[lang] = \
            product_data_store_dictionary.pop(
                product_data.ProductData.KEY_LANGUAGE_DATA, 
                None,
        )

        # Add/fix datetime fields.
        self.__add_or_fix_datetime_field(
            offer_dictionary=offer_dictionary,
            product_data_store_dictionary=product_data_store_dictionary,
            product_dictionary=product_dictionary,
            store_dictionary=store_dictionary,
        )

        # TODO: Could have these values set in config no need to lookup values.
        self.__upsert_store(store_dictionary)
     
        product_found_by_gtin = self.__find_product_found_by_gtin(
            product_dictionary
        ) if product_dictionary.get(product.Product.KEY_GTIN) else None
        product_found_by_store_and_number = None
        model_number = product_dictionary.get(
            product.Product.KEY_MODEL_NUMBER
        )
        brand=product_dictionary.get(
            product.Product.KEY_BRAND
        )

        if not product_found_by_gtin and model_number and brand:
            product_found_by_store_and_number = \
                self.__find_product_by_model_number_and_brand(
                    model_number=model_number,
                    brand=brand,
                )

        if not product_found_by_gtin \
            and not product_found_by_store_and_number: 
            # Insert product.
            product_dictionary[
                product.Product.KEY_PRODUCT_DATA
            ] = product_data_dictionary
            
            product_id = self.products_collection.insert(product_dictionary)
            logging.log(logging.INFO, "Added product to database!")
        else:
            product1 = product_found_by_gtin \
                or product_found_by_store_and_number
            product_id = product1[product.Product.KEY_ID]
            product_data_store_seller_index = \
                self.__create_store_seller_index(
                    store_seller_key=store_seller_key,
                )

            if not product1[product.Product.KEY_PRODUCT_DATA].get(
                store_seller_key
            ):
                logging.info('Store data is not set.')

                self.products_collection.update_one(
                    filter={
                        product.Product.KEY_ID: product1[
                            product.Product.KEY_ID
                        ],
                    }, 
                    update={
                        '$set': {
                            product_data_store_seller_index: \
                                product_data_dictionary[store_seller_key],
                            product.Product.KEY_UPDATED: product_dictionary[
                                product.Product.KEY_UPDATED
                            ],
                        },
                        '$addToSet': self.__make_add_to_set_data(product_dictionary=product_dictionary, langauge=lang),
                    },
                    upsert=True,
                )
            elif not product1[product.Product.KEY_PRODUCT_DATA].get(
                store_seller_key
            ).get(lang):
                # TODO: Add supported lang
                product_data_store_seller_lang_index = \
                    self.__create_lang_data_index(
                        product_data_store_seller_index= \
                            product_data_store_seller_index,
                        lang=lang,
                    )

                self.products_collection.update_one(
                    filter={
                        product.Product.KEY_ID: product1[
                            product.Product.KEY_ID
                        ],
                    }, 
                    update={
                        '$set': {
                            product_data_store_seller_lang_index: \
                                product_data_dictionary.get(
                                    store_seller_key
                                ).get(lang),
                            product.Product.KEY_UPDATED: product_dictionary[
                                product.Product.KEY_UPDATED
                            ]
                        },
                        '$addToSet': self.__make_add_to_set_data(product_dictionary=product_dictionary, langauge=lang),
                    },
                    upsert=True,
                )

                logging.log(logging.INFO, "Updated product, added a new language in product data in database!") # TODO: More descriptive messages, use variables.

        # logging.log(logging.INFO, "Updated product's product data in database!") 
        # TODO: Check if URL is the same.
        # TODO: Add new language to fields.
        # TODO: Add supported languages.

        offer_dictionary[offer.Offer.KEY_PRODUCT_ID] = product_id

        offer_id = self.offers_collection.insert(offer_dictionary)
        logging.log(logging.INFO, "Added offer to database!")
        
        return item

    # def __is_product_data_set(self, subject, index): # TODO: No lookup required.
    #     return True if subject.get(index) else False

    # def __is_language_set(self, subject, store_id, sold_by, language):
    #     # if lookup.get(f"{store_id} ({sold_by})") and lookup.get(ProductData.KEY_STORE_ID).get(f"{store_id} ({sold_by})").get(language):
    #     #     return True

    #     return False

    def __create_store_seller_index(
        self, 
        store_seller_key,
    ):
        return product.Product.KEY_PRODUCT_DATA \
                    + '.' + store_seller_key

    def __create_lang_data_index(
        self, 
        product_data_store_seller_index: str,
        lang: str
    ):
        return product_data_store_seller_index \
                    + '.' + lang

    def __find_product_found_by_gtin(self, product_dictionary):
        return self.products_collection.find_one({
            product.Product.KEY_GTIN: product_dictionary[
                product.Product.KEY_GTIN
            ]
        })
    
    def __find_product_by_model_number_and_brand(
        self, 
        model_number, 
        brand,
    ):
        brand_regex = re.compile(f'^{brand}$', re.IGNORECASE)
        
        return self.products_collection.find_one(
            {
                '$and': [
                    {
                        product.Product.KEY_MODEL_NUMBER: model_number
                    },
                    {
                        product.Product.KEY_BRAND: brand_regex
                    }
                ]
            }
        )
    
    def __add_or_fix_datetime_field(
        self,
        offer_dictionary,
        product_data_store_dictionary,
        product_dictionary,
        store_dictionary,
    ):
        dictionaries = [
            offer_dictionary,
            product_data_store_dictionary,
            product_dictionary,
            store_dictionary,
        ]

        now = datetime.utcnow()
        datetime_indexes = [
            'created',
            'updated',
        ]

        for dictionary in dictionaries:
            for datetime_index in datetime_indexes:
                dictionary[datetime_index] = now

    def __upsert_store(self, store_dictionary):
        # nUpserted
        # writeConcernError
        return self.stores_collection.update_one(
            filter={
                store_item.StoreItem.KEY_ID: store_dictionary[
                    store_item.StoreItem.KEY_ID
                ]
            },
            update={
                '$setOnInsert': store_dictionary,
            },
            upsert=True,
        )
        # logging.log(logging.INFO, "Added store to database!")

    def __make_add_to_set_data(self, product_dictionary: Dict, langauge: str) -> Dict:
        return {
            product.Product.KEY_NAME: product_dictionary[
                product.Product.KEY_NAME
            ][0],
            product.Product.KEY_BRAND: product_dictionary[
                product.Product.KEY_BRAND
            ][0],
            product.Product.KEY_SUPPORTED_LANGUAGES: langauge,
            product.Product.KEY_TAGS: { 
                '$each': product_dictionary.get(product.Product.KEY_TAGS) 
            },
        }

        