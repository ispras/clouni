from toscaparser.common.exception import TOSCAException
from toscaparser.utils.gettextutils import _


class UnsupportedRequirementError(TOSCAException):
    msg_fmt = _('Requirement "%(what)s" is not supported.')


class UnavailableNodeFilterError (TOSCAException):
    msg_fmt = _('The "%(what)s" requirement support "node_filter" parameter only with "%(param)s" specifying')


class UnspecifiedParameter(TOSCAException):
    msg_fmt = _('One of parameters %(what)s must be specified')


class UnsupportedToscaParameterUsage(TOSCAException):
    msg_fmt = _('Unable to use unsupported TOSCA parameter: %(what)s')


class ToscaParametersMappingFailed(TOSCAException):
    msg_fmt = _('Unable to parse the following parameter %(what)s')


class ProviderMappingFileError(TOSCAException):
    msg_fmt = _('Errors in mapping file "%(what)s"')


class TemplateDependencyError(TOSCAException):
    msg_fmt = _('Resolving dependencies in template failed on template "%(what)s"')


class UnsupportedExecutorType(TOSCAException):
    msg_fmt = _('Unsupported executor/configuration tool name: "%(what)s"')
