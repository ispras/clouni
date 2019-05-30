import json
import os

from toscaparser.common.exception import ExceptionCollector
from toscaparser.utils.gettextutils import _

from translator.common.exception import UnknownProvider
from translator.common.combine_templates import PROVIDER_TEMPLATES


def translate(provider, tosca_template, _facts, a_file=False):
    if type(_facts) is dict:
        facts = _facts
    elif os.path.isfile(_facts):
        with open(_facts, "r") as ff:
            facts = json.load(ff)
    else:
        facts = _facts

    yaml_tpl = None
    if os.path.isfile(tosca_template):
        if a_file:
            with open(tosca_template) as tf:
                yaml_tpl = tf.read()
        else:
            ExceptionCollector.appendException(IOError(_('%s is a file') % tosca_template))
    else:
        if a_file:
            ExceptionCollector.appendException(IOError(_('Template parameter is not a file or not found')))
        else:
            yaml_tpl = tosca_template

    tosca_template_class = PROVIDER_TEMPLATES.get(provider)
    if not tosca_template_class:
        ExceptionCollector.appendException(UnknownProvider(
            what=provider
        ))
    tosca = tosca_template_class(yaml_tpl=yaml_tpl, a_file=False, facts=facts)
    return tosca.to_ansible()
