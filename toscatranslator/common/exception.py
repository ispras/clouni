from toscaparser.common.exception import TOSCAException
from toscaparser.utils.gettextutils import _


class UnsupportedRequirementError(TOSCAException):
    msg_fmt = _('Requirement "%(what)s" is not supported.')


class UnavailableNodeFilterError (TOSCAException):
    msg_fmt = _('The "%(what)s" requirement support "node_filter" parameter only with "%(param)s" specifying, '
                'but only "%(data)s" is present')

class ValueType (TOSCAException):
    msg_fmt = _('The value "%(what)s" must be of type "%(type)s"')


class UnspecifiedParameter(TOSCAException):
    msg_fmt = _('One of parameters %(what)s must be specified')


class UnsupportedToscaParameterUsage(TOSCAException):
    msg_fmt = _('Unable to use unsupported TOSCA parameter: %(what)s')


class ToscaParametersMappingFailed(TOSCAException):
    msg_fmt = _('Unable to parse the following parameter %(what)s')


class ProviderFileError(TOSCAException):
    msg_fmt = _('Error parsing file "%(what)s"')


class TemplateDependencyError(TOSCAException):
    msg_fmt = _('Resolving dependencies in template failed on template "%(what)s"')


class UnsupportedExecutorType(TOSCAException):
    msg_fmt = _('Unsupported executor/configuration tool name: "%(what)s"')


class ProviderConfigurationNotFound(TOSCAException):
    msg_fmt = _('Provider configuration was not found. It must be one of the variants: "%(what)s"')


class ProviderConfigurationParameterError(TOSCAException):
    msg_fmt = _('Provider configuration parameter "%(what)s" has unsupported value or missing')


class ConditionFileError(TOSCAException):
    msg_fmt = _('Error loading condition file "%(what)s"')