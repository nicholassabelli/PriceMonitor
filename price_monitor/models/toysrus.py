import datetime
import logging
import json
import re
from price_monitor.items import (
    offer,
    product,
    product_data
)
from price_monitor.item_loaders import (
    product_item_loader,
    product_data_item_loader
)
from price_monitor.models import (
    availability,
    condition,
    curreny,
    global_trade_item_number,
    language,
    region,
    store,
    universal_product_code
)

class Toysrus(store.Store):
    store_id = 'toysrus_canada' # TODO: Constants?
    store_name = 'Toys”R”Us'
    sold_by = 'Toys”R”Us (Canada) Ltd.'
    region = region.Region.CANADA.value
    domain = 'toysrus.ca'
    allowed_domains = [domain]
    custom_settings = {
        'ITEM_PIPELINES': {
            'price_monitor.pipelines.strip_amount_pipeline.StripAmountPipeline': 300,
            'price_monitor.pipelines.mongo_db_pipeline.MongoDBPipeline': 1000
        }
    }

    def parse_product(self, response):
        data = self._find_json_data(response)
        
        if data:
            return self.__load_with_dictionary(response, data)

        logging.warning('No product data found!')
        return None

    def _find_json_data(self, response):
        product_data = response \
            .css('div.b-product_details-stock_error p::attr(data-product)') \
            .extract()

        if product_data:
            return json.loads(product_data[0])
        
        return None

    def __load_with_dictionary(self, response, data):
        product_loader = product_item_loader \
            .ProductItemLoader(response=response)

        lang = language.Language.EN.value


        data['additionalInfo'] = self.__parse_aditional_info(
            data['additionalInfo']
        )
        
        try:
            upc = (universal_product_code.UniversalProductCode(
                data['additionalInfo']['UPC']
            )).value
        except:
            upc = None

        product_loader.add_value(
            product.Product.KEY_BRAND,
            data['brand']
        )
        product_loader.add_value(
            product.Product.KEY_MODEL_NUMBER,
            data['additionalInfo']['Numéro fabricant']
        )

        if upc:
            product_loader.add_value(
                product.Product.KEY_GTIN, 
                super()._create_gtin_field(
                    response=response, 
                    type=global_trade_item_number \
                        .GlobalTradeItemNumber.UPCA.value,
                    value=upc
                )
            )

        product_loader.add_value(
            product.Product.KEY_CURRENT_OFFER,
            self.__get_offer_with_dictionary(response, data)
        )
        product_loader.add_value(
            product.Product.KEY_STORE,
            self.__create_store_dictionary(response)
        )
        product_loader.add_value(
            product.Product.KEY_PRODUCT_DATA, 
            self.__create_product_data_dictionary(response=response, data=data, upc=upc)
        )
        
        return product_loader.load_item()

    def __create_product_data_dictionary(self, response, data, upc):
        product_data_value_loader = \
            product_data_item_loader.ProductDataItemLoader(response=response)

        if upc:
            product_data_value_loader.add_value(
                product.Product.KEY_GTIN, 
                super()._create_gtin_field(
                    response=response, 
                    type=global_trade_item_number \
                        .GlobalTradeItemNumber.UPCA.value, 
                    value=upc
                )
            )

        product_data_value_loader.add_value(
            product_data.ProductData.KEY_BRAND, 
            data['brand']
        )
        product_data_value_loader.add_value( # TODO: HTML entities being replaced with '', it needs spaces. Or we should keep it the same.
            product_data.ProductData.KEY_DESCRIPTION, 
            super()._create_text_field(
                response=response, 
                value=data['longDescription'],  # replace_tags
                language=language.Language.EN.value 
            )
        )
        # product_data_value_loader.add_value(
        #     field_name=product_data.ProductData.KEY_SUPPORTED_LANGUAGES,
        #     value={language.Language.EN.value: {}} # TODO: Fixed.
        # )
        product_data_value_loader.add_value(
            field_name=product_data.ProductData.KEY_MODEL_NUMBER, 
            value=data['additionalInfo']['Numéro fabricant']
        )
        product_data_value_loader.add_value(
            product_data.ProductData.KEY_NAME, 
            super()._create_text_field(
                response=response, 
                value=data['productName'],
                language=language.Language.EN.value
            )
        )
        product_data_value_loader.add_value(
            product_data.ProductData.KEY_SKU, 
            data['SKN']
        )
        product_data_value_loader.add_value(
            offer.Offer.KEY_SOLD_BY,
            self.sold_by
        )
        product_data_value_loader.add_value(
            offer.Offer.KEY_STORE_ID, 
            [self.store_id]
        )
        product_data_value_loader.add_value(
            product_data.ProductData.KEY_URL,
            response.url
        )

        return (product_data_value_loader.load_item()).get_dictionary()

    def _determine_availability(self, data):
        return availability.Availability.IN_STOCK.value if data \
            else availability.Availability.OUT_OF_STOCK.value

    def __get_offer_with_dictionary(self, response, data):
        return super()._create_offer_dictionary(
            response=response, 
            amount=data['price']['sales']['value'], 
            availability=data['available'], 
            condition=condition.Condition.NEW.value, 
            currency=curreny.Currency.CAD.value, 
            sold_by=self.sold_by, 
            store_id=self.store_id
        )
        # sku=data['SKN'], 

    def __create_store_dictionary(self, response):
        return super()._create_store_dictionary(
            response=response, 
            domain=self.domain, 
            store_id=self.store_id, 
            store_name=self.store_name, 
            region=self.region
        )

    def __parse_aditional_info(self, additional_info):
        result = dict()

        for group in additional_info['groups']:
            for entry in group['data']:
                result[entry['name']] = entry['value']
        
        return result