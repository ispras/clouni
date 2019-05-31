from toscatranslator.providers.openstack.translator_to_openstack import TRANSLATE_FUNCTION as OPENSTACK_TRANSLATOR
from toscatranslator.providers.amazon.translator_to_amazon import TRANSLATE_FUNCTION as AMAZON_TRANSLATOR


TRANSLATE_FUNCTION = dict(
    openstack=OPENSTACK_TRANSLATOR,
    amazon=AMAZON_TRANSLATOR
)
