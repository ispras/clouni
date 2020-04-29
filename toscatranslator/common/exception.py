from toscaparser.common.exception import TOSCAException
from toscaparser.utils.gettextutils import _


class FulfillRequirementError(TOSCAException):
    msg_fmt = _('Requirement "%(what)s" could not be fullfilled')


class UnsupportedRequirementError(TOSCAException):
    msg_fmt = _('Requirement "%(what)s" is not supported.')


class UnavailableNodeFilterError (TOSCAException):
    msg_fmt = _('The "%(what)s" requirement support "node_filter" parameter only with "%(param)s" specifying')


class UnsupportedNodeTypeError (TOSCAException):
    msg_fmt = _('Node type "%(what)s" is not supported')


class InappropriateParameterValueError (TOSCAException):
    msg_fmt = _('Assigned value of parameter "%(what)s" is not appropriate. Please change the value')


class UnspecifiedParameter(TOSCAException):
    msg_fmt = _('One of parameters %(what)s must be specified')


class UnknownProvider(TOSCAException):
    msg_fmt = _('Provider "%(what)s" is not supported')


class UnspecifiedTranslatorForProviderError(TOSCAException):
    msg_fmt = _('Translator for provider "%(what)s" is not specified')


class UnspecifiedProviderTranslatorForNamespaceError(TOSCAException):
    msg_fmt = _('Translator for namespace "%(what)s" is not specified')


class UnspecifiedFactsParserForProviderError(TOSCAException):
    msg_fmt = _('Ansible facts parser for provider "%(what)s" is not specified"')


class UnsupportedFactsFormat(TOSCAException):
    msg_fmt = _('Input error for parameter "facts": "dict" or "path" is required. If path is provided, '
                'then path is incorrect.')


class UnsupportedFilteringValues(TOSCAException):
    msg_fmt = _('Unable to match objects of type %(what) with value of type %(target)')


class UnsupportedToscaParameterUsage(TOSCAException):
    msg_fmt = _('Unable to use unsupported TOSCA parameter: %(what)s')


class ToscaParametersMappingFailed(TOSCAException):
    msg_fmt = _('Unable to parse the following parameter %(what)s')


class UnsupportedMappingFunction(TOSCAException):
    msg_fmt = _('Unsupported function "%(what)s", supported functions are %(supported)s')


class ProviderMappingFileError(TOSCAException):
    msg_fmt = _('Errors in mapping file "%(what)s"')


class TemplateDependencyError(TOSCAException):
    msg_fmt = _('Resolving dependencies in template failed on node "%(what)s"')


class UnsupportedExecutorType(TOSCAException):
    msg_fmt = _('Unsupported executor/configuration tool name: "%(what)s"')
